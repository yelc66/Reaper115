from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
import sys
import os
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sys.path.append(current_dir)
import init
import datetime
from app.utils.sqlitelib import *
import time
import random
import os
import re
import yaml
from pathlib import Path
from urllib.parse import urlparse
from urllib.parse import urlparse
from app.core.offline_task_retry import sehua_offline
from app.core.selenium_browser import SeleniumBrowser
from app.utils.utils import get_magnet_hash, read_yaml_file, check_magnet
from app.utils.message_queue import add_task_to_queue
from telegram.helpers import escape_markdown
import asyncio
import requests

# 全局browser
browser = None

def _build_full_url(path: str):
    """根据 browser.base_url 构造完整 URL，避免重复添加协议头"""
    if not browser or not browser.base_url:
        return path
    base = browser.base_url.rstrip('/')
    if not base.startswith('http'):
        base = f"https://{base}"
    return f"{base}/{path.lstrip('/')}"


def _parse_topic_date(value, today=None):
    if not value:
        return None
    raw = str(value).strip()
    if today is None:
        today = datetime.datetime.now().date()

    match = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", raw)
    if match:
        try:
            return datetime.datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except ValueError:
            return None

    if any(keyword in raw for keyword in ("刚刚", "秒前", "分钟前", "小时前", "小时", "半小时前", "今天")):
        return today

    if "昨天" in raw:
        return today - datetime.timedelta(days=1)

    if "前天" in raw:
        return today - datetime.timedelta(days=2)

    match = re.search(r"(\d+)\s*天前", raw)
    if match:
        return today - datetime.timedelta(days=int(match.group(1)))

    try:
        return datetime.datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_topic_age_days(value, today=None):
    if not value:
        return None
    raw = str(value).strip()
    if today is None:
        today = datetime.datetime.now().date()

    if any(keyword in raw for keyword in ("刚刚", "秒前", "分钟前", "小时前", "小时", "半小时前", "今天")):
        return 0

    if "昨天" in raw:
        return 1

    if "前天" in raw:
        return 2

    match = re.search(r"(\d+)\s*天前", raw)
    if match:
        return int(match.group(1))

    parsed_date = _parse_topic_date(raw, today)
    if parsed_date:
        return (today - parsed_date).days

    return None


def _normalize_crawl_mode(mode_or_date, end_date=None):
    raw = str(mode_or_date or "").strip().lower()
    if raw in ("today", "今天"):
        return "today"
    if raw in ("yesterday", "昨天"):
        return "yesterday"
    if raw in ("7days", "seven_days", "week", "七天", "近7天", "近 7 天"):
        return "7days"

    start, end = _normalize_date_range(mode_or_date, end_date)
    today = datetime.datetime.now().date()
    if start and end:
        if start == today and end == today:
            return "today"
        if start == today - datetime.timedelta(days=1) and end == today - datetime.timedelta(days=1):
            return "yesterday"
        if start == today - datetime.timedelta(days=7) and end == today:
            return "7days"

    return raw or "yesterday"


def _format_crawl_mode(mode):
    mode = _normalize_crawl_mode(mode)
    return {
        "today": "今天",
        "yesterday": "昨天",
        "7days": "七天",
    }.get(mode, mode)


def _topic_matches_crawl_mode(topic_date_text, mode, today=None):
    if today is None:
        today = datetime.datetime.now().date()
    age_days = _parse_topic_age_days(topic_date_text, today)
    if age_days is None or age_days < 0:
        return False
    mode = _normalize_crawl_mode(mode)
    if mode == "today":
        return age_days == 0
    if mode == "yesterday":
        return age_days == 1
    if mode == "7days":
        return age_days <= 7
    target_date = _parse_topic_date(mode, today)
    topic_date = _parse_topic_date(topic_date_text, today)
    if target_date and topic_date:
        return topic_date == target_date
    return False


def _page_is_older_than_crawl_mode(found_dates, mode, today=None):
    if today is None:
        today = datetime.datetime.now().date()
    page_ages = [_parse_topic_age_days(item, today) for item in found_dates]
    page_ages = [item for item in page_ages if item is not None]
    if not page_ages:
        return False, None

    newest_age = min(page_ages)
    mode = _normalize_crawl_mode(mode)
    max_age = {"today": 0, "yesterday": 1, "7days": 7}.get(mode)
    if max_age is None:
        target_date = _parse_topic_date(mode, today)
        if not target_date:
            return False, newest_age
        target_age = (today - target_date).days
        return newest_age > target_age, newest_age
    return newest_age > max_age, newest_age


def _format_topic_date(value, today=None):
    parsed = _parse_topic_date(value, today)
    return parsed.strftime("%Y-%m-%d") if parsed else None


def _normalize_date_range(start_date, end_date=None):
    start = _parse_topic_date(start_date)
    end = _parse_topic_date(end_date or start_date)
    if not start or not end:
        return None, None
    if start > end:
        start, end = end, start
    return start, end


def _format_date_range(start_date, end_date=None):
    start, end = _normalize_date_range(start_date, end_date)
    if not start or not end:
        return str(start_date)
    if start == end:
        return start.strftime("%Y-%m-%d")
    return f"{start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}"

def get_base_url():
    base_url = init.bot_config.get('sehuatang_spider', {}).get('base_url', "www.sehuatang.net")
    if not base_url:
        base_url = "www.sehuatang.net"
    return base_url


def _parse_cookie_string(cookie_string):
    cookies = []
    if not cookie_string:
        return cookies
    for item in cookie_string.split(';'):
        item = item.strip()
        if not item or '=' not in item:
            continue
        name, value = item.split('=', 1)
        name = name.strip()
        if not name:
            continue
        cookies.append({
            'name': name,
            'value': value.strip(),
            'path': '/'
        })
    return cookies


def _normalize_cookie(cookie):
    if not isinstance(cookie, dict):
        return None
    name = str(cookie.get('name', '')).strip()
    value = cookie.get('value')
    if not name or value is None:
        return None

    normalized = {
        'name': name,
        'value': str(value),
        'path': cookie.get('path') or '/'
    }
    for key in ('domain', 'secure', 'httpOnly', 'sameSite'):
        if key in cookie and cookie.get(key) not in (None, ''):
            normalized[key] = cookie.get(key)
    if cookie.get('expiry') not in (None, ''):
        try:
            normalized['expiry'] = int(cookie.get('expiry'))
        except (TypeError, ValueError):
            pass
    return normalized


def _get_configured_cookies():
    sehua_config = init.bot_config.get('sehuatang_spider', {}) or {}
    cookies = []
    cookies.extend(_parse_cookie_string(sehua_config.get('cookie_string', '')))
    for cookie in sehua_config.get('cookies', []) or []:
        normalized = _normalize_cookie(cookie)
        if normalized:
            cookies.append(normalized)
    return cookies


async def apply_configured_cookies():
    cookies = _get_configured_cookies()
    if not cookies:
        return
    if not browser or not browser.driver:
        init.logger.warn("涩花 Cookie 注入跳过：浏览器未初始化")
        return

    def _add_cookies(driver):
        success_count = 0
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
                success_count += 1
            except Exception as e:
                init.logger.debug(f"涩花 Cookie 写入失败 [{cookie.get('name')}]: {e}")
        if success_count:
            init.logger.info(f"涩花 Cookie 写入完成: {success_count}/{len(cookies)}，刷新页面...")
            driver.refresh()
            time.sleep(2)
        else:
            init.logger.warn("涩花 Cookie 配置存在，但没有成功写入，请检查 cookie domain 是否匹配 base_url")

    await browser.run_with_driver(_add_cookies)


async def download_image(image_url, save_path):
    """
    使用全局浏览器下载外链图片并保存到本地
    专门用于下载外部图片链接，使用最简单可靠的方法
    
    Args:
        image_url (str): 图片的URL
        save_path (str): 保存路径（不包含扩展名）
        
    Returns:
        bool: 下载是否成功
        str: 本地文件路径或错误信息
    """
    if not image_url:
        return False, "图片URL为空"
    
    if not browser or not browser.driver:
        return False, "无法获取浏览器页面"
    
    try:
        # 确保保存目录存在
        if not os.path.exists(save_path):
            os.makedirs(save_path, exist_ok=True)
            init.logger.debug(f"创建目录: {save_path}")
        
        init.logger.debug(f"开始下载外链图片: {image_url}")
        
        # 使用 requests 配合 selenium cookies 下载
        try:
            init.logger.debug("尝试直接访问图片URL...")
            
            cookies = await browser.get_cookies()
            session = requests.Session()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
            
            headers = {
                "User-Agent": init.USER_AGENT,
                "Referer": f"https://{get_base_url()}/"
            }
            
            def _download():
                return session.get(image_url, headers=headers, timeout=60)
            
            response = await asyncio.to_thread(_download)
            
            if response.status_code == 200:
                # 检查Content-Type是否为图片
                content_type = response.headers.get('content-type', '').lower()
                init.logger.debug(f"Content-Type: {content_type}")
                
                if any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'gif', 'webp']):
                    init.logger.debug("检测到图片内容，开始下载...")
                    
                    # 获取图片数据
                    image_data = response.content

                    # 获取文件名
                    filename = get_image_name(image_url)

                    # 保存文件
                    final_save_path = os.path.join(save_path, filename)
                    init.logger.debug(f"保存到: {final_save_path}")
                    
                    with open(final_save_path, 'wb') as f:
                        f.write(image_data)
                    
                    file_size = len(image_data)
                    if os.path.exists(final_save_path) and file_size > 0:
                        init.logger.info(f"图片下载成功: {final_save_path} ({file_size} bytes)")
                        return True, final_save_path
                    else:
                        error_msg = f"图片保存失败: {final_save_path}"
                        init.logger.warn(error_msg)
                        return False, error_msg
                else:
                    error_msg = f"URL返回的不是图片内容，Content-Type: {content_type}"
                    init.logger.warn(error_msg)
                    return False, error_msg
            else:
                status_code = response.status_code
                error_msg = f"访问失败，状态码: {status_code}"
                init.logger.warn(error_msg)
                return False, error_msg
                
        except Exception as direct_error:
            error_msg = f"直接访问图片失败: {str(direct_error)}"
            init.logger.warn(error_msg)
            return False, error_msg
        
    except Exception as e:
        error_msg = f"下载图片时发生错误: {str(e)}"
        init.logger.error(error_msg)
        return False, error_msg

def get_section_id(section_name):
    section_map = {
        "国产原创": 2,
        "亚洲无码原创": 36,
        "亚洲有码原创": 37,
        "高清中文字幕": 103,
        "素人有码系列": 104,
        "4K原版": 151,
        "VR视频区": 160,
        "欧美无码": 38
    }
    return section_map.get(section_name, 0)


async def sehuatang_spider_start_async():
    """完整的爬虫启动函数，包含浏览器生命周期管理"""
    global browser
    if not init.bot_config.get('sehuatang_spider', {}).get('enable', False):
        return
    today = datetime.datetime.now().date()
    yesterday_str = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    # 初始化全局浏览器
    browser = SeleniumBrowser(get_base_url())
    crawl_finished = False
    section_name = "未知"

    try:
        await browser.init_browser()

        if not browser.driver:
            reason = getattr(browser, "last_error", None) or "请检查 REMOTE_SELENIUM_URL 和远程 Selenium 服务状态"
            message = escape_markdown(f"❌ 浏览器初始化失败！{reason}", version=2)
            add_task_to_queue(init.get_allowed_user(), None, message)
            return

        await apply_configured_cookies()

        # 尝试通过 Cloudflare 验证
        await browser.pass_cloudflare_check()
        crawl_mode = "yesterday"
        sections = init.bot_config['sehuatang_spider'].get('sections', [])
        for section in sections:
            section_name = section.get('name')
            init.logger.info(f"开始爬取 {section_name} 分区...")
            await section_spider(section_name, crawl_mode, today=today)
            init.logger.info(f"{section_name} 分区爬取完成")
            delay = random.uniform(5, 10)
            await asyncio.sleep(delay)
        crawl_finished = True
    except Exception as e:
        init.logger.warn(f"爬取 {section_name} 分区时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭全局浏览器
        await browser.close()

    if not crawl_finished:
        init.logger.warn("涩花爬取未完成，跳过离线任务")
        return

    # 离线到115 (Sync)
    init.logger.info("开始执行涩花离线任务...")
    sehua_offline(yesterday_str)

def sehuatang_spider_start():
    try:
        asyncio.run(sehuatang_spider_start_async())
    except Exception as e:
        init.logger.error(f"涩花爬虫启动失败: {e}")
        
        
async def sehuatang_spider_by_date_async(date, end_date=None):
    """完整的爬虫启动函数，包含浏览器生命周期管理"""
    global browser
    browser = SeleniumBrowser(get_base_url())
    crawl_mode = _normalize_crawl_mode(date, end_date)
    date_label = _format_crawl_mode(crawl_mode)
    crawl_finished = False
    section_name = "未知"

    try:
        await browser.init_browser()
        # 初始化全局浏览器
        if not browser.driver:
            reason = getattr(browser, "last_error", None) or "请检查 REMOTE_SELENIUM_URL 和远程 Selenium 服务状态"
            message = escape_markdown(f"❌ 浏览器初始化失败！{reason}", version=2)
            add_task_to_queue(init.get_allowed_user(), None, message)
            return

        await apply_configured_cookies()

        # 尝试通过 Cloudflare 验证
        await browser.pass_cloudflare_check()
        sections = init.bot_config['sehuatang_spider'].get('sections', [])
        for section in sections:
            section_name = section.get('name')
            init.logger.info(f"开始爬取 {section_name} 分区...")
            await section_spider(section_name, crawl_mode)
            init.logger.info(f"{section_name} 分区爬取完成")
            delay = random.uniform(5, 10)
            await asyncio.sleep(delay)
        crawl_finished = True
    except Exception as e:
        init.logger.warn(f"爬取 {section_name} 分区时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭全局浏览器
        await browser.close()
        try:
            # 离线到115 (Sync)
            if crawl_finished:
                init.logger.info("开始执行涩花离线任务...")
                sehua_offline(date_label)
            else:
                init.logger.warn("涩花爬取未完成，跳过离线任务")
        except Exception as e:
            init.logger.error(f"涩花离线任务执行失败: {e}")
        finally:
            init.CRAWL_SEHUA_STATUS = 0

def sehuatang_spider_by_date(date, end_date=None):
    try:
        asyncio.run(sehuatang_spider_by_date_async(date, end_date))
    except Exception as e:
        init.logger.error(f"涩花爬虫(按日期)启动失败: {e}")
        init.CRAWL_SEHUA_STATUS = 0
    
    
async def section_spider(section_name, date, end_date=None, today=None):
    if today is None:
        today = datetime.datetime.now().date()
    crawl_mode = _normalize_crawl_mode(date, end_date)
    date_label = _format_crawl_mode(crawl_mode)

    update_list = await get_section_update(section_name, crawl_mode, today=today)
    
    if not update_list:
        init.logger.info(f"没有找到 {section_name} 在 {date_label} 的更新内容")
        return
    
    successful_count = 0
    failed_count = 0
    
    results = []

    try:
        for i, topic in enumerate(update_list):
            if isinstance(topic, dict):
                topic_path = topic.get('url')
                topic_date = topic.get('date') or date
            else:
                topic_path = topic
                topic_date = date
            url = _build_full_url(topic_path)
            init.logger.debug(f"正在处理第 {i+1}/{len(update_list)} 个话题: {url}")
            
            success = False
            max_retries = 3
            
            for retry in range(max_retries):
                try:
                    # 添加随机延迟避免被反爬虫
                    if i > 0:  # 第一个请求不延迟
                        delay = random.uniform(2, 5)
                        init.logger.debug(f"等待 {delay:.1f} 秒...")
                        await asyncio.sleep(delay)
                    
                    # 尝试访问页面
                    init.logger.debug(f"  尝试访问 (第 {retry+1} 次)...")
                    await browser.goto(url)
                    
                    # 检查 Cloudflare
                    await browser.pass_cloudflare_check()
                    
                    # 检查 safeid
                    await safeid_check()

                    # 检查年龄验证
                    await age_check()
                    
                    # 等待页面完全加载
                    # await page.wait_for_load_state("networkidle", timeout=60000)
                    
                    html = await browser.get_page_source()
                    if html and len(html) > 1000:  # 确保获取到完整页面
                        result = await parse_topic(section_name, html, url, topic_date)
                        if result and result.get('title'):
                            init.logger.debug(f"成功解析: {result.get('title', 'Unknown')}")
                            results.append(result)
                            successful_count += 1
                        else:
                            init.logger.debug(f"解析失败，内容为空")
                        success = True
                        break
                    else:
                        init.logger.warn(f"页面内容过短，可能加载失败")

                except Exception as e:
                    init.logger.warn(f"第 {retry+1} 次尝试出错: {str(e)}")
                    if retry < max_retries - 1:
                        await asyncio.sleep(5)
            
            if not success:
                init.logger.warn(f"所有重试都失败，跳过此链接")
                failed_count += 1
                
            # 每处理5个页面后增加额外延迟
            if (i + 1) % 5 == 0:
                extra_delay = random.uniform(5, 10)
                init.logger.info(f"已处理 {i+1} 个页面，休息 {extra_delay:.1f} 秒...")
                await asyncio.sleep(extra_delay)
        
        # 写入数据库
        if results:
            save_sehua2db(results)   
            results.clear()
       
    except Exception as e:
        init.logger.warn(f"爬虫过程中发生严重错误: {str(e)}")
    finally:
        init.logger.info(f"本次爬取结束 - 成功: {successful_count}, 失败: {failed_count}")
        # 注意：这里不关闭浏览器，保持cookie
            
async def parse_topic(section_name, html, url, date):
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    result['section_name'] = section_name
    result['publish_date'] = date
    result['pub_url'] = url
    result['save_path'] = get_sehua_save_path(section_name)
    title_tag = soup.find('span', {'id': 'thread_subject'})
    title = title_tag.text if title_tag else None
    if title:
        result['title'] = title
        if section_name == '国产原创':
            result['av_number'] = 'N/A'
        else:
            result['av_number'] = get_av_number_from_title(title)
    
    # 查找主要内容区域 - 使用更精确的选择器
    postmessage = soup.find('td', {'id': lambda x: x and x.startswith('postmessage_')})
    
    if not postmessage:
        # 备用方案：查找包含class="t_f"的td
        postmessage = soup.find('td', class_='t_f')
    
    if postmessage:
        # 获取HTML内容
        content_html = str(postmessage)
        
        # 提取影片容量
        size_match = None
        if '【影片容量】：' in content_html:
            import re
            size_pattern = r'【影片容量】：(.*?)(?:<br[^>]*>|【(?:出演女优|影片名称|是否有码|种子期限|下载工具|影片预览)】)'
            size_search = re.search(size_pattern, content_html)
            if size_search:
                size_match = size_search.group(1).strip()
                size_match = re.sub(r'<[^>]+>', '', size_match).strip()
                size_match = re.sub(r'\s+', ' ', size_match).strip()
        result['size'] = size_match
        
        # 提取是否有码
        type_match = None
        if '【是否有码】：' in content_html:
            import re
            type_pattern = r'【是否有码】：(.*?)(?:<br[^>]*>|【(?:出演女优|影片容量|影片名称|种子期限|下载工具|影片预览)】)'
            type_search = re.search(type_pattern, content_html)
            if type_search:
                type_match = type_search.group(1).strip()
                type_match = re.sub(r'<[^>]+>', '', type_match).strip()
                type_match = re.sub(r'\s+', ' ', type_match).strip()
        result['movie_type'] = type_match
        
        # 提取封面图片URL（从img标签的zoomfile属性）
        img_tag = postmessage.find('img', {'zoomfile': True})
        result['post_url'] = img_tag['zoomfile'] if img_tag else None
        
        # 下载图片到本地保存到tmp（可通过 notify_with_image 配置跳过）
        notify_with_image = init.bot_config.get('sehuatang_spider', {}).get('notify_with_image', True)
        if result['post_url'] and notify_with_image:
            success, local_path = await download_image(result['post_url'], f"{init.TEMP}/sehua")
            if success:
                init.logger.debug(f"图片已下载到: {local_path}")
                result['image_path'] = local_path


        # 提取磁力链接（从blockcode div内的li标签）
        blockcode = postmessage.find('div', class_='blockcode')
        magnet = None
        if blockcode:
            li_tag = blockcode.find('li')
            if li_tag:
                magnet_text = li_tag.get_text().strip()
                # 确保是完整的magnet链接
                if magnet_text.startswith('magnet:'):
                    magnet = magnet_text
        result['magnet'] = magnet
    
    else:
        # 如果找不到主要内容区域，设置默认值
        result = {
            'title': None,
            'size': None,
            'movie_type': None,
            'post_url': None,
            'magnet': None
        }
    
    init.logger.info(f"解析结果: {result}")
    return result


async def get_section_update(section_name, date, end_date=None, today=None):
    if today is None:
        today = datetime.datetime.now().date()
    all_data_today = []
    section_id = get_section_id(section_name)
    if section_id == 0:
        return all_data_today

    crawl_mode = _normalize_crawl_mode(date, end_date)
    date_label = _format_crawl_mode(crawl_mode)

    max_pages = init.bot_config.get('sehuatang_spider', {}).get('max_pages', 50)
    
    try:
        for page_num in range(1, max_pages + 1):
            url = _build_full_url(f"forum.php?mod=forumdisplay&fid={section_id}&page={page_num}")
            init.logger.info(f"正在获取 {section_name} 第 {page_num} 页...")
            
            success = False
            max_retries = 3
            
            for retry in range(max_retries):
                try:
                    if page_num > 1 or retry > 0:  # 第一个请求不延迟
                        delay = random.uniform(5, 10)
                        await asyncio.sleep(delay)
                    
                    # 访问目标页面
                    await browser.goto(url)
                    await browser.pass_cloudflare_check()
                    await safeid_check()
                    await age_check()
                    
                    # 等待页面完全加载
                    await browser.wait_for_element("tbody[id^='normalthread_']")

                    # 获取页面 HTML
                    html = await browser.get_page_source()
                    if html and len(html) > 1000:
                        # 验证页面是否包含预期的内容结构
                        if 'normalthread_' in html or 'postlist' in html:
                            topics, found_dates = parse_section_page(html, crawl_mode, page_num, section_name, today=today)
                            if topics:
                                init.logger.info(f"其中 {len(topics)} 个目标时间范围话题")
                                all_data_today.extend(topics)
                                success = True
                                break

                            if not found_dates:
                                init.logger.info(f"  第 {page_num} 页没有解析到帖子时间，停止翻页")
                                return all_data_today

                            page_is_older, newest_age = _page_is_older_than_crawl_mode(found_dates, crawl_mode, today)
                            if page_is_older:
                                init.logger.info(f"  第 {page_num} 页最新帖子已是 {newest_age} 天前，早于目标时间范围 {date_label}，停止翻页")
                                return all_data_today

                            success = True
                            init.logger.info(f"  第 {page_num} 页包含目标时间范围但无匹配标题，继续翻页")
                            break
                        else:
                            init.logger.warn(f"  页面结构异常，可能仍在加载中")
                            await browser.pass_cloudflare_check()
                    else:
                        init.logger.warn(f"  页面内容过短，可能加载失败")
                        
                except Exception as e:
                    init.logger.warn(f"第 {retry+1} 次尝试出错: {str(e)}")
                    if retry < max_retries - 1:
                        await asyncio.sleep(5)
            
            if not success:
                init.logger.warn(f"第 {page_num} 页获取失败，跳过")
                if page_num == 1:
                     init.logger.error(f"❌ [{section_name}] 分区第1页获取失败，停止当前分区爬取")
                     return []
                break
                
    except Exception as e:
        init.logger.warn(f"获取列表页面时发生错误: {str(e)}")
    init.logger.info(f"总共找到 {len(all_data_today)} 个目标时间范围话题")
    return all_data_today


def _extract_tid(link):
    """从帖子链接中提取 tid，支持 thread-TID-x-x.html 和 ?tid=TID 两种格式"""
    from urllib.parse import urlparse, parse_qs
    # 格式1: thread-123456-1-1.html
    m = re.search(r'thread-(\d+)-', link)
    if m:
        return m.group(1)
    # 格式2: forum.php?mod=viewthread&tid=123456
    qs = parse_qs(urlparse(link).query)
    tid = qs.get('tid', [None])[0]
    return tid


def parse_section_page(html_content, date, page_num, section_name, end_date=None, today=None):
    if today is None:
        today = datetime.datetime.now().date()
    topics = []
    soup = BeautifulSoup(html_content, "html.parser")
    crawl_mode = _normalize_crawl_mode(date, end_date)
    date_label = _format_crawl_mode(crawl_mode)
    
    # 调试信息
    init.logger.debug(f"正在解析时间范围为 {date_label} 的帖子...")
    
    # 查找所有线程
    threads = soup.find_all('tbody', id=lambda x: x and x.startswith('normalthread_'))
    init.logger.info(f"第 {page_num} 页，找到 {len(threads)} 个帖子")

    found_dates = []  # 用于调试，收集找到的所有日期
    date_match_count = 0
    strategy_skip_samples = []
    
    for i, thread in enumerate(threads):
        # 提取日期（从td.by下的em内的span的title属性）
        date_td = thread.find('td', class_='by')
        topic_date = None
        
        if date_td:
            # 在td.by内查找em标签，然后在em内查找有title属性的span
            em_tag = date_td.find('em')
            if em_tag:
                # 查找有title属性的span（不限制class）
                date_span = em_tag.find('span', title=True)
                if date_span:
                    topic_date = date_span.get('title')
                else:
                    topic_date = em_tag.get_text(" ", strip=True)
                if topic_date:
                    found_dates.append(topic_date)
        
        # 提取标题用于调试
        title_link = thread.find('a', class_='s xst')
        title = title_link.text.strip() if title_link else "无标题"
        
        parsed_topic_date = _parse_topic_date(topic_date, today)
        normalized_topic_date = _format_topic_date(topic_date, today)
        if not parsed_topic_date or not _topic_matches_crawl_mode(topic_date, crawl_mode, today):
            continue  # 跳过目标时间范围外的帖子
        date_match_count += 1
            
        # 提前过滤标题
        if not is_title_allowed(section_name, title):
            init.logger.debug(f"标题[{title}]不满足[{section_name}]板块的规则，跳过!")
            if len(strategy_skip_samples) < 3:
                strategy_skip_samples.append(title)
            continue
              
        # 提取链接（从标题的a标签的href属性）
        link = title_link['href'].replace('&amp;', '&') if title_link else ""
        if not link:
            init.logger.info(f"  跳过帖子[{title}]: title_link 未找到（class='s xst' 不匹配?）")
            continue
        topic_id = _extract_tid(link)
        if topic_id:
            topic_link = f"forum.php?mod=viewthread&tid={topic_id}&extra=page%3D1"
            topics.append({"url": topic_link, "date": normalized_topic_date})
            init.logger.info(f"找到目标时间范围帖子: {title}...")
        else:
            init.logger.info(f"  跳过帖子[{title}]: 链接格式无法解析 ({link})")
    
    # 调试信息：显示找到的所有唯一日期
    unique_dates = list(set(found_dates))
    init.logger.debug(f"  页面中找到的日期: {unique_dates}")
    init.logger.debug(f"  目标时间范围: {date_label}")
    init.logger.debug(f"  匹配的目标时间范围帖子数量: {len(topics)}")
    if date_match_count and not topics:
        init.logger.info(f"  第 {page_num} 页日期命中 {date_match_count} 个，但无法加入队列（策略过滤或链接解析失败）")
        for sample in strategy_skip_samples:
            init.logger.info(f"  策略跳过示例: {sample}")
    
    return topics, found_dates


async def age_check():
    try:
        # 等待页面基本加载
        # await browser.wait_for_page_loaded(timeout=30000)
        
        content = await browser.get_page_source()
        init.logger.debug(f"  页面内容长度: {len(content)}")
        # 检测多种可能的年龄验证提示文本
        age_indicators = ["满18岁，请点此进入", "满18岁,请点此进入", "满18岁"]
        if any(ind in content for ind in age_indicators):
            init.logger.info("  检测到年龄验证页面，尝试通过多种方式进入...")
            initial_url = await browser.get_current_url()
            passed = False

            # 尝试多次点击不同文本的按钮
            click_texts = ["满18岁，请点此进入", "满18岁,请点此进入", "点此进入"]
            for attempt in range(3):
                for txt in click_texts:
                    try:
                        await browser.click_text(txt)
                        await asyncio.sleep(1)
                    except Exception:
                        pass

                # 等待页面发生变化或期望元素出现（最长等待 15s）
                for _ in range(15):
                    await asyncio.sleep(1)
                    new_content = await browser.get_page_source()
                    current_url = await browser.get_current_url()
                    if current_url and current_url != initial_url:
                        passed = True
                        break
                    if len(new_content) > len(content) + 200:
                        passed = True
                        break
                    if 'tbody id=' in new_content or 'postlist' in new_content or 'normalthread_' in new_content or 'class="t_f"' in new_content:
                        passed = True
                        break
                if passed:
                    init.logger.info("  年龄验证通过，页面已加载")
                    break

            if not passed:
                init.logger.warn("  页面内容似乎没有变化，可能验证失败")
        else:
            # 即使没有年龄验证，也要等待页面完全加载
            await browser.wait_for_element("tbody[id^='normalthread_']")
            
    except Exception as e:
        init.logger.warn(f"  年龄验证处理出错: {str(e)}")
        # 继续执行，不因为年龄验证失败而中断


async def safeid_check():
    """检查并处理 safeid 验证"""
    try:
        content = await browser.get_page_source()
        if "var safeid" in content:
            init.logger.info("检测到 safeid 变量，尝试提取并添加 Cookie...")
            safeid = extract_safeid(content)
            if safeid:
                init.logger.info(f"提取到 safeid: {safeid}")
                
                # 添加 cookie
                cookie_dict = {
                    'name': '_safe',
                    'value': safeid,
                    'path': '/',
                }
                
                # 在 driver 线程中执行 cookie 添加操作
                await browser.run_with_driver(lambda d: d.add_cookie(cookie_dict))
                
                init.logger.info("safeid cookie 添加成功，刷新页面...")
                await browser.run_with_driver(lambda d: d.refresh())
                await asyncio.sleep(3) # 等待刷新完成
                
                # 再次等待元素加载
                await browser.wait_for_element("tbody[id^='normalthread_']")
            else:
                init.logger.warn("未提取到 valid safeid")
    except Exception as e:
        init.logger.warn(f"safeid 处理出错: {e}")

def extract_safeid(html):
    """提取 safeid"""
    try:
        pattern = r"var\s+safeid\s*=\s*['\"]([^'\"]+)['\"]"
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None

    
        
def get_av_number_from_title(title):
    av_number = ""
    if ' ' in title:
        parts = title.split(' ')
        tmp = parts[0].strip()
        if tmp.endswith('-'):
            tmp = tmp[:-1]
        av_number = tmp.upper()
    return av_number

def get_image_name(image_url):
    parsed = urlparse(image_url)
    filename = Path(parsed.path).name
    return filename


def save_sehua2db(results):
    insert_count = 0
    try:
        with SqlLiteLib() as sqlite:
            for result in results:
                # 检查是否满足爬取策略
                match_strategyed, specify_path = match_strategy(result)
                if not match_strategyed:
                    continue
                # 检查是否已存在（通过磁力链接Hash判断，忽略tracker等参数差异）
                magnet_hash = get_magnet_hash(result.get('magnet'))
                if magnet_hash:
                    # 如果能提取到hash，使用模糊匹配查询
                    sql_check = "select count(*) from sehua_data where magnet LIKE ?"
                    params_check = (f'%{magnet_hash}%', )
                else:
                    # 提取不到hash，回退到完全匹配
                    sql_check = "select count(*) from sehua_data where magnet = ?"
                    params_check = (result.get('magnet'), )

                count = sqlite.query_one(sql_check, params_check)
                if count > 0:
                    init.logger.info(f"[{result.get('title')}]检测到相同磁力链接(Hash: {magnet_hash})已存在，跳过入库！")
                    continue  # 已存在，跳过
                
                # 判断数据完整性
                if not result.get('section_name') or \
                    not result.get('title') or \
                    not result.get('magnet') or \
                    not result.get('size') or \
                    not result.get('movie_type') or \
                    not result.get('post_url') or \
                    not result.get('publish_date') or \
                    not result.get('pub_url') or \
                    not specify_path:
                    init.logger.warn(f"数据不完整，跳过入库: {result}")
                    continue
                
                if check_magnet(result.get('magnet')) is False:
                    init.logger.warn(f"[{result.get('magnet')}]磁力链接格式不正确，跳过入库!")
                    continue
                
                # 插入数据
                insert_query = '''
                INSERT INTO sehua_data (section_name, av_number, title, movie_type, size, magnet, post_url, publish_date, pub_url, image_path, save_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                params_insert = (
                        result.get('section_name'),
                        result.get('av_number'),
                        result.get('title'),
                        result.get('movie_type'),
                        result.get('size'),
                        result.get('magnet'),
                        result.get('post_url'),
                        result.get('publish_date'),
                        result.get('pub_url'),
                        result.get('image_path'),
                        specify_path
                    )
                sqlite.execute_sql(insert_query, params_insert)
                insert_count += 1
                
            init.logger.info(f"涩花[{results[0].get('section_name')}]版块，[{results[0].get('publish_date')}]日，[{insert_count}]条数据入库成功!")
    except Exception as e:
        init.logger.error(f"保存涩花数据到数据库时出错: {str(e)}")
        
        
def _active_strategy_rules(section_name):
    sections = (init.bot_config.get('sehuatang_spider') or {}).get('sections') or []
    for sec in sections:
        if sec.get('name') == section_name:
            rules = sec.get('rules') or []
            return [r for r in rules if r.get('active', True)]
    return []


def _rule_matches(rule, title):
    pattern = rule.get('pattern', '')
    return bool(pattern and re.search(pattern, title, re.IGNORECASE))


def is_title_allowed(section_name, title):
    section_rules = _active_strategy_rules(section_name)
    if not section_rules:
        return True
    include_rules = [rule for rule in section_rules if rule.get('kind', 'include') == 'include']
    for rule in section_rules:
        if rule.get('kind', 'include') == 'exclude' and _rule_matches(rule, title):
            return False
    if not include_rules:
        return True
    for rule in include_rules:
        if _rule_matches(rule, title):
            return True
    return False


def match_strategy(result):
    section_name = result.get('section_name', '')
    section_rules = _active_strategy_rules(section_name)
    if not section_rules:
        return True, result.get('save_path')
    title = result.get('title', '')
    include_rules = [rule for rule in section_rules if rule.get('kind', 'include') == 'include']
    for rule in section_rules:
        if rule.get('kind', 'include') == 'exclude' and _rule_matches(rule, title):
            name = rule.get('name', '未知策略')
            init.logger.info(f"标题[{title}]匹配排除规则[{name}]，跳过!")
            return False, None
    if not include_rules:
        return True, result.get('save_path')
    for rule in include_rules:
        if _rule_matches(rule, title):
            name = rule.get('name', '未知策略')
            init.logger.info(f"标题[{title}]匹配包含规则[{name}]成功!")
            save_path = rule.get('save_path') or result.get('save_path')
            return True, save_path
    return False, None


def get_sehua_save_path(_section_name):
    sections = init.bot_config.get('sehuatang_spider', {}).get('sections', [])
    for section in sections:
        section_name = section.get('name', '')
        if section_name == _section_name:
            return section.get('save_path', f'/AV/涩花/{section_name}')
    return f'/AV/涩花/{_section_name}'


if __name__ == "__main__":
    init.load_yaml_config()
    init.create_logger()
    init.init_db()
    sehuatang_spider_by_date("2025-09-25")
