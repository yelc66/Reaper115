from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import init
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


async def _start_sehua_crawl(update: Update, crawl_mode: str):
    label = _MODE_LABELS.get(crawl_mode, crawl_mode)
    init.CRAWL_SEHUA_STATUS = 1
    await update.message.reply_text(f"🕷️ 开始爬取涩花数据（{label}），爬取完成后会发送通知，请稍后...")
    from app.core.sehuatang_spider import sehuatang_spider_by_date
    thread = threading.Thread(target=sehuatang_spider_by_date, args=(crawl_mode,), daemon=True)
    thread.start()


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
        await update.message.reply_text(
            "⚠️ 参数错误，支持：today / yesterday / 7days\n"
            "例：/csh、/csh today、/csh 7days\n\n"
            "也可以直接使用：/csh_yesterday /csh_today /csh_7days"
        )
        return

    await _start_sehua_crawl(update, crawl_mode)


async def crawl_sehua_yesterday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await crawl_sehua_preset(update, "yesterday")


async def crawl_sehua_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await crawl_sehua_preset(update, "today")


async def crawl_sehua_7days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await crawl_sehua_preset(update, "7days")


async def crawl_sehua_preset(update: Update, crawl_mode: str):
    usr_id = update.message.from_user.id
    if not init.check_user(usr_id):
        await update.message.reply_text("⚠️ 对不起，您无权使用115机器人！")
        return

    if init.CRAWL_SEHUA_STATUS == 1:
        await update.message.reply_text("⚠️ 涩花爬取任务正在进行中，请稍后再试！")
        return

    await _start_sehua_crawl(update, crawl_mode)


def register_crawl_handlers(application):
    application.add_handler(CommandHandler('csh', crawl_sehua))
    application.add_handler(CommandHandler('csh_yesterday', crawl_sehua_yesterday))
    application.add_handler(CommandHandler('csh_today', crawl_sehua_today))
    application.add_handler(CommandHandler('csh_7days', crawl_sehua_7days))
    init.logger.info("✅ Crawl处理器已注册")
