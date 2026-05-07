# -*- coding: utf-8 -*-

import json
import time
import asyncio
import threading
from telegram import Update, BotCommand
from telegram.ext import ContextTypes, CommandHandler, Application
from telegram.helpers import escape_markdown

# 导入init模块（此时__init__.py已经设置了模块路径）
import init

from app.utils.message_queue import add_task_to_queue, queue_worker
from app.handlers.download_handler import register_download_handlers
from app.handlers.video_handler import register_video_handlers
from app.core.scheduler import start_scheduler_in_thread
from app.handlers.offline_task_handler import register_offline_task_handlers
from app.handlers.crawl_handler import register_crawl_handlers
from app.handlers.auth_115_handler import register_auth_115_handlers
from app.web.server import start_web_server_in_thread
from app.core.selenium_browser import check_browser_health


def telegram_configured():
    token = str(init.bot_config.get('bot_token') or '').strip()
    allowed_user = str(init.bot_config.get('allowed_user') or '').strip()
    return (
        token
        and token != 'your_bot_token'
        and allowed_user
        and allowed_user != 'your_user_id'
    )


def get_version(md_format=False):
    version = "v3.4.1"
    if md_format:
        return escape_markdown(version, version=2)
    return version

def get_help_info():
    version = get_version()
    help_info = f"""
<b>🍿 Telegram-115Bot {version} 使用手册</b>\n\n
<b>🔧 命令列表</b>\n
<code>/start</code> - 显示帮助信息\n
<code>/reload</code> - <i>重载配置</i>\n
<code>/rl</code> - 查看重试列表\n
<code>/csh_yesterday</code> - 爬取昨日涩花\n
<code>/csh_today</code> - 爬取今日涩花\n
<code>/csh_7days</code> - 爬取近七天涩花\n
<code>/q</code> - 取消当前会话\n\n
<b>✨ 功能说明</b>\n
<u>磁力/离线下载：</u>
• 直接输入下载链接，支持磁力/ed2k/迅雷
• 离线超时可选择添加到重试列表
<u>重试列表：</u>
• 输入 <code>"/rl"</code>
• 查看当前重试列表，可根据需要选择是否清空\n
<u>手动爬取涩花：</u>
• 常用：<code>/csh_yesterday</code>、<code>/csh_today</code>、<code>/csh_7days</code>\n
<u>视频转存：</u>
• 直接转发视频给机器人，选择保存目录即可保存到115
"""
    return help_info

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_info = get_help_info()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_info, parse_mode="html", disable_web_page_preview=True)

async def reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init.load_yaml_config()
    init.initialize_115open()
    init.logger.info("Reload configuration success:")
    init.logger.info(json.dumps(init.bot_config))
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🔁重载配置完成！", parse_mode="html")

def start_async_loop():
    """启动异步事件循环的线程"""
    import app.utils.message_queue as mq
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    mq.global_loop = loop  # 在 run_forever 前赋值，确保其他线程可立即使用
    init.logger.info("事件循环已启动")
    try:
        token = init.bot_config['bot_token']
        loop.create_task(queue_worker(loop, token))
        loop.run_forever()
    except Exception as e:
        init.logger.error(f"事件循环异常: {e}")
    finally:
        loop.close()
        init.logger.info("事件循环已关闭")

def send_start_message():
    version = get_version()
    if init.openapi_115 is None:
        return

    line1, line2, line3, line4 = init.openapi_115.welcome_message()
    if not line1:
        return
    line5 = escape_markdown(f"Telegram-115Bot {version} 启动成功！", version=2)
    if line1 and line2 and line3 and line4:
        formatted_message = f"""
{line1}
{line2}
{line3}
{line4}

{line5}

发送 `/start` 查看操作说明"""

        add_task_to_queue(
            init.bot_config['allowed_user'],
            f"{init.IMAGE_PATH}/neuter010.png",
            message=formatted_message
        )


def check_browser_on_startup():
    """启动时检查浏览器状态。爬虫启用时检测失败会阻止启动。"""
    spider_enabled = init.bot_config.get("sehuatang_spider", {}).get("enable", False)
    ok, message = check_browser_health()

    if ok:
        init.logger.info(message)
        return True

    log_message = f"启动浏览器检测未通过：{message}"
    if spider_enabled:
        init.logger.error(log_message)
        if telegram_configured():
            notify_message = escape_markdown(
                f"⚠️ 启动浏览器检测未通过：{message}\n涩花爬虫无法正常运行，请检查 REMOTE_SELENIUM_URL 和远程 Selenium 服务。",
                version=2
            )
            add_task_to_queue(
                init.bot_config['allowed_user'],
                None,
                message=notify_message
            )
        return False
    else:
        init.logger.warn(f"{log_message}。当前涩花爬虫未启用，仅记录此提示。")
        return True


def update_logger_level():
    import logging
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('telegram.ext.Application').setLevel(logging.WARNING)
    logging.getLogger('telegram.ext.Updater').setLevel(logging.WARNING)
    logging.getLogger('telegram.Bot').setLevel(logging.WARNING)

def get_bot_menu():
    return [
        BotCommand("start", "帮助信息"),
        BotCommand("reload", "重载配置"),
        BotCommand("rl", "重试列表"),
        BotCommand("csh_yesterday", "抓取昨日涩花"),
        BotCommand("csh_today", "抓取今日涩花"),
        BotCommand("csh_7days", "抓取近七天涩花"),
        BotCommand("auth", "115扫码重新授权"),
        BotCommand("q", "取消当前会话")]


async def set_bot_menu(application):
    """异步设置Bot菜单"""
    try:
        await application.bot.set_my_commands(get_bot_menu())
        init.logger.info("Bot菜单命令已设置!")
    except Exception as e:
        init.logger.error(f"设置Bot菜单失败: {e}")

async def post_init(application):
    """应用初始化后的回调"""
    await set_bot_menu(application)


if __name__ == '__main__':
    init.init()
    tg_enabled = telegram_configured()
    if tg_enabled:
        # 启动消息队列
        message_thread = threading.Thread(target=start_async_loop, daemon=True)
        message_thread.start()
        # 等待消息队列准备就绪
        import app.utils.message_queue as message_queue
        max_wait = 30  # 最多等待30秒
        wait_count = 0
        while True:
            if message_queue.global_loop is not None:
                init.logger.info("消息队列线程已准备就绪！")
                break
            time.sleep(1)
            wait_count += 1
            if wait_count >= max_wait:
                init.logger.error("消息队列线程未准备就绪，程序将退出。")
                exit(1)
    else:
        init.logger.warn("Telegram Bot 未配置，跳过 Telegram polling 和消息队列。")
    init.logger.info("Starting bot with configuration:")
    init.logger.info(json.dumps(init.bot_config))
    if not check_browser_on_startup():
        init.logger.error("浏览器检测失败，程序将退出。")
        exit(1)
    # 调整telegram日志级别
    update_logger_level()
    token = str(init.bot_config.get('bot_token') or '').strip()
    application = None
    if tg_enabled:
        application = Application.builder().token(token).post_init(post_init).build()

        # 启动帮助
        start_handler = CommandHandler('start', start)
        application.add_handler(start_handler)
        # 重载配置
        reload_handler = CommandHandler('reload', reload)
        application.add_handler(reload_handler)

    # 初始化115open对象
    if not init.initialize_115open():
        init.logger.error("115 OpenAPI客户端初始化失败，服务将继续运行；如启用 Telegram，可通过 /auth 重新授权。")
        if tg_enabled:
            add_task_to_queue(
                init.bot_config['allowed_user'],
                None,
                message="⚠️ 115 OpenAPI 初始化失败，下载/爬虫功能暂不可用。\n请使用 /auth 重新扫码授权，或在 Web UI 中检查 Token 配置。"
            )


    if tg_enabled:
        # 注册下载
        register_download_handlers(application)
        # 注册离线任务
        register_offline_task_handlers(application)
        # 手动爬虫
        register_crawl_handlers(application)
        # 115扫码授权
        register_auth_115_handlers(application)
        # 注册视频
        register_video_handlers(application)

    init.logger.info(f"USER_AGENT: {init.USER_AGENT}")

    # 启动机器人轮询
    try:
        # 启动订阅线程
        start_scheduler_in_thread()
        init.logger.info("订阅线程启动成功！")
        start_web_server_in_thread()
        time.sleep(3)  # 等待订阅线程启动
        if tg_enabled:
            send_start_message()
            application.run_polling()  # 阻塞运行
        else:
            init.logger.info("Telegram Bot 未启用，Web API 和调度器保持运行。")
            while True:
                time.sleep(3600)
    except KeyboardInterrupt:
        init.logger.info("程序已被用户终止（Ctrl+C）。")
    except SystemExit:
        init.logger.info("程序正在退出。")
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()  # 获取完整的异常堆栈信息
        init.logger.error(f"程序遇到错误：{str(e)}\n{error_details}")
    finally:
        init.logger.info("机器人已停止运行。")
