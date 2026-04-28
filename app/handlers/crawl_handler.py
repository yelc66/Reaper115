from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import init
import datetime
import threading


async def crawl_sehua(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usr_id = update.message.from_user.id
    if not init.check_user(usr_id):
        await update.message.reply_text("⚠️ 对不起，您无权使用115机器人！")
        return

    if context.args:
        try:
            date_obj = datetime.datetime.strptime(context.args[0], "%Y%m%d")
            date = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            await update.message.reply_text("⚠️ 日期格式错误，请使用 yyyymmdd 格式，例如：20250808")
            return
    else:
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        date = yesterday.strftime("%Y-%m-%d")
        init.logger.info("涩花默认爬取昨日数据")

    if init.CRAWL_SEHUA_STATUS == 1:
        await update.message.reply_text("⚠️ 涩花爬取任务正在进行中，请稍后再试！")
        return

    init.CRAWL_SEHUA_STATUS = 1
    await update.message.reply_text(f"🕷️ 开始爬取涩花数据，日期: {date}，爬取完成后会发送通知，请稍后...")
    from app.core.sehua_spider import sehua_spider_by_date
    thread = threading.Thread(target=sehua_spider_by_date, args=(date,))
    thread.start()


def register_crawl_handlers(application):
    application.add_handler(CommandHandler('csh', crawl_sehua))
    init.logger.info("✅ Crawl处理器已注册")
