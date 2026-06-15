"""missav 爬虫：榜单页 → 番号详情 → magnet（中文字幕优先，否则容量最大）。

与 sehuatang_spider 平行，但 missav 是「榜单页」模式（无日期维度），
靠 magnet hash 去重避免重复入库。HTML 抓取走 SeleniumBrowser（内建 FlareSolverr 过 CF）。
"""
import sys
import os

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sys.path.append(current_dir)

import init
import re
import html as htmllib
import time
import random
import asyncio
import datetime
import requests
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from telegram.helpers import escape_markdown

from app.utils.sqlitelib import *
from app.core.selenium_browser import SeleniumBrowser
from app.utils.utils import get_magnet_hash, check_magnet
from app.utils.message_queue import add_task_to_queue
from app.core.missav_offline import missav_offline

# 全局浏览器
browser = None

# 榜单导航词：列表页里这些是分类入口，不是影片详情，需排除
_NAV_WORDS = {
    "english-subtitle", "new", "release", "uncensored-leak", "weekly-hot",
    "monthly-hot", "today-hot", "siro", "luxu", "gana", "maan", "scute",
    "ara", "fc2", "heyzo", "tokyohot", "actresses", "genres", "makers",
    "search", "labels", "series", "chinese-subtitle", "uncensored",
}

# 中文字幕标识：magnet 行文本含其一即视为字幕版。
# missav 详情页字幕行用 [SUB] 标签或 "中文字幕" 文字标注。
# 注意：不能用裸 "字幕"，因为 missav 用 "无字幕" 标注非字幕版，会把它误判成字幕版。
_SUB_MARKERS = ("中文字幕", "[SUB]", "subtitle", "uncensored-leak")


def get_base_url():
    base_url = init.bot_config.get('missav_spider', {}).get('base_url', "missav.ws")
    return base_url or "missav.ws"


def _build_full_url(path: str):
    base = get_base_url().rstrip('/')
    if not base.startswith('http'):
        base = f"https://{base}"
    return f"{base}/{path.lstrip('/')}"


# ---------------------------------------------------------------------------
# 列表页解析：提取番号详情链接
# ---------------------------------------------------------------------------

def _extract_detail_links(html, max_items):
    """从榜单页 HTML 提取影片详情链接，排除分类导航词，去重，取前 max_items 个。"""
    links = []
    seen = set()
    for href in re.findall(r'href="(https://[^"]*missav[^"]*/[^"]+)"', html):
        tail = href.rstrip('/').rsplit('/', 1)[-1].lower()
        if tail in _NAV_WORDS:
            continue
        # 影片详情番号特征：字母+数字（abp-123 / ssis-456 / fc2-ppv-1234567）或纯数字
        if re.match(r"^[a-z0-9]+-[a-z0-9-]*\d+$", tail) or re.match(r"^\d{6,}$", tail):
            if href not in seen:
                seen.add(href)
                links.append(href)
        if len(links) >= max_items:
            break
    return links


# ---------------------------------------------------------------------------
# 详情页解析：选 magnet（中文字幕优先，否则容量最大）
# ---------------------------------------------------------------------------

_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([GMK])B", re.IGNORECASE)


def _parse_size_bytes(text):
    """从行文本解析容量为字节数，解析不到返回 -1。"""
    m = _SIZE_RE.search(text or "")
    if not m:
        return -1
    num = float(m.group(1))
    unit = m.group(2).upper()
    factor = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}.get(unit, 1)
    return int(num * factor)


def _av_number_from_url(url):
    """从 https://missav.ws/en/start-583 提取 START-583。"""
    tail = url.rstrip('/').rsplit('/', 1)[-1]
    return tail.upper()


def _select_best_magnet(soup):
    """遍历详情页所有 magnet 行，按「中文字幕优先，否则容量最大」选一条。

    返回 (magnet, movie_type, size_text)；无 magnet 返回 (None, None, None)。
    """
    candidates = []  # [(magnet, row_text, size_bytes, is_sub)]
    for a in soup.find_all("a", href=re.compile(r"^magnet:")):
        magnet = htmllib.unescape(a.get("href", "")).strip()
        if not magnet.startswith("magnet:"):
            continue
        row = a.find_parent(["tr", "div", "li"]) or a
        row_text = row.get_text(" ", strip=True)
        size_bytes = _parse_size_bytes(row_text)
        is_sub = any(mk in row_text for mk in _SUB_MARKERS)
        candidates.append((magnet, row_text, size_bytes, is_sub))

    if not candidates:
        return None, None, None

    # 优先中文字幕版
    subs = [c for c in candidates if c[3]]
    pool = subs if subs else candidates

    # 在所选池里取容量最大；解析不到容量(-1)的自然排到末尾，全员-1时即取池中第一条
    best = sorted(pool, key=lambda c: c[2], reverse=True)[0]

    magnet, row_text, size_bytes, is_sub = best
    movie_type = "中文字幕" if is_sub else "无字幕"
    size_m = _SIZE_RE.search(row_text)
    size_text = size_m.group(0) if size_m else None
    return magnet, movie_type, size_text


def parse_detail(html, url, list_name):
    """解析详情页，返回入库 dict（含 magnet/title/av_number/post_url 等）。"""
    soup = BeautifulSoup(html, "html.parser")
    result = {
        'list_name': list_name,
        'pub_url': url,
        'av_number': _av_number_from_url(url),
        'publish_date': datetime.datetime.now().strftime("%Y-%m-%d"),
        'save_path': get_save_path(list_name),
    }

    # 标题：优先 og:title / <title>
    title = None
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        title = og["content"].strip()
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
    result['title'] = title or result['av_number']

    # 封面
    post_url = None
    og_img = soup.find("meta", attrs={"property": "og:image"})
    if og_img and og_img.get("content"):
        post_url = og_img["content"].strip()
    result['post_url'] = post_url

    # magnet（核心选择逻辑）
    magnet, movie_type, size_text = _select_best_magnet(soup)
    result['magnet'] = magnet
    result['movie_type'] = movie_type
    result['size'] = size_text

    # 封面下载（可通过 notify_with_image 配置跳过）
    notify_with_image = init.bot_config.get('missav_spider', {}).get('notify_with_image', False)
    if post_url and notify_with_image:
        ok, local_path = _download_image(post_url, f"{init.TEMP}/missav")
        if ok:
            result['image_path'] = local_path

    return result


def _download_image(image_url, save_dir):
    """直接用 requests 下载封面（missav 封面 CDN 通常不在 CF 保护下）。"""
    try:
        os.makedirs(save_dir, exist_ok=True)
        headers = {"User-Agent": init.USER_AGENT, "Referer": f"https://{get_base_url()}/"}
        resp = requests.get(image_url, headers=headers, timeout=60)
        if resp.status_code == 200 and 'image' in resp.headers.get('content-type', '').lower():
            filename = Path(urlparse(image_url).path).name or "cover.jpg"
            path = os.path.join(save_dir, filename)
            with open(path, 'wb') as f:
                f.write(resp.content)
            init.logger.debug(f"[missav] 封面下载成功: {path}")
            return True, path
    except Exception as e:
        init.logger.warn(f"[missav] 封面下载失败: {e}")
    return False, None


# ---------------------------------------------------------------------------
# 榜单爬取
# ---------------------------------------------------------------------------

async def list_spider(list_cfg):
    list_name = list_cfg.get('name', '未知榜单')
    path = list_cfg.get('path', '')
    max_items = init.bot_config.get('missav_spider', {}).get('max_items', 12)

    url = _build_full_url(path)
    init.logger.info(f"[missav] 开始爬取榜单 [{list_name}] {url}")

    try:
        await browser.goto(url)
        await browser.pass_cloudflare_check()
        html = await browser.get_page_source()
    except Exception as e:
        init.logger.error(f"[missav][{list_name}] 榜单页获取失败: {e}")
        return

    if not html or len(html) < 1000:
        init.logger.warn(f"[missav][{list_name}] 榜单页内容过短，跳过")
        return

    detail_links = _extract_detail_links(html, max_items)
    init.logger.info(f"[missav][{list_name}] 提取到 {len(detail_links)} 个番号详情链接")
    if not detail_links:
        return

    results = []
    for i, link in enumerate(detail_links):
        # 提前用番号近似当标题做策略过滤：仅命中“排除”规则才跳过详情页抓取（少触发 CF）。
        # include 规则需真标题才能判定，留到入库 match_strategy 兜底——番号里不会含中文字幕等关键词，
        # 若此处用 is_title_allowed 会把含 include 规则的整张榜单全部误杀。
        av_number = _av_number_from_url(link)
        if _hits_exclude_rule(list_name, av_number):
            init.logger.info(f"[missav] 番号[{av_number}]命中排除规则，跳过详情页抓取")
            continue
        if i > 0:
            await asyncio.sleep(random.uniform(2, 5))
        try:
            await browser.goto(link)
            await browser.pass_cloudflare_check()
            dhtml = await browser.get_page_source()
            if not dhtml or len(dhtml) < 1000:
                init.logger.warn(f"[missav] 详情页内容过短，跳过: {link}")
                continue
            result = parse_detail(dhtml, link, list_name)
            if result.get('magnet'):
                init.logger.info(f"[missav] 解析成功: {result['av_number']} [{result['movie_type']}] {result['size']}")
                results.append(result)
            else:
                init.logger.info(f"[missav] 未找到 magnet，跳过: {result['av_number']}")
        except Exception as e:
            init.logger.warn(f"[missav] 详情页处理出错 {link}: {e}")

        if (i + 1) % 5 == 0:
            await asyncio.sleep(random.uniform(5, 10))

    if results:
        save_missav2db(results)


# ---------------------------------------------------------------------------
# 入库（hash 去重 + 策略过滤）
# ---------------------------------------------------------------------------

def save_missav2db(results):
    insert_count = 0
    try:
        with SqlLiteLib() as sqlite:
            for result in results:
                matched, specify_path = match_strategy(result)
                if not matched:
                    continue

                magnet_hash = get_magnet_hash(result.get('magnet'))
                if magnet_hash:
                    count = sqlite.query_one(
                        "select count(*) from missav_data where magnet LIKE ?",
                        (f'%{magnet_hash}%',))
                else:
                    count = sqlite.query_one(
                        "select count(*) from missav_data where magnet = ?",
                        (result.get('magnet'),))
                if count > 0:
                    init.logger.info(f"[missav][{result.get('av_number')}] magnet 已存在(Hash:{magnet_hash})，跳过入库")
                    continue

                if not result.get('list_name') or not result.get('title') or \
                        not result.get('magnet') or not specify_path:
                    init.logger.warn(f"[missav] 数据不完整，跳过入库: {result.get('av_number')}")
                    continue

                if check_magnet(result.get('magnet')) is False:
                    init.logger.warn(f"[missav] magnet 格式不正确，跳过: {result.get('magnet')}")
                    continue

                sqlite.execute_sql(
                    '''INSERT INTO missav_data
                       (list_name, av_number, title, movie_type, size, magnet,
                        post_url, publish_date, pub_url, image_path, save_path)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (result.get('list_name'), result.get('av_number'), result.get('title'),
                     result.get('movie_type'), result.get('size'), result.get('magnet'),
                     result.get('post_url'), result.get('publish_date'), result.get('pub_url'),
                     result.get('image_path'), specify_path))
                insert_count += 1
            init.logger.info(f"[missav][{results[0].get('list_name')}] {insert_count} 条数据入库成功")
    except Exception as e:
        init.logger.error(f"[missav] 保存数据到数据库出错: {e}")


# ---------------------------------------------------------------------------
# 策略匹配（仿 sehua，读 missav_spider.lists[].rules）
# ---------------------------------------------------------------------------

def _active_strategy_rules(list_name):
    lists = (init.bot_config.get('missav_spider') or {}).get('lists') or []
    for lst in lists:
        if lst.get('name') == list_name:
            rules = lst.get('rules') or []
            return [r for r in rules if r.get('active', True)]
    return []


def _rule_matches(rule, title):
    pattern = rule.get('pattern', '')
    return bool(pattern and re.search(pattern, title, re.IGNORECASE))


def _hits_exclude_rule(list_name, text):
    """text 是否命中任一“排除”规则。用于列表页提前过滤（仅 exclude 安全，番号不含 include 关键词）。"""
    for r in _active_strategy_rules(list_name):
        if r.get('kind', 'include') == 'exclude' and _rule_matches(r, text):
            return True
    return False


def is_title_allowed(list_name, title):
    rules = _active_strategy_rules(list_name)
    if not rules:
        return True
    if _hits_exclude_rule(list_name, title):
        return False
    include_rules = [r for r in rules if r.get('kind', 'include') == 'include']
    if not include_rules:
        return True
    return any(_rule_matches(r, title) for r in include_rules)


def match_strategy(result):
    list_name = result.get('list_name', '')
    rules = _active_strategy_rules(list_name)
    if not rules:
        return True, result.get('save_path')
    title = result.get('title', '')
    include_rules = [r for r in rules if r.get('kind', 'include') == 'include']
    for r in rules:
        if r.get('kind', 'include') == 'exclude' and _rule_matches(r, title):
            init.logger.info(f"[missav] 标题[{title}]匹配排除规则[{r.get('name','')}]，跳过")
            return False, None
    if not include_rules:
        return True, result.get('save_path')
    for r in include_rules:
        if _rule_matches(r, title):
            return True, r.get('save_path') or result.get('save_path')
    return False, None


def get_save_path(list_name):
    lists = init.bot_config.get('missav_spider', {}).get('lists', [])
    for lst in lists:
        if lst.get('name') == list_name:
            return lst.get('save_path', f'/AV/missav/{list_name}')
    return f'/AV/missav/{list_name}'


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

async def _run_all_lists():
    global browser
    browser = SeleniumBrowser(get_base_url())
    crawl_finished = False
    try:
        await browser.init_browser()
        if not browser.driver:
            reason = getattr(browser, "last_error", None) or "请检查 FlareSolverr / 远程 Selenium 服务状态"
            add_task_to_queue(init.get_allowed_user(), None,
                              escape_markdown(f"❌ missav 浏览器初始化失败！{reason}", version=2))
            return
        await browser.pass_cloudflare_check()
        lists = init.bot_config.get('missav_spider', {}).get('lists', [])
        for lst in lists:
            await list_spider(lst)
            await asyncio.sleep(random.uniform(5, 10))
        crawl_finished = True
    except Exception as e:
        init.logger.warn(f"[missav] 爬取过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser.close()

    if crawl_finished:
        init.logger.info("[missav] 爬取完成，开始离线任务...")
        missav_offline()
    else:
        init.logger.warn("[missav] 爬取未完成，跳过离线任务")


async def missav_spider_start_async():
    if not init.bot_config.get('missav_spider', {}).get('enable', False):
        return
    await _run_all_lists()


def missav_spider_start():
    """调度入口"""
    try:
        asyncio.run(missav_spider_start_async())
    except Exception as e:
        init.logger.error(f"[missav] 爬虫启动失败: {e}")


def missav_spider_manual():
    """TG / Web 手动触发入口"""
    try:
        asyncio.run(_run_all_lists())
    except Exception as e:
        init.logger.error(f"[missav] 手动爬虫启动失败: {e}")
    finally:
        init.CRAWL_MISSAV_STATUS = 0


if __name__ == "__main__":
    init.load_yaml_config()
    init.create_logger()
    init.init_db()
    asyncio.run(_run_all_lists())
