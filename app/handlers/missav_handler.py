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


async def emby_hot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not init.check_user(update.message.from_user.id):
        await update.message.reply_text("⚠️ 对不起，您无权使用115机器人！")
        return
    cfg = init.bot_config.get('emby') or {}
    if not cfg.get('url') or not cfg.get('api_key'):
        await update.message.reply_text("⚠️ 未配置 emby.url / emby.api_key")
        return
    await update.message.reply_text("🔥 开始同步 Emby 热门合集，请稍后...")
    from app.core.emby_hot import run_emby_hot

    def _job():
        res = run_emby_hot(force=True)
        from app.utils.message_queue import add_task_to_queue
        from telegram.helpers import escape_markdown
        msg = "❌ Emby 热门合集同步失败，详见日志" if res is None else "\n".join(
            f"✅ {r['collection']}: 库中 {r['owned']}，+{r['added']} -{r['removed']}，缺 {len(r['missing'])}" for r in res) or "榜单为空"
        add_task_to_queue(init.get_allowed_user(), None, escape_markdown(msg, version=2))
    threading.Thread(target=_job, daemon=True).start()


def register_missav_handlers(application):
    application.add_handler(CommandHandler('cmv', crawl_missav))
    application.add_handler(CommandHandler('embyhot', emby_hot))
    init.logger.info("✅ Missav处理器已注册")
