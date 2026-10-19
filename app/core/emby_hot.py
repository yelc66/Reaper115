"""Emby 热门合集：把 missav 今日/本周/本月热门榜单里「库中已有」的番号同步成 Emby 合集(BoxSet)。

只抓榜单页拿番号（不进详情页、不下载），按 organize 的番号解析规则匹配 Emby 条目，
然后让合集成员与当前榜单保持一致（新增上榜的加入，掉榜的移除）。默认关闭。

配置 (config.yaml):
emby:
  enabled: false
  url: http://192.168.3.2:8096
  api_key: xxx
  user_id: ""            # 可选；填写后用 /Users/{id}/Items 查询
  sync_time: "05:00"
  max_items: 48          # 每个榜单取前 N 个（自动翻页）
  auto_download: false   # 缺失番号自动下载
  download_source_order: [sehuatang, missav]
  collections:
    today-hot: 今日热门
    weekly-hot: 本周热门
    monthly-hot: 本月热门
  list_paths:            # 可选，覆盖榜单路径（base_url 取 missav_spider.base_url）
    today-hot: dm296/en/today-hot
"""
import asyncio
import os
import random
import re
from typing import Dict, List, Optional

import requests

from app.core.organize import parse_video_name

DEFAULT_COLLECTIONS = {"today-hot": "今日热门", "weekly-hot": "本周热门", "monthly-hot": "本月热门"}
DEFAULT_LIST_PATHS = {"today-hot": "dm296/en/today-hot", "weekly-hot": "dm170/en/weekly-hot", "monthly-hot": "dm266/en/monthly-hot"}
_MISSAV_TAIL_RE = re.compile(r'-(?:uncensored-leak|chinese-subtitle|english-subtitle)$', re.I)


def normalize_number(text: str, context: str = "") -> Optional[str]:
    """番号/文件名/路径 -> 标准番号（与 organize 相同规则）。识别不了返回 None。"""
    if not text:
        return None
    base = os.path.basename(text.replace('\\', '/'))
    base = _MISSAV_TAIL_RE.sub('', base.rsplit('.', 1)[0] if '.' in base[-6:] else base)
    p = parse_video_name(base + ".mp4", context)
    return p.number.upper() if p else None


def numbers_from_list_html(html: str, max_items: int) -> List[str]:
    """榜单页 HTML -> 按排名去重的番号列表（复用 missav_spider 的列表解析）。"""
    from app.core.missav_spider import _extract_detail_links, _av_number_from_url
    out = []
    for link in _extract_detail_links(html, max_items):
        n = normalize_number(_av_number_from_url(link))
        if n and n not in out:
            out.append(n)
    return out


class EmbyClient:
    def __init__(self, url: str, api_key: str, user_id: str = "", session=None, timeout: int = 20):
        self.url = url.rstrip('/')
        self.user_id = user_id or ""
        self.s = session or requests.Session()
        self.s.headers.update({"X-Emby-Token": api_key, "Accept": "application/json"})
        self.timeout = timeout

    def _req(self, method, path, **params):
        r = self.s.request(method, f"{self.url}{path}", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json() if r.content and 'json' in r.headers.get('Content-Type', 'application/json') else None

    def _items(self, **params):
        path = f"/Users/{self.user_id}/Items" if self.user_id else "/Items"
        return (self._req("GET", path, Recursive="true", **params) or {}).get("Items", [])

    def find_items(self, number: str) -> List[str]:
        """按番号搜索影片，Name/Path 解析后番号一致才算命中。返回 item id 列表（多版本都返回）。"""
        found = []
        for it in self._items(SearchTerm=number, IncludeItemTypes="Movie,Video", Fields="Path"):
            path = it.get("Path") or ""
            parent = os.path.basename(os.path.dirname(path.replace('\\', '/')))
            cands = [normalize_number(path, parent), normalize_number(it.get("Name", ""))]
            if number.upper() in cands:
                found.append(it["Id"])
        return found

    def find_collection(self, name: str) -> Optional[str]:
        for it in self._items(IncludeItemTypes="BoxSet", SearchTerm=name):
            if it.get("Name") == name:
                return it["Id"]
        return None

    def collection_items(self, cid: str) -> List[str]:
        return [it["Id"] for it in self._items(ParentId=cid)]

    def create_collection(self, name: str, ids: List[str]) -> str:
        return self._req("POST", "/Collections", Name=name, Ids=",".join(ids))["Id"]

    def add_items(self, cid: str, ids: List[str]):
        self._req("POST", f"/Collections/{cid}/Items", Ids=",".join(ids))

    def remove_items(self, cid: str, ids: List[str]):
        self._req("DELETE", f"/Collections/{cid}/Items", Ids=",".join(ids))


def sync_collection(client: EmbyClient, name: str, ranked_numbers: List[str], log=None) -> Dict:
    """让合集 name 只包含 ranked_numbers 中库里已有的条目。返回统计。"""
    want, missing = [], []
    for n in ranked_numbers:
        ids = client.find_items(n)
        if ids:
            want.extend(i for i in ids if i not in want)
        else:
            missing.append(n)
    cid = client.find_collection(name)
    added, removed = [], []
    if cid is None:
        if want:
            cid = client.create_collection(name, want)
            added = list(want)
    else:
        have = client.collection_items(cid)
        added = [i for i in want if i not in have]
        removed = [i for i in have if i not in want]
        if added:
            client.add_items(cid, added)
        if removed:
            client.remove_items(cid, removed)
    res = {"collection": name, "id": cid, "owned": len(want), "missing": missing, "added": len(added), "removed": len(removed)}
    if log:
        log.info(f"[Emby热门] {name}: 库中 {len(want)} 条，新增 {len(added)}，移除 {len(removed)}，缺失 {len(missing)} {missing}")
    return res


def page_url(base: str, path: str, page: int) -> str:
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    if page <= 1:
        return url
    return f"{url}{'&' if '?' in url else '?'}page={page}"


async def collect_ranked(fetch_page, max_items: int, max_pages: int = 10) -> List[str]:
    """按页抓取榜单直到凑满 max_items：fetch_page(page) -> html。某页没有新番号即停止。"""
    out: List[str] = []
    for page in range(1, max_pages + 1):
        html = await fetch_page(page) or ""
        new = [n for n in numbers_from_list_html(html, 1000) if n not in out]
        if not new:
            break
        out.extend(new)
        if len(out) >= max_items:
            break
    return out[:max_items]


async def _fetch_rankings(keys, cfg, base_url, log):
    from app.core.selenium_browser import SeleniumBrowser
    paths = {**DEFAULT_LIST_PATHS, **(cfg.get("list_paths") or {})}
    max_items = int(cfg.get("max_items", 48))
    max_pages = int(cfg.get("max_pages", 10))
    browser = SeleniumBrowser(base_url)
    out = {}
    try:
        await browser.init_browser()
        if not browser.driver:
            raise RuntimeError(getattr(browser, "last_error", None) or "浏览器初始化失败")
        await browser.pass_cloudflare_check()
        base = base_url if base_url.startswith("http") else f"https://{base_url}"
        for k in keys:
            async def fetch(page, _k=k):
                if page > 1:
                    await asyncio.sleep(random.uniform(2, 4))
                await browser.goto(page_url(base, paths[_k], page))
                await browser.pass_cloudflare_check()
                return await browser.get_page_source()
            out[k] = await collect_ranked(fetch, max_items, max_pages)
            log.info(f"[Emby热门] 榜单 {k}: {len(out[k])} 个 {out[k]}")
            await asyncio.sleep(3)
    finally:
        await browser.close()
    return out


def run_emby_hot(force: bool = False):
    """调度/手动入口。force=True 时忽略 enabled（手动触发仍需配置 url/api_key）。
    返回每个合集的统计；开启 auto_download 时附加 {"auto_download": [...]}。"""
    import init
    cfg = init.bot_config.get("emby") or {}
    if not (cfg.get("enabled") or force):
        return None
    if not cfg.get("url") or not cfg.get("api_key"):
        init.logger.warn("[Emby热门] 未配置 emby.url / emby.api_key，跳过")
        return None
    cols = cfg.get("collections") or DEFAULT_COLLECTIONS
    base_url = (init.bot_config.get("missav_spider") or {}).get("base_url") or "missav.ws"
    try:
        ranks = asyncio.run(_fetch_rankings(list(cols), cfg, base_url, init.logger))
        client = EmbyClient(cfg["url"], cfg["api_key"], cfg.get("user_id", ""))
        results = [dict(sync_collection(client, cols[k], ranks.get(k, []), init.logger), ranked=len(ranks.get(k, [])))
                   for k in cols if ranks.get(k)]
    except Exception as e:
        init.logger.error(f"[Emby热门] 同步失败: {e}")
        return None
    if cfg.get("auto_download"):
        missing = []
        for r in results:
            missing.extend(n for n in r["missing"] if n not in missing)
        try:
            from app.core.emby_hot_download import download_missing
            dl = download_missing(missing, cfg)
        except Exception as e:
            init.logger.error(f"[Emby热门下载] 失败: {e}")
            dl = [{"status": "error", "msg": str(e)}]
        results.append({"auto_download": dl})
    return results
