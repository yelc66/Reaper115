from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import init
import threading


async def crawl_missav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usr_id = update.message.from_user.id
    if not init.check_user(usr_id):
        await update.message.reply_text("⚠️ 对不起，您无权使用115机器人！")
        return

    if not init.bot_config.get('missav_spider', {}).get('enable', False):
        await update.message.reply_text("⚠️ missav 爬虫未启用，请在配置中开启 missav_spider.enable。")
        return

    if init.CRAWL_MISSAV_STATUS == 1:
        await update.message.reply_text("⚠️ missav 爬取任务正在进行中，请稍后再试！")
        return

    init.CRAWL_MISSAV_STATUS = 1
    await update.message.reply_text("🕷️ 开始爬取 missav 数据，爬取完成后会发送通知，请稍后...")
    from app.core.missav_spider import missav_spider_manual
    thread = threading.Thread(target=missav_spider_manual, daemon=True)
    thread.start()


def register_missav_handlers(application):
    application.add_handler(CommandHandler('cmv', crawl_missav))
    init.logger.info("✅ Missav处理器已注册")
