"""missav 离线 + 后处理流水线，对 missav_data 表做与 sehua 等价的处理。

复用 offline_task_retry 里表无关的纯逻辑（分组/年月路径/图片清理/标题清洗）。
"""
import init
import os
import time
import threading
from datetime import datetime, timedelta

from app.utils.sqlitelib import *
from app.utils.message_queue import add_task_to_queue
from app.utils.utils import get_magnet_hash
from telegram.helpers import escape_markdown

# 复用 sehua 离线里的表无关纯逻辑，避免重复造轮子
from app.core.offline_task_retry import (
    DEAD_SEED_DAYS,
    POLL_INTERVAL_SECONDS,
    create_offline_group_by_save_path,
    add_year_month_to_path,
    del_images,
    _sanitize_title,
)


# ---------------------------------------------------------------------------
# 后台轮询：检测 is_download=1 的任务，完成则后处理
# ---------------------------------------------------------------------------

def _post_process_watcher():
    init.logger.info(f"[missav轮询] 后台轮询线程启动，间隔 {POLL_INTERVAL_SECONDS // 60} 分钟")
    try:
        while True:
            time.sleep(POLL_INTERVAL_SECONDS)
            with SqlLiteLib() as sqlite:
                pending = sqlite.query_all("SELECT id FROM missav_data WHERE is_download=1")
            if not pending:
                init.logger.info("[missav轮询] 所有任务已处理完毕，轮询线程退出")
                break
            init.logger.info(f"[missav轮询] 检测到 {len(pending)} 个待后处理任务，触发后处理")
            try:
                missav_post_process()
            except Exception as e:
                init.logger.error(f"[missav轮询] 后处理执行出错: {e}")
    finally:
        init.MISSAV_POLL_WATCHER_RUNNING = False


def start_post_process_watcher():
    if init.MISSAV_POLL_WATCHER_RUNNING:
        init.logger.info("[missav轮询] 轮询线程已在运行，跳过重复启动")
        return
    init.MISSAV_POLL_WATCHER_RUNNING = True
    t = threading.Thread(target=_post_process_watcher, name="missav-poll-watcher", daemon=True)
    t.start()


def missav_offline_retry():
    """调度器入口：先后处理，再提交新的离线任务"""
    if init.openapi_115 is None:
        init.logger.warn("[missav] 115 未授权，跳过离线任务")
        return
    init.logger.info("[missav] 开始离线任务...")
    missav_post_process()
    missav_offline()


# ---------------------------------------------------------------------------
# 阶段一：提交离线
# ---------------------------------------------------------------------------

def missav_offline(date=None):
    if init.openapi_115 is None:
        init.logger.error("[missav] 115 未授权，跳过离线任务")
        return
    submitted_results = []
    lists = init.bot_config.get('missav_spider', {}).get('lists', [])
    sort_by_ym = init.bot_config.get('missav_spider', {}).get('sort_by_year_month', False)

    for lst in lists:
        list_name = lst.get('name', '')
        sql = "SELECT * FROM missav_data WHERE is_download=0 AND list_name=? ORDER BY publish_date DESC"
        with SqlLiteLib() as sqlite:
            results = sqlite.query_all(sql, (list_name,))
        if not results:
            init.logger.info(f"[missav][{list_name}] 没有需要离线的任务")
            continue

        init.logger.info(f"[missav][{list_name}] 找到 {len(results)} 个需要离线的任务")
        offline_groups = create_offline_group_by_save_path(results)
        if not offline_groups:
            init.logger.warn("[missav] 离线任务未执行，可能 115 离线配额不足")
            add_task_to_queue(init.get_allowed_user(), None,
                              "missav 离线任务未执行，可能是 115 离线配额不足，请检查 115 账号状态！")
            return

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for save_path, (item_ids, batches) in offline_groups.items():
            real_path = add_year_month_to_path(sort_by_ym, save_path)
            for batch_tasks, batch_ids in batches:
                task_count = len(batch_tasks.strip().splitlines())
                ok = init.openapi_115.offline_download_specify_path(batch_tasks, real_path)
                if ok:
                    init.logger.info(f"[missav] {task_count} 个离线任务提交成功，路径: {real_path}")
                    with SqlLiteLib() as sqlite:
                        for item_id in batch_ids:
                            sqlite.execute_sql(
                                "UPDATE missav_data SET is_download=1, submitted_at=? WHERE id=?",
                                (now_str, item_id))
                    submitted_results.extend(r for r in results if r['id'] in batch_ids)
                else:
                    init.logger.error(f"[missav] {task_count} 个离线任务提交失败，路径: {real_path}")
                time.sleep(2)

    if not submitted_results:
        date_text = f"，日期: {date}" if date else ""
        init.logger.info(f"[missav] 离线任务完成{date_text}，没有待离线任务")
        add_task_to_queue(init.get_allowed_user(), None,
                          escape_markdown(f"✅ missav 爬取完成{date_text}，没有找到更新内容或待离线任务。", version=2))
        return

    _notify_submitted(submitted_results, date)
    start_post_process_watcher()


def _notify_submitted(submitted_results, date=None):
    list_counts = {}
    for item in submitted_results:
        ln = item['list_name']
        list_counts[ln] = list_counts.get(ln, 0) + 1
    lines = []
    for ln, cnt in list_counts.items():
        lines.append(escape_markdown(f"[{ln}] 已提交离线: {cnt} 个", version=2))
        init.logger.info(f"[missav][{ln}] 已提交离线: {cnt} 个")
    date_text = escape_markdown(f"，日期: {date}" if date else "", version=2)
    final_message = f"**missav 离线任务已提交{date_text}:**\n" + "\n".join(lines)
    add_task_to_queue(init.get_allowed_user(), None, final_message)


# ---------------------------------------------------------------------------
# 阶段二：后处理
# ---------------------------------------------------------------------------

def missav_post_process():
    sql = "SELECT * FROM missav_data WHERE is_download=1 ORDER BY submitted_at ASC"
    with SqlLiteLib() as sqlite:
        pending_items = sqlite.query_all(sql)
    if not pending_items:
        init.logger.info("[missav后处理] 没有待后处理的离线任务")
        return

    init.logger.info(f"[missav后处理] 找到 {len(pending_items)} 个待检查任务")
    offline_task_status = init.openapi_115.get_offline_tasks()
    if not offline_task_status:
        init.logger.warn("[missav后处理] 获取 115 离线任务列表失败，跳过本次后处理")
        return

    task_map = {task['info_hash'].upper(): task for task in offline_task_status}
    sort_by_ym = init.bot_config.get('missav_spider', {}).get('sort_by_year_month', False)
    now = datetime.now()
    dead_threshold = now - timedelta(days=DEAD_SEED_DAYS)

    images_to_delete = []
    completed_count = skipped_count = dead_count = 0

    for item in pending_items:
        item_id = item['id']
        title = item['title']
        magnet = item['magnet']
        save_path = add_year_month_to_path(sort_by_ym, item['save_path'])
        submitted_at = item.get('submitted_at')

        item_hash = (get_magnet_hash(magnet) or '').upper()
        task = task_map.get(item_hash)

        if task and task.get('status') == 2 and task.get('percentDone') == 100:
            init.logger.info(f"[missav后处理] {title} 115 下载完成，开始广告清理")
            try:
                resource_name = task.get('name', '')
                final_path = f"{save_path}/{resource_name}"
                if init.openapi_115.is_directory(final_path):
                    init.openapi_115.auto_clean_all(final_path, protect_sibling_of_largest=True)
                    _rename_by_title(final_path, title)
                else:
                    init.logger.info(f"[missav后处理] {title} 为单文件，跳过广告清理和重命名")
            except Exception as e:
                init.logger.error(f"[missav后处理] {title} 广告清理失败: {e}")
            with SqlLiteLib() as sqlite:
                sqlite.execute_sql("UPDATE missav_data SET is_download=2 WHERE id=?", (item_id,))
            if item.get('image_path'):
                images_to_delete.append(item['image_path'])
            completed_count += 1
            continue

        is_dead = False
        if submitted_at:
            try:
                if datetime.strptime(submitted_at, "%Y-%m-%d %H:%M:%S") < dead_threshold:
                    is_dead = True
            except Exception:
                pass
        elif task is None:
            is_dead = True

        if is_dead:
            init.logger.warn(f"[missav后处理] {title} 超过 {DEAD_SEED_DAYS} 天未完成，标记放弃")
            with SqlLiteLib() as sqlite:
                sqlite.execute_sql("UPDATE missav_data SET is_download=2 WHERE id=?", (item_id,))
            if item.get('image_path'):
                images_to_delete.append(item['image_path'])
            dead_count += 1
            continue

        percent = task.get('percentDone', 0) if task else 0
        init.logger.info(f"[missav后处理] {title} 仍在下载中 ({percent}%)，跳过")
        skipped_count += 1

    init.logger.info(f"[missav后处理] 完成: {completed_count}，死种放弃: {dead_count}，等待中: {skipped_count}")
    del_images(images_to_delete)

    if completed_count > 0 or dead_count > 0:
        add_task_to_queue(init.get_allowed_user(), None, escape_markdown(
            f"missav 后处理完成: {completed_count} 个下载完成，{dead_count} 个死种放弃，{skipped_count} 个仍在下载",
            version=2))


def _rename_by_title(final_path, title):
    if not init.bot_config.get('missav_spider', {}).get('rename_by_title', False):
        return
    new_name = _sanitize_title(title)
    if not new_name:
        init.logger.warn(f"[missav后处理] 标题为空，跳过重命名: {final_path}")
        return
    current_name = os.path.basename(final_path)
    if current_name == new_name:
        return
    ok = init.openapi_115.rename(final_path, new_name)
    if ok:
        init.logger.info(f"[missav后处理] 重命名成功: [{current_name}] → [{new_name}]")
    else:
        init.logger.warn(f"[missav后处理] 重命名失败: [{current_name}] → [{new_name}]")


if __name__ == '__main__':
    init.load_yaml_config()
    init.create_logger()
    missav_offline()
