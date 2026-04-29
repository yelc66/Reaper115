from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import init
import datetime
import threading


_MODE_ALIASES = {
    "today": "today", "今天": "today",
    "yesterday": "yesterday", "昨天": "yesterday",
    "7days": "7days", "seven_days": "7days", "七天": "7days",
}

_MODE_LABELS = {
    "today": "今天",
    "yesterday": "昨天",
    "7days": "近七天",
}


async def crawl_sehua(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usr_id = update.message.from_user.id
    if not init.check_user(usr_id):
        await update.message.reply_text("⚠️ 对不起，您无权使用115机器人！")
        return

    if init.CRAWL_SEHUA_STATUS == 1:
        await update.message.reply_text("⚠️ 涩花爬取任务正在进行中，请稍后再试！")
        return

    arg = context.args[0].strip() if context.args else ""

    if not arg:
        crawl_mode = "yesterday"
    elif arg.lower() in _MODE_ALIASES:
        crawl_mode = _MODE_ALIASES[arg.lower()]
    else:
        try:
            date_obj = datetime.datetime.strptime(arg, "%Y%m%d")
            crawl_mode = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            await update.message.reply_text(
                "⚠️ 参数错误，支持：today / yesterday / 7days / yyyymmdd\n"
                "例：/csh、/csh today、/csh 7days、/csh 20250428"
            )
            return

    label = _MODE_LABELS.get(crawl_mode, crawl_mode)
    init.CRAWL_SEHUA_STATUS = 1
    await update.message.reply_text(f"🕷️ 开始爬取涩花数据（{label}），爬取完成后会发送通知，请稍后...")
    from app.core.sehuatang_spider import sehuatang_spider_by_date
    thread = threading.Thread(target=sehuatang_spider_by_date, args=(crawl_mode,), daemon=True)
    thread.start()


def register_crawl_handlers(application):
    application.add_handler(CommandHandler('csh', crawl_sehua))
    init.logger.info("✅ Crawl处理器已注册")
