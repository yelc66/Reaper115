# -*- coding: utf-8 -*-
import os
from zoneinfo import ZoneInfo
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import init
import threading
from apscheduler.triggers.interval import IntervalTrigger
from app.handlers.offline_task_handler import try_to_offline2115_again
from app.core.sehuatang_spider import sehuatang_spider_start
from app.core.offline_task_retry import offline_task_retry
from app.core.missav_spider import missav_spider_start
from app.core.missav_offline import missav_offline_retry


def _get_scheduler_timezone():
    # 显式指定时区，不依赖容器系统是否安装 tzdata（slim 镜像默认没有）。
    # 否则 APScheduler 会回退到 UTC，导致定时任务比预期晚 8 小时触发。
    tz_name = os.environ.get("TZ") or "Asia/Shanghai"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("Asia/Shanghai")


SCHEDULER_TZ = _get_scheduler_timezone()
scheduler = BlockingScheduler(timezone=SCHEDULER_TZ)

def get_sehua_sync_time():
    sync_time = {'hour': 3, 'minute': 0}
    sehua_config = init.bot_config.get("sehuatang_spider") or {}
    sehua_sync_time = sehua_config.get("sync_time", "03:00")
    try:
        hour, minute = map(int, sehua_sync_time.split(":"))
        sync_time['hour'] = hour
        sync_time['minute'] = minute
    except Exception as e:
        init.logger.warn(f"解析涩花同步时间失败: {e}，将使用默认时间 03:00")
    return sync_time


def get_missav_sync_time():
    sync_time = {'hour': 4, 'minute': 0}
    missav_config = init.bot_config.get("missav_spider") or {}
    missav_sync_time = missav_config.get("sync_time", "04:00")
    try:
        hour, minute = map(int, missav_sync_time.split(":"))
        sync_time['hour'] = hour
        sync_time['minute'] = minute
    except Exception as e:
        init.logger.warn(f"解析 missav 同步时间失败: {e}，将使用默认时间 04:00")
    return sync_time

def clear_request_count():
    if init.openapi_115 is None:
        return
    init.logger.info(f"昨日累计115 OpenAPI请求次数: [{init.openapi_115.request_count}]")
    cache_hit_rate = (init.openapi_115.cache_hit / init.openapi_115.request_count * 100) if init.openapi_115.request_count > 0 else 0
    init.logger.info(f"昨日累计115 缓存命中率: [{cache_hit_rate:.2f}%]")
    init.logger.info("正在重置115请求计数...")
    init.openapi_115.clear_request_count()
    init.logger.info("115请求计数已重置！")

tasks = []

def init_tasks():
    global tasks
    sehua_sync_time = get_sehua_sync_time()
    tasks = [
        {"id": "offline_task_retry_task", "func": offline_task_retry, "hour": "9,18", "minute": 0, "task_type": "time"},
        {"id": "retry_failed_downloads", "func": try_to_offline2115_again, "interval": 12 * 60 * 60, "task_type": "interval"},
        {"id": "clear_request_count_task", "func": clear_request_count, "hour": 0, "minute": 0, "task_type": "time"},
        {"id": "sehuatang_spider_task", "func": sehuatang_spider_start, "hour": sehua_sync_time.get("hour", 3), "minute": sehua_sync_time.get("minute", 0), "task_type": "time"}
    ]

    # missav 仅在启用时挂载爬虫 + 后处理重试任务
    if (init.bot_config.get("missav_spider") or {}).get("enable", False):
        missav_sync_time = get_missav_sync_time()
        tasks.extend([
            {"id": "missav_spider_task", "func": missav_spider_start, "hour": missav_sync_time.get("hour", 4), "minute": missav_sync_time.get("minute", 0), "task_type": "time"},
            {"id": "missav_offline_retry_task", "func": missav_offline_retry, "hour": "10,19", "minute": 0, "task_type": "time"},
        ])


def subscribe_scheduler():
    init_tasks()
    for task in tasks:
        if not scheduler.get_job(task["id"]):
            if task['task_type'] == 'interval':
                scheduler.add_job(
                    task["func"],
                    IntervalTrigger(seconds=task["interval"]),
                    id=task["id"],
                )
            if task['task_type'] == 'time':
                scheduler.add_job(
                    task["func"],
                    CronTrigger(hour=task["hour"], minute=task["minute"], timezone=SCHEDULER_TZ),
                    id=task["id"],
                )
    init.logger.info(f"调度器时区: {SCHEDULER_TZ}，已挂载任务: {[t['id'] for t in tasks]}")
    if not scheduler.running:
        scheduler.start()


def reload_scheduler():
    """根据当前 init.bot_config 重新计算并同步调度任务。

    用于 Web 端修改配置后无需重启容器即可生效：
    - 新增/缺失的任务会被添加（如开启 missav 后挂载 missav 任务）
    - 时间变更的任务会被重新调度（如改了 sync_time）
    - 不再需要的任务会被移除（如关闭 missav 后卸载 missav 任务）
    """
    if not scheduler.running:
        # 调度器还没起来，交给正常启动流程即可
        subscribe_scheduler()
        return

    init_tasks()
    desired_ids = {task["id"] for task in tasks}

    # 移除不再需要的任务
    for job in list(scheduler.get_jobs()):
        if job.id not in desired_ids:
            scheduler.remove_job(job.id)
            init.logger.info(f"调度任务已卸载: {job.id}")

    # 添加或更新需要的任务
    for task in tasks:
        if task['task_type'] == 'interval':
            trigger = IntervalTrigger(seconds=task["interval"])
        else:
            trigger = CronTrigger(hour=task["hour"], minute=task["minute"], timezone=SCHEDULER_TZ)

        if scheduler.get_job(task["id"]):
            # 已存在则更新触发器（覆盖时间变更）
            scheduler.reschedule_job(task["id"], trigger=trigger)
        else:
            scheduler.add_job(task["func"], trigger, id=task["id"])
            init.logger.info(f"调度任务已挂载: {task['id']}")

    init.logger.info(f"调度器已重载，当前任务: {[t['id'] for t in tasks]}")


def stop_all_subscriptions():
    for task in tasks:
        job = scheduler.get_job(task['id'])
        if job:
            scheduler.remove_job(task['id'])
            init.logger.info(f"任务 {task['id']} 已停止")
        else:
            init.logger.info(f"任务 {task['id']} 不存在")


def start_scheduler_in_thread():
    thread = threading.Thread(target=subscribe_scheduler)
    thread.daemon = True
    thread.start()
