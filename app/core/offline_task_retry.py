
import init
import re
import time
import os
import asyncio
from datetime import datetime, timedelta
from app.utils.sqlitelib import *
from app.utils.message_queue import add_task_to_queue
from telegram.helpers import escape_markdown

# 超过此天数仍未完成视为死种，跳过不再处理
DEAD_SEED_DAYS = 3


def wait_for_message_queue_completion(task_name="任务", timeout=0):
    from app.utils.message_queue import message_queue, global_loop

    init.logger.info(f"等待{task_name}通知发送完成...")

    if global_loop:
        try:
            future = asyncio.run_coroutine_threadsafe(
                message_queue.join(),
                global_loop
            )
            future.result(timeout=None if timeout == 0 else timeout)
            init.logger.debug(f"队列已清空，额外等待5秒确保消息完全发送...")
            time.sleep(5)
            init.logger.info(f"所有{task_name}通知已发送完成，开始清理流程")
        except Exception as e:
            init.logger.error(f"等待消息队列完成时出错: {e}")
            while not message_queue.empty():
                init.logger.debug(f"消息队列还有 {message_queue.qsize()} 个任务待处理，等待中...")
                time.sleep(5)
            time.sleep(10)
            init.logger.info(f"所有{task_name}通知已发送完成（降级方案），开始清理流程")
    else:
        init.logger.warn("事件循环未初始化，使用降级方案等待")
        while not message_queue.empty():
            time.sleep(5)
        time.sleep(10)
        init.logger.info(f"所有{task_name}通知已发送完成（降级方案），开始清理流程")


def offline_task_retry():
    """调度器入口：先做后处理，再提交新的离线任务"""
    init.logger.info("开始涩花离线任务...")
    sehua_post_process()
    sehua_offline()


# ---------------------------------------------------------------------------
# 阶段一：提交离线任务，成功即标记 is_download=1
# ---------------------------------------------------------------------------

def sehua_offline(date=None):
    """查找 is_download=0 的条目，批量提交到 115，提交成功立即标记为已离线"""
    submitted_results = []
    sections = init.bot_config.get('sehuatang_spider', {}).get('sections', [])
    sort_by_ym = init.bot_config.get('sehuatang_spider', {}).get('sort_by_year_month', False)

    for section in sections:
        section_name = section.get('name', '')
        sql = "SELECT * FROM sehua_data WHERE is_download=0 AND section_name=? ORDER BY publish_date DESC"
        with SqlLiteLib() as sqlite:
            results = sqlite.query_all(sql, (section_name,))
        if not results:
            init.logger.info(f"[涩花][{section_name}]板块，没有找到需要离线任务~")
            continue

        init.logger.info(f"[涩花][{section_name}]板块，找到 {len(results)} 个需要离线的任务")
        offline_groups = create_offline_group_by_save_path(results)
        if not offline_groups:
            init.logger.warn("涩花离线任务未执行，可能是115离线配额不足，请检查115账号状态！")
            add_task_to_queue(init.bot_config['allowed_user'], f"{init.IMAGE_PATH}/male023.png",
                              "涩花离线任务未执行，可能是115离线配额不足，请检查115账号状态！")
            return

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for save_path, (item_ids, batches) in offline_groups.items():
            real_path = add_year_month_to_path(sort_by_ym, save_path)
            for batch_tasks, batch_ids in batches:
                task_count = len(batch_tasks.strip().splitlines())
                ok = init.openapi_115.offline_download_specify_path(batch_tasks, real_path)
                if ok:
                    init.logger.info(f"{task_count} 个离线任务提交成功，路径: {real_path}")
                    with SqlLiteLib() as sqlite:
                        for item_id in batch_ids:
                            sqlite.execute_sql(
                                "UPDATE sehua_data SET is_download=1, submitted_at=? WHERE id=?",
                                (now_str, item_id)
                            )
                    submitted_results.extend(
                        r for r in results if r['id'] in batch_ids
                    )
                else:
                    init.logger.error(f"{task_count} 个离线任务提交失败，路径: {real_path}")
                time.sleep(2)

    if not submitted_results:
        date_text = f"，日期: {date}" if date else ""
        message = escape_markdown(f"✅ 涩花爬取完成{date_text}，没有找到更新内容或待离线任务。", version=2)
        init.logger.info(f"涩花离线任务完成{date_text}，没有找到更新内容或待离线任务。")
        add_task_to_queue(init.bot_config['allowed_user'], None, message)
        return

    _notify_submitted(submitted_results, date)


def _notify_submitted(submitted_results, date=None):
    """按板块统计提交数量，发送 TG 汇总通知"""
    section_counts = {}
    for item in submitted_results:
        sn = item['section_name']
        section_counts[sn] = section_counts.get(sn, 0) + 1

    lines = []
    for sn, cnt in section_counts.items():
        line = escape_markdown(f"[{sn}] 已提交离线: {cnt} 个", version=2)
        lines.append(line)
        init.logger.info(f"[{sn}] 已提交离线: {cnt} 个")

    date_text = escape_markdown(f"，日期: {date}" if date else "", version=2)
    final_message = f"**涩花离线任务已提交{date_text}:**\n" + "\n".join(lines)
    add_task_to_queue(init.bot_config['allowed_user'], f"{init.IMAGE_PATH}/sehua_daily_update.png", final_message)


# ---------------------------------------------------------------------------
# 阶段二：后处理已提交的任务（下次调度时执行）
# ---------------------------------------------------------------------------

def sehua_post_process():
    """
    查找 is_download=1 的条目，对照 115 云端任务状态：
    - 已完成 → 广告清理，标记 is_download=2
    - 仍在下载 → 跳过，等待下次
    - 超过 DEAD_SEED_DAYS 天未完成 → 记录警告，标记 is_download=2（放弃）
    """
    sql = "SELECT * FROM sehua_data WHERE is_download=1 ORDER BY submitted_at ASC"
    with SqlLiteLib() as sqlite:
        pending_items = sqlite.query_all(sql)

    if not pending_items:
        init.logger.info("[涩花后处理] 没有待后处理的离线任务")
        return

    init.logger.info(f"[涩花后处理] 找到 {len(pending_items)} 个待检查任务")

    offline_task_status = init.openapi_115.get_offline_tasks()
    task_map = {task['url']: task for task in offline_task_status}

    sort_by_ym = init.bot_config.get('sehuatang_spider', {}).get('sort_by_year_month', False)
    now = datetime.now()
    dead_threshold = now - timedelta(days=DEAD_SEED_DAYS)

    images_to_delete = []
    completed_count = 0
    skipped_count = 0
    dead_count = 0

    for item in pending_items:
        item_id = item['id']
        title = item['title']
        magnet = item['magnet']
        save_path = add_year_month_to_path(sort_by_ym, item['save_path'])
        submitted_at = item.get('submitted_at')

        task = task_map.get(magnet)

        # 115 任务已完成
        if task and task.get('status') == 2 and task.get('percentDone') == 100:
            init.logger.info(f"[涩花后处理] {title} 115下载完成，开始广告清理")
            try:
                resource_name = task.get('name', '')
                final_path = f"{save_path}/{resource_name}"
                if init.openapi_115.is_directory(final_path):
                    init.openapi_115.auto_clean_all(final_path)
                    _rename_by_title(final_path, title)
                else:
                    init.logger.info(f"[涩花后处理] {title} 为单文件，跳过广告清理和重命名")
            except Exception as e:
                init.logger.error(f"[涩花后处理] {title} 广告清理失败: {e}")

            with SqlLiteLib() as sqlite:
                sqlite.execute_sql("UPDATE sehua_data SET is_download=2 WHERE id=?", (item_id,))
            if item.get('image_path'):
                images_to_delete.append(item['image_path'])
            completed_count += 1
            continue

        # 判断是否超过死种阈值
        is_dead = False
        if submitted_at:
            try:
                submitted_dt = datetime.strptime(submitted_at, "%Y-%m-%d %H:%M:%S")
                if submitted_dt < dead_threshold:
                    is_dead = True
            except Exception:
                pass
        elif task is None:
            # 115 任务列表里已经没有这条记录（可能被手动删除）
            is_dead = True

        if is_dead:
            init.logger.warn(f"[涩花后处理] {title} 超过 {DEAD_SEED_DAYS} 天未完成，标记放弃")
            with SqlLiteLib() as sqlite:
                sqlite.execute_sql("UPDATE sehua_data SET is_download=2 WHERE id=?", (item_id,))
            if item.get('image_path'):
                images_to_delete.append(item['image_path'])
            dead_count += 1
            continue

        # 仍在下载中，跳过
        percent = task.get('percentDone', 0) if task else 0
        init.logger.info(f"[涩花后处理] {title} 仍在下载中 ({percent}%)，跳过")
        skipped_count += 1

    init.logger.info(
        f"[涩花后处理] 完成: {completed_count}，死种放弃: {dead_count}，等待中: {skipped_count}"
    )

    del_images(images_to_delete)

    if completed_count > 0 or dead_count > 0:
        msg = escape_markdown(
            f"涩花后处理完成: {completed_count} 个下载完成，{dead_count} 个死种放弃，{skipped_count} 个仍在下载",
            version=2
        )
        add_task_to_queue(init.bot_config['allowed_user'], None, msg)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

_ILLEGAL_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

def _sanitize_title(title: str) -> str:
    """去除文件名非法字符，并截断到合理长度"""
    sanitized = _ILLEGAL_CHARS.sub(' ', title).strip()
    return sanitized[:120] if sanitized else ""


def _rename_by_title(final_path: str, title: str):
    """在广告清理后，按 sehua 标题重命名目录（可通过 rename_by_title 配置关闭）"""
    if not init.bot_config.get('sehuatang_spider', {}).get('rename_by_title', False):
        return
    new_name = _sanitize_title(title)
    if not new_name:
        init.logger.warn(f"[涩花后处理] 标题为空，跳过重命名: {final_path}")
        return
    current_name = os.path.basename(final_path)
    if current_name == new_name:
        init.logger.info(f"[涩花后处理] 目录名与标题一致，无需重命名: {new_name}")
        return
    ok = init.openapi_115.rename(final_path, new_name)
    if ok:
        init.logger.info(f"[涩花后处理] 重命名成功: [{current_name}] → [{new_name}]")
    else:
        init.logger.warn(f"[涩花后处理] 重命名失败: [{current_name}] → [{new_name}]")


def del_images(images):
    if not images:
        return
    for image_path in images:
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
                init.logger.debug(f"已删除临时图片文件: {image_path}")
            except Exception as e:
                init.logger.warn(f"删除临时图片文件失败: {image_path}, 错误: {e}")
    init.logger.info("所有临时图片文件已删除!")


def create_offline_group_by_save_path(res_list):
    """
    返回 {save_path: (all_ids, [(batch_magnet_str, batch_ids), ...])}
    每批最多 100 条
    """
    path_groups: dict[str, list] = {}
    for item in res_list:
        if not item.get('magnet'):
            init.logger.warn(f"跳过无效的离线任务，标题: {item.get('title', 'Unknown')}，下载链接为空")
            continue
        sp = item.get('save_path')
        if sp not in path_groups:
            path_groups[sp] = []
        path_groups[sp].append(item)

    result = {}
    for save_path, items in path_groups.items():
        all_ids = [i['id'] for i in items]
        batches = []
        current_batch_magnets = []
        current_batch_ids = []
        for item in items:
            current_batch_magnets.append(item['magnet'])
            current_batch_ids.append(item['id'])
            if len(current_batch_magnets) == 100:
                batches.append(("\n".join(current_batch_magnets), current_batch_ids))
                current_batch_magnets = []
                current_batch_ids = []
        if current_batch_magnets:
            batches.append(("\n".join(current_batch_magnets), current_batch_ids))
        result[save_path] = (all_ids, batches)

    return result


def add_year_month_to_path(need_add, original_path):
    if not need_add:
        return original_path
    current_yearmonth = datetime.now().strftime("%Y%m")
    return os.path.normpath(f"{original_path}/{current_yearmonth}")


if __name__ == '__main__':
    init.load_yaml_config()
    init.create_logger()
    sehua_offline()
