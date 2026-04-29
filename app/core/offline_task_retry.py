
import init
import time
import os
import asyncio
from datetime import datetime
from app.utils.sqlitelib import *
from app.utils.message_queue import add_task_to_queue
from telegram.helpers import escape_markdown


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
    init.logger.info("开始涩花离线任务...")
    sehua_offline()


def sehua_offline(date=None):
    save_path_list = []
    check_results = []
    sections = init.bot_config.get('sehuatang_spider', {}).get('sections', [])
    for section in sections:
        section_name = section.get('name', '')
        save_path = section.get('save_path', f'/AV/涩花/{section_name}')
        sql = "select * from sehua_data WHERE is_download=0 and section_name=? order by publish_date desc"
        with SqlLiteLib() as sqlite:
            results = sqlite.query_all(sql, (section_name,))
            if not results:
                init.logger.info(f"[涩花][{section_name}]板块，没有找到需要离线任务~")
                continue
            init.logger.info(f"[涩花][{section_name}]板块，找到 {len(results)} 个需要离线的任务")
            check_results.extend(results)
            offline_groups = create_offline_group_by_save_path(results)
            if offline_groups:
                for save_path, batches in offline_groups.items():
                    save_path = add_year_month_to_path(init.bot_config.get('sehuatang_spider', {}).get('sort_by_year_month', False), save_path)
                    if save_path not in save_path_list:
                        save_path_list.append(save_path)
                    for batch_tasks in batches:
                        task_count = len(batch_tasks.split('\n'))
                        offline2115(batch_tasks, task_count, save_path)
            else:
                init.logger.warn("涩花离线任务未执行，可能是115离线配额不足，请检查115账号状态！")
                add_task_to_queue(init.bot_config['allowed_user'], f"{init.IMAGE_PATH}/male023.png", "涩花离线任务未执行，可能是115离线配额不足，请检查115账号状态！")
                return

    if not check_results:
        date_text = f"，日期: {date}" if date else ""
        message = escape_markdown(f"✅ 涩花爬取完成{date_text}，没有找到更新内容或待离线任务。", version=2)
        init.logger.info(f"涩花离线任务完成{date_text}，没有找到更新内容或待离线任务。")
        add_task_to_queue(init.bot_config['allowed_user'], None, message)
        return

    time.sleep(300)
    domestic_original_count = 0
    domestic_original_success = 0
    asia_censored_count = 0
    asia_censored_success = 0
    asia_uncensored_count = 0
    asia_uncensored_success = 0
    hd_subtitle_count = 0
    hd_subtitle_success = 0

    success_counters = [0, 0, 0, 0]

    offline_task_status = init.openapi_115.get_offline_tasks()
    images = []
    time_stamp = int(time.time())
    success_task = []
    for item in check_results:
        section_name = item['section_name']
        magnet = item['magnet']
        if section_name == '国产原创':
            domestic_original_count += 1
        elif section_name == '亚洲有码原创':
            asia_censored_count += 1
        elif section_name == '亚洲无码原创':
            asia_uncensored_count += 1
        elif section_name == '高清中文字幕':
            hd_subtitle_count += 1
        save_path = add_year_month_to_path(init.bot_config.get('sehuatang_spider', {}).get('sort_by_year_month', False), item['save_path'])
        for task in offline_task_status:
            if task['url'] == magnet:
                if task['status'] == 2 and task['percentDone'] == 100:
                    sehua_success_proccesser(item, save_path, task, success_counters)
                    images.append(item['image_path'])
                    if section_name == '国产原创':
                        success_task.append({"task": task, "save_path": save_path, "image_path": item['image_path']})
                    else:
                        success_task.append({"task": task, "save_path": save_path})
                else:
                    init.logger.warn(f"{item['title']} 离线下载失败或未完成。")
                    init.openapi_115.del_offline_task(task['info_hash'])
                break

    wait_for_message_queue_completion("涩花")

    domestic_original_success = success_counters[0]
    asia_censored_success = success_counters[1]
    asia_uncensored_success = success_counters[2]
    hd_subtitle_success = success_counters[3]

    messages = []
    if domestic_original_count > 0:
        message_line = escape_markdown(f"[国产原创]离线任务完成情况: {domestic_original_success}/{domestic_original_count}", version=2)
        messages.append(message_line)
        init.logger.info(f"[国产原创]离线任务完成情况: {domestic_original_success}/{domestic_original_count}")

    if asia_censored_count > 0:
        message_line = escape_markdown(f"[亚洲有码原创]离线任务完成情况: {asia_censored_success}/{asia_censored_count}", version=2)
        messages.append(message_line)
        init.logger.info(f"[亚洲有码原创]离线任务完成情况: {asia_censored_success}/{asia_censored_count}")

    if asia_uncensored_count > 0:
        message_line = escape_markdown(f"[亚洲无码原创]离线任务完成情况: {asia_uncensored_success}/{asia_uncensored_count}", version=2)
        messages.append(message_line)
        init.logger.info(f"[亚洲无码原创]离线任务完成情况: {asia_uncensored_success}/{asia_uncensored_count}")

    if hd_subtitle_count > 0:
        message_line = escape_markdown(f"[高清中文字幕]离线任务完成情况: {hd_subtitle_success}/{hd_subtitle_count}", version=2)
        messages.append(message_line)
        init.logger.info(f"[高清中文字幕]离线任务完成情况: {hd_subtitle_success}/{hd_subtitle_count}")

    if messages:
        final_message = "**涩花离线任务完成情况:**\n" + "\n".join(messages)
        if domestic_original_success + asia_censored_success + asia_uncensored_success + hd_subtitle_success > 0:
            add_task_to_queue(init.bot_config['allowed_user'], f"{init.IMAGE_PATH}/sehua_daily_update.png", final_message)
        else:
            add_task_to_queue(init.bot_config['allowed_user'], f"{init.IMAGE_PATH}/teacher_pto.jpg", final_message)

    for path in save_path_list:
        init.openapi_115.auto_clean_all(path)

    init.openapi_115.clear_cloud_task()

    del_images(images)


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


def sehua_success_proccesser(item, save_path, task, success_list):
    id = item['id']
    section_name = item['section_name']
    av_number = item['av_number']
    title = item['title']
    movie_type = item['movie_type']
    size = item['size']
    magnet = item['magnet']
    post_url = item['post_url']
    publish_date = item['publish_date']
    pub_url = item['pub_url']
    image_path = item['image_path']

    with SqlLiteLib() as sqlite:
        sql_update = "UPDATE sehua_data SET is_download=1 WHERE id=?"
        sqlite.execute_sql(sql_update, (id,))

    init.logger.info(f"{title} 离线下载成功！")

    if section_name == '国产原创':
        success_list[0] += 1
    elif section_name == '亚洲有码原创':
        success_list[1] += 1
    elif section_name == '亚洲无码原创':
        success_list[2] += 1
    elif section_name == '高清中文字幕':
        success_list[3] += 1

    if init.bot_config.get('sehuatang_spider', {}).get('notify_me', False):
        msg_av_number = escape_markdown(f"#{av_number}", version=2)
        msg_title = escape_markdown(title, version=2)
        msg_date = escape_markdown(publish_date, version=2)
        msg_size = escape_markdown(size, version=2)
        msg_section = escape_markdown(section_name, version=2)
        msg_movie_type = escape_markdown(movie_type, version=2)
        if section_name == '国产原创':
            message = f"""
**涩花爬取通知**

**版块:**   {msg_section}
**标题:**   `{msg_title}`
**类型:**   {msg_movie_type}
**大小:**   {msg_size}
**发布日期:** {msg_date}
**下载链接:** `{magnet}`
**发布链接:** [点击查看详情]({pub_url})
            """
        else:
            message = f"""
**涩花爬取通知**

**版块:**    {msg_section}
**番号:**   `{msg_av_number.upper()}`
**标题:**   `{msg_title}`
**类型:**    {msg_movie_type}
**大小:**    {msg_size}
**发布日期:** {msg_date}
**下载链接:** `{magnet}`
**发布链接:** [点击查看详情]({pub_url})
                """
        add_task_to_queue(init.bot_config['allowed_user'], image_path, message)


def offline2115(offline_tasks, task_count, save_path):
    offline_success = init.openapi_115.offline_download_specify_path(offline_tasks, save_path)
    if not offline_success:
        init.logger.error(f"{task_count}个离线任务添加离线失败!")
    else:
        init.logger.info(f"{task_count}个离线任务添加离线成功!")
    time.sleep(2)


def create_offline_url(res_list):
    offline_tasks = ""
    offline_tasks_list = []
    index = 0
    for item in res_list:
        if not item['magnet']:
            init.logger.warn(f"跳过无效的离线任务，标题: {item['title']}，下载链接为空")
            continue
        offline_tasks += item['magnet'] + "\n"
        index += 1
        if index == 100:
            offline_tasks_list.append(offline_tasks[:-1])
            offline_tasks = ""
            index = 0
    if offline_tasks:
        offline_tasks_list.append(offline_tasks[:-1])
    return offline_tasks_list


def create_offline_group_by_save_path(res_list):
    path_groups = {}
    for item in res_list:
        if not item.get('magnet'):
            init.logger.warn(f"跳过无效的离线任务，标题: {item.get('title', 'Unknown')}，下载链接为空")
            continue
        save_path = item.get('save_path')
        if save_path not in path_groups:
            path_groups[save_path] = []
        path_groups[save_path].append(item['magnet'])

    result = {}
    for save_path, magnets in path_groups.items():
        batches = []
        current_batch = ""
        count = 0
        for magnet in magnets:
            current_batch += magnet + "\n"
            count += 1
            if count == 100:
                batches.append(current_batch[:-1])
                current_batch = ""
                count = 0
        if current_batch:
            batches.append(current_batch[:-1])
        result[save_path] = batches

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
