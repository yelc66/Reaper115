# -*- coding: utf-8 -*-

import init
from app.utils.sqlitelib import *
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from app.utils.message_queue import add_task_to_queue
import time
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram.error import TelegramError

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)


def get_failed_tasks():
    with SqlLiteLib() as sqlite:
        sql = "SELECT * FROM offline_task WHERE is_download = 0"
        return sqlite.query_all(sql)

def mark_task_as_completed(task_id: int):
    with SqlLiteLib() as sqlite:
        sql = "UPDATE offline_task SET is_download = 1, completed_at = datetime('now') WHERE id = ?"
        sqlite.execute_sql(sql, (task_id,))

def update_retry_time(task_id: int):
    with SqlLiteLib() as sqlite:
        sql = "UPDATE offline_task SET retry_count = retry_count + 1 WHERE id = ?"
        sqlite.execute_sql(sql, (task_id,))

def clear_failed_tasks():
    with SqlLiteLib() as sqlite:
        sql = "DELETE FROM offline_task WHERE is_download = 0"
        sqlite.execute_sql(sql, ())


def try_to_offline2115_again():
    failed_tasks = get_failed_tasks()
    if not failed_tasks:
        init.logger.info("重试列表为空，暂时没有需要重试的任务！")
        return

    from app.core.offline_task_retry import create_offline_url
    create_offline_url_list = create_offline_url(failed_tasks)
    for offline_tasks in create_offline_url_list:
        if not offline_tasks:
            continue
        offline_success = init.openapi_115.offline_download_specify_path(offline_tasks, failed_tasks[0]['save_path'])
        if offline_success:
            init.logger.info(f"重试任务 {offline_tasks} 添加离线成功")
        else:
            init.logger.error(f"重试任务 {offline_tasks} 添加离线失败")
        time.sleep(2)

    time.sleep(300)

    success_list = []
    offline_task_status = init.openapi_115.get_offline_tasks()
    for failed_task in failed_tasks:
        task_id = failed_task['id']
        link = failed_task['magnet']
        title = failed_task['title']
        save_path = failed_task['save_path']
        for task in offline_task_status:
            if task['url'] == link:
                if task['status'] == 2 and task['percentDone'] == 100:
                    resource_name = task['name']
                    init.logger.info(f"重试任务 {title} 下载完成！")
                    if init.openapi_115.is_directory(f"{save_path}/{resource_name}"):
                        init.openapi_115.auto_clean_all(f"{save_path}/{resource_name}")
                        old_name = f"{save_path}/{resource_name}"
                    else:
                        init.openapi_115.create_dir_for_file(f"{save_path}", "temp")
                        init.openapi_115.move_file(f"{save_path}", f"{save_path}/temp")
                        old_name = f"{save_path}/temp"

                    init.openapi_115.rename(old_name, title)
                    new_final_path = f"{save_path}/{title}"
                    file_list = init.openapi_115.get_files_from_dir(new_final_path)
                    from app.utils.media_utils import create_strm_file, notice_emby_scan_library
                    create_strm_file(new_final_path, file_list)
                    notice_emby_scan_library(new_final_path)

                    if len(link) > 600:
                        link = link[:600] + "..."

                    message = f"""✅ **重试任务 `{title}` 下载成功！**

**资源名称:** `{title}`
**磁力链接:** `{link}`
**保存路径:** `{save_path}`
        """
                    try:
                        add_task_to_queue(init.bot_config['allowed_user'], None, message=message)
                    except TelegramError as e:
                        init.logger.warn(f"Telegram API error: {e}")
                    except Exception as e:
                        init.logger.warn(f"Unexpected error: {e}")

                    mark_task_as_completed(task_id)
                    success_list.append(task['info_hash'])

                else:
                    init.logger.warn(f"重试任务 {title} 下载超时！")
                    update_retry_time(task_id)
                    init.openapi_115.del_offline_task(task['info_hash'])
                break

    for info_hash in success_list:
        init.logger.info(f"清除云端任务 {info_hash} ...")
        init.openapi_115.del_offline_task(info_hash, del_source_file=0)
        time.sleep(2)


async def view_retry_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    retry_list = get_failed_tasks()
    if not retry_list:
        await update.message.reply_text("🈳当前重试列表为空")
        return

    retry_text = "**重试列表：**\n\n"
    for i, task in enumerate(retry_list):
        retry_text += f"{i + 1}\\. `{task['title']}`\n"

    keyboard = [
        [InlineKeyboardButton("清空所有", callback_data="clear_all")],
        [InlineKeyboardButton("返回", callback_data="return")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(retry_text, reply_markup=reply_markup, parse_mode='MarkdownV2')


async def handle_clear_retry_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    callback_data = query.data

    if callback_data == "clear_all":
        clear_failed_tasks()
        await query.edit_message_text("✅ 重试列表已清空！")
    elif callback_data == "return":
        await query.edit_message_text("操作已取消")


def register_offline_task_handlers(application):
    application.add_handler(CommandHandler("rl", view_retry_list))
    application.add_handler(CallbackQueryHandler(handle_clear_retry_list, pattern="^(clear_all|return)$"))
    init.logger.info("✅ Offline Task处理器已注册")
