# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, \
    MessageHandler, filters, CallbackQueryHandler
import init
import os
import uuid
from datetime import datetime
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
class _VideoManagerStub:
    async def add_task(self, task_info): pass
    async def cancel_task(self, task_id): return False

video_manager = _VideoManagerStub()

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)
# 过滤 Telethon 的异步会话实验性功能警告
filterwarnings(action="ignore", message="Using async sessions support is an experimental feature")


async def save_video2115(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usr_id = update.message.from_user.id
    if not init.check_user(usr_id):
        await update.message.reply_text("⚠️ 对不起，您无权使用115机器人！")
        return
    
    await update.message.reply_text("⚠️ 视频转存功能已禁用（当前版本不支持 Telethon 客户端）")
    return

    if update.message and update.message.video:
        video = update.message.video
        file_name = video.file_name if video.file_name else f"{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
        
        # 获取扩展名
        _, file_ext = os.path.splitext(file_name)
        if not file_ext:
            file_ext = ".mp4"

        # 生成唯一任务ID
        task_id = str(uuid.uuid4())[:8]
        
        # 暂存视频信息到 context.user_data，使用 task_id 作为 key
        context.user_data[f"video_{task_id}"] = {
            "file_name": file_name,
            "file_ext": file_ext,
            "file_size": video.file_size,
            "message_id": update.message.message_id,
            "chat_id": update.effective_chat.id
        }

        # 询问是否重命名
        keyboard = [
            [InlineKeyboardButton("使用默认名称", callback_data=f"video_rename_default_{task_id}")],
            [InlineKeyboardButton("自定义名称", callback_data=f"video_rename_custom_{task_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"📹 收到视频: {file_name}\n❓是否需要重命名？",
            reply_markup=reply_markup,
            reply_to_message_id=update.message.message_id
        )

async def show_directory_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: str, edit_message: bool = False):
    """显示目录选择界面"""
    video_info = context.user_data.get(f"video_{task_id}")
    if not video_info:
        if edit_message and update.callback_query:
            await update.callback_query.edit_message_text("❌ 任务已过期")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ 任务已过期")
        return

    file_name = video_info['file_name']
    
    # 显示主分类
    keyboard = []
    
    # 添加上次保存路径按钮
    last_path = context.user_data.get('last_video_save_path')
    if last_path:
        keyboard.append([InlineKeyboardButton(f"🚀 上次保存: {last_path}", callback_data=f"quick_last_{task_id}")])
        
    keyboard.extend([
        [InlineKeyboardButton(f"📁 {category['display_name']}", callback_data=f"main_{category['name']}_{task_id}")] 
        for category in init.bot_config['category_folder']
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"📹 视频文件: {file_name}\n❓请选择要保存到哪个分类："
    
    if edit_message and update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=text,
            reply_markup=reply_markup,
            reply_to_message_id=update.message.message_id
        )

async def handle_rename_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理重命名输入"""
    task_id = context.user_data.get('video_rename_task_id')
    if not task_id:
        return

    new_name = update.message.text.strip()
    
    video_info = context.user_data.get(f"video_{task_id}")
    if video_info:
        # 如果新名字没有扩展名，且我们有原扩展名
        if not os.path.splitext(new_name)[1]:
             file_ext = video_info.get('file_ext', '.mp4')
             new_name += file_ext
             
        video_info['file_name'] = new_name
        # 清除等待状态
        del context.user_data['video_rename_task_id']
        
        # 显示目录选择
        await show_directory_selection(update, context, task_id)



async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        # 忽略 "Query is too old" 错误，这通常发生在点击很久之前的按钮时
        init.logger.debug(f"Callback query answer failed: {e}")
    
    data = query.data
    parts = data.split('_')
    action = parts[0]
    
    if action == "video" and len(parts) > 1 and parts[1] == "rename":
        # 处理重命名选择: video_rename_default_taskId 或 video_rename_custom_taskId
        # parts: ['video', 'rename', 'sub_action', 'task_id']
        if len(parts) < 4:
             return
             
        sub_action = parts[2]
        task_id = parts[3]
        
        if sub_action == "default":
            # 使用默认名称，直接显示目录选择
            await show_directory_selection(update, context, task_id, edit_message=True)
            
        elif sub_action == "custom":
            # 自定义名称，提示输入
            context.user_data['video_rename_task_id'] = task_id
            await query.edit_message_text("⌨️ 请输入新的文件名（无需后缀）：")

    elif action == "main":
        # 选择主分类: main_categoryName_taskId
        category_name = parts[1]
        task_id = parts[2]
        
        sub_categories = [
            item['path_map'] for item in init.bot_config["category_folder"] if item['name'] == category_name
        ][0]

        keyboard = [
            [InlineKeyboardButton(f"📁 {category['name']}", callback_data=f"sub_{category['path']}_{task_id}")] 
            for category in sub_categories
        ]
        keyboard.append([InlineKeyboardButton("返回", callback_data=f"back_{task_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❓请选择子分类：", reply_markup=reply_markup)
        
    elif action == "sub" or action == "quick":
        # 选择子分类: sub_path_taskId 或 quick_last_taskId
        save_path = None
        task_id = None
        
        if action == "sub":
            task_id = parts[-1]
            save_path = "_".join(parts[1:-1])
            # 记录本次保存路径
            context.user_data['last_video_save_path'] = save_path
        elif action == "quick":
            task_id = parts[2]
            save_path = context.user_data.get('last_video_save_path')
            if not save_path:
                await query.answer("上次保存路径已失效，请重新选择", show_alert=True)
                return
        
        video_info = context.user_data.get(f"video_{task_id}")
        if not video_info:
            await query.edit_message_text("❌ 任务信息已过期")
            return

        # 获取原始消息对象
        try:
            # 确定 entity
            entity = None
            # 如果是私聊（chat_id == user_id），User Client 需要去获取和 Bot 的聊天记录
            if video_info['chat_id'] == update.effective_user.id:
                # 动态获取 Bot 用户名，无需依赖配置文件
                try:
                    bot_info = await context.bot.get_me()
                    entity = f"@{bot_info.username}"
                except Exception as e:
                    init.logger.error(f"获取Bot信息失败: {e}")
                    # 回退到配置文件
                    entity = init.bot_config.get('bot_name')
            else:
                # 群组情况，直接用 chat_id
                entity = video_info['chat_id']

            if not entity:
                await query.edit_message_text("❌ 无法确定消息来源 (Entity unknown)")
                return

            await query.edit_message_text("⚠️ 视频转存功能已禁用")
            return
                
            # 提交任务到管理器
            task_info = {
                "task_id": task_id,
                "file_name": video_info['file_name'],
                "file_size": video_info['file_size'],
                "save_path": save_path,
                "message": target_msg,
                "context": context,
                "chat_id": update.effective_chat.id,
                "message_id": query.message.message_id  # 更新这条消息的状态
            }
            
            await video_manager.add_task(task_info)
            
            # 清理 user_data
            del context.user_data[f"video_{task_id}"]
            
        except Exception as e:
            init.logger.error(f"提交任务失败: {e}")
            await query.edit_message_text(f"❌ 提交任务失败: {e}")

    elif action == "back":
        task_id = parts[1]
        keyboard = []
        
        # 添加上次保存路径按钮
        last_path = context.user_data.get('last_video_save_path')
        if last_path:
            keyboard.append([InlineKeyboardButton(f"🚀 上次保存: {last_path}", callback_data=f"quick_last_{task_id}")])
            
        keyboard.extend([
            [InlineKeyboardButton(f"📁 {category['display_name']}", callback_data=f"main_{category['name']}_{task_id}")] 
            for category in init.bot_config['category_folder']
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❓请选择要保存到哪个分类：", reply_markup=reply_markup)

    elif action == "v" and parts[1] == "cancel":
        # 取消下载: v_cancel_taskId
        task_id = parts[2]
        success = await video_manager.cancel_task(task_id)
        if success:
            await query.edit_message_text("🛑 正在取消任务...")
        else:
            await query.answer("任务无法取消或已完成", show_alert=True)

    elif action == "cancel":
        # 保留旧逻辑以防万一，或者直接移除
        if len(parts) > 2 and parts[1] == "dl":
            task_id = parts[2]
            success = await video_manager.cancel_task(task_id)
            if success:
                await query.edit_message_text("🛑 正在取消任务...")


def register_video_handlers(application):
    # 注册视频消息处理器
    application.add_handler(MessageHandler(filters.VIDEO, save_video2115))
    
    # 注册重命名输入处理器 (只处理文本，且非命令)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rename_input))
    
    # 注册回调处理器
    # 添加 v_ 前缀支持，添加 rename 前缀支持
    application.add_handler(CallbackQueryHandler(handle_category_selection, pattern="^(main|sub|back|cancel|quick|v|video_rename)_"))
    
    init.logger.info("✅ Video处理器已注册")
    


