# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, CallbackQueryHandler
import init
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)


SELECT_MAIN_CATEGORY_SYNC, SELECT_SUB_CATEGORY_SYNC = range(30, 32)


async def sync_directory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usr_id = update.message.from_user.id
    if not init.check_user(usr_id):
        await update.message.reply_text("⚠️ 对不起，您无权使用115机器人！")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(f"📁 {category['display_name']}", callback_data=category['name'])] for category in
        init.bot_config['category_folder']
    ]
    keyboard.append([InlineKeyboardButton("退出", callback_data="quit")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="❓请选择要查看的分类：",
                                   reply_markup=reply_markup)
    return SELECT_MAIN_CATEGORY_SYNC


async def select_main_category_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected_main_category = query.data
    if selected_main_category == "return":
        keyboard = [
            [InlineKeyboardButton(f"📁 {category['display_name']}", callback_data=category['name'])]
            for category in init.bot_config['category_folder']
        ]
        keyboard.append([InlineKeyboardButton("退出", callback_data="quit")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="❓请选择要查看的分类：",
                                       reply_markup=reply_markup)
        return SELECT_MAIN_CATEGORY_SYNC
    elif selected_main_category == "quit":
        return await quit_conversation(update, context)
    else:
        context.user_data["selected_main_category"] = selected_main_category
        sub_categories = [
            item['path_map'] for item in init.bot_config["category_folder"] if item['name'] == selected_main_category
        ][0]

        keyboard = [
            [InlineKeyboardButton(f"📁 {category['name']}", callback_data=category['path'])] for category in sub_categories
        ]
        keyboard.append([InlineKeyboardButton("退出", callback_data="quit")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❓请选择目录：", reply_markup=reply_markup)
        return SELECT_SUB_CATEGORY_SYNC


async def select_sub_category_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_path = query.data
    if selected_path == "quit":
        return await quit_conversation(update, context)
    try:
        await query.edit_message_text(text=f"🔄 正在获取 [{selected_path}] 文件列表，请稍后...")
        video_files = init.openapi_115.get_sync_dir(selected_path)
        count = len(video_files) if video_files else 0
        await query.edit_message_text(text=f"✅ [{selected_path}] 共找到 {count} 个视频文件。")
        return ConversationHandler.END
    except Exception as e:
        await query.edit_message_text(text=f"❌ 获取目录失败：{str(e)}！")
        return ConversationHandler.END


async def quit_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.edit_message_text(text="🚪用户退出本次会话")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="🚪用户退出本次会话")
    return ConversationHandler.END


def register_sync_handlers(application):
    sync_handler = ConversationHandler(
        entry_points=[CommandHandler("sync", sync_directory)],
        states={
            SELECT_MAIN_CATEGORY_SYNC: [CallbackQueryHandler(select_main_category_sync)],
            SELECT_SUB_CATEGORY_SYNC: [CallbackQueryHandler(select_sub_category_sync)],
        },
        fallbacks=[CommandHandler("q", quit_conversation)],
        per_chat=True
    )
    application.add_handler(sync_handler)
    init.logger.info("✅ Sync处理器已注册")
