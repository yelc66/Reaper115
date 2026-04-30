# -*- coding: utf-8 -*-

import init
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler


async def auth_115(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usr_id = update.effective_user.id
    if not init.check_user(usr_id):
        return

    app_id = init.bot_config.get("115_app_id", "")
    if not app_id or str(app_id).lower() == "your_115_app_id":
        await update.message.reply_text("115 App ID 未配置，请先在 config.yaml 中填写 115_app_id")
        return

    await update.message.reply_text("正在获取115扫码授权二维码，请稍候...")

    import threading

    def _do_auth():
        try:
            if init.openapi_115 is None:
                from app.core.open_115 import OpenAPI_115
                import threading as _t
                init.openapi_115 = OpenAPI_115.__new__(OpenAPI_115)
                init.openapi_115.access_token = ""
                init.openapi_115.refresh_token = ""
                init.openapi_115.lock = _t.Lock()
                init.openapi_115.refresh_lock = _t.Lock()

            init.openapi_115.auth_pkce(usr_id, app_id)
            init.initialize_115open()
        except Exception as e:
            init.logger.error(f"115 扫码授权失败: {e}")
            from app.utils.message_queue import add_task_to_queue
            add_task_to_queue(usr_id, None, f"115 扫码授权失败: {e}")

    threading.Thread(target=_do_auth, daemon=True).start()


def register_auth_115_handlers(application):
    application.add_handler(CommandHandler("auth", auth_115))
