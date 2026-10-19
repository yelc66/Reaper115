"""Emby 热门榜单缺失番号自动下载（emby.auto_download，默认关闭）。

对每个「上榜但 Emby 库中没有」的番号：
  1. 按 emby.download_source_order（默认 ['sehuatang', 'missav']）依次找 magnet：
     - sehuatang：站内搜索番号，优先「高清中文字幕」版块 / 标题含中文字幕的帖子，再看其它帖子；
       进帖子用 sehuatang_spider.parse_topic 取 magnet
     - missav：详情页用 missav_spider.parse_detail（中文字幕 + UC 优先，同优先度按清晰度）
  2. 写入 sehua_data / missav_data 并立即提交 115 离线，标记 is_download=1，
     启动对应的后处理轮询（广告清理 → 重命名 → organize 整理到 /涩花/整理）。
  3. 每个番号记入 emby_hot_attempts 表，retry_days 天内不再重复尝试。
"""
import asyncio
import datetime
import random
import re
import sqlite3
from typing import Callable, Dict, List, Optional

SEHUA_PREFERRED_FID = 103  # 高清中文字幕
SEHUA_FID_NAMES = {2: "国产原创", 36: "亚洲无码原创", 37: "亚洲有码原创", 103: "高清中文字幕",
                   104: "素人有码系列", 151: "4K原版", 160: "VR视频区", 38: "欧美无码",
                   143: "求片问答", 166: "AI专区"}
# 只有这些资源版块的帖子才可能直接带 magnet；求片区(143)/AI专区(166) 等一律排除
SEHUA_RESOURCE_FIDS = (103, 151, 37, 36, 104, 2, 160, 38)
_SEHUA_LOCK_MARKERS = ("隐藏", "本帖隐藏", "锁定", "locked", "抱歉，本帖要求阅读权限", "没有权限")


def sehua_topic_skip_reason(html: str) -> Optional[str]:
    """帖子页面被锁/隐藏/无权限时返回原因，否则 None。"""
    if not html:
        return "页面为空"
    if "blockcode" in html or "magnet:?" in html:
        return None
    for m in _SEHUA_LOCK_MARKERS:
        if m in html:
            return f"帖子含「{m}」"
    return None

_ATTEMPT_DDL = """CREATE TABLE IF NOT EXISTS emby_hot_attempts (
    av_number TEXT PRIMARY KEY,
    last_try DATETIME,
    source TEXT,
    status TEXT,       -- submitted / not_found / submit_failed
    detail TEXT
)"""


# ---------------------------------------------------------------------------
# 尝试记录（去重）
# ---------------------------------------------------------------------------

class AttemptStore:
    def __init__(self, db_file: str):
        self.db_file = db_file
        with sqlite3.connect(db_file) as c:
            c.execute(_ATTEMPT_DDL)

    def recently_tried(self, number: str, days: int, now=None) -> bool:
        now = now or datetime.datetime.now()
        with sqlite3.connect(self.db_file) as c:
            row = c.execute("SELECT last_try FROM emby_hot_attempts WHERE av_number=?", (number,)).fetchone()
        if not row or not row[0]:
            return False
        try:
            last = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return False
        return now - last < datetime.timedelta(days=days)

    def record(self, number: str, source: str, status: str, detail: str = "", now=None):
        ts = (now or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_file) as c:
            c.execute("INSERT OR REPLACE INTO emby_hot_attempts (av_number,last_try,source,status,detail) VALUES (?,?,?,?,?)",
                      (number, ts, source, status, detail[:500]))


# ---------------------------------------------------------------------------
# sehuatang 搜索结果解析（纯函数）
# ---------------------------------------------------------------------------

_TID_RE = re.compile(r'(?:thread-(\d+)-\d+-\d+\.html|mod=viewthread(?:&amp;|&)tid=(\d+))')
_FID_RE = re.compile(r'(?:forum-(\d+)-\d+\.html|mod=forumdisplay(?:&amp;|&)fid=(\d+))')


def _strip_tags(s: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s)).strip()


def parse_sehua_search(html: str) -> List[Dict]:
    """Discuz 搜索结果页 -> [{tid, title, fid}]（按页面顺序）。"""
    out, seen = [], set()
    blocks = re.split(r'<li[^>]*class="pbw"', html)[1:] or [html]
    for b in blocks:
        h3 = re.search(r'<h3[^>]*>(.*?)</h3>', b, re.S)
        scope = h3.group(1) if h3 else b
        m = _TID_RE.search(scope)
        if not m:
            continue
        tid = m.group(1) or m.group(2)
        if tid in seen:
            continue
        seen.add(tid)
        title = _strip_tags(scope)
        f = _FID_RE.search(b)
        fid = int(f.group(1) or f.group(2)) if f else 0
        out.append({"tid": tid, "title": title, "fid": fid})
    return out


def rank_sehua_candidates(results: List[Dict], number: str, normalize: Callable[[str], Optional[str]]) -> List[Dict]:
    """只保留标题番号与目标一致的帖子；中文字幕版块/标题优先。"""
    hits = []
    for r in results:
        if r.get("fid") not in SEHUA_RESOURCE_FIDS:
            continue
        title = r.get("title", "")
        first = title.split(" ")[0] if title else ""
        if normalize(first) != number and normalize(title) != number:
            continue
        sub = r.get("fid") == SEHUA_PREFERRED_FID or "中文字幕" in title or "中字" in title
        hits.append((0 if sub else 1, r))
    hits.sort(key=lambda x: x[0])
    return [r for _, r in hits]


# ---------------------------------------------------------------------------
# 主流程（依赖可注入，便于测试）
# ---------------------------------------------------------------------------

class HotDownloader:
    """finders: {source: async fn(number) -> result dict | None}；
    submit: fn(source, number, result) -> (ok, msg)；notify: fn(text)。"""

    def __init__(self, cfg: dict, store: AttemptStore, finders: Dict[str, Callable], submit: Callable,
                 notify: Callable, log, sleep=asyncio.sleep):
        self.cfg = cfg or {}
        self.store = store
        self.finders = finders
        self.submit = submit
        self.notify = notify
        self.log = log
        self.sleep = sleep
        self.order = [s for s in (self.cfg.get("download_source_order") or ["sehuatang", "missav"]) if s in finders]
        self.retry_days = int(self.cfg.get("retry_days", 7))
        self.max_per_run = int(self.cfg.get("max_downloads_per_run", 10))

    async def run(self, missing: List[str]) -> List[Dict]:
        report, done = [], 0
        for number in missing:
            if done >= self.max_per_run:
                report.append({"number": number, "status": "skipped_limit"})
                continue
            if self.store.recently_tried(number, self.retry_days):
                report.append({"number": number, "status": "skipped_recent"})
                continue
            done += 1
            found, src, errors = None, None, []
            for s in self.order:
                try:
                    found = await self.finders[s](number)
                except Exception as e:  # 单源失败不影响其它源
                    errors.append(f"{s}: {e}")
                    found = None
                if found and found.get("magnet"):
                    src = s
                    break
                await self.sleep(random.uniform(2, 4))
            if not src:
                self.store.record(number, ",".join(self.order), "not_found", "; ".join(errors))
                self.log.info(f"[Emby热门下载] {number} 各来源均未找到 magnet {errors}")
                report.append({"number": number, "status": "not_found", "errors": errors})
                continue
            ok, msg = self.submit(src, number, found)
            status = "submitted" if ok else "submit_failed"
            self.store.record(number, src, status, msg or "")
            self.log.info(f"[Emby热门下载] {number} 来源 {src} -> {status} {msg or ''}")
            if ok:
                self.notify(f"🔥 热门补全：{number} 已提交离线（来源 {src}）\n{found.get('title') or ''}")
            report.append({"number": number, "status": status, "source": src, "title": found.get("title"), "msg": msg})
            await self.sleep(random.uniform(2, 5))
        return report


# ---------------------------------------------------------------------------
# 运行时实现（依赖 init / selenium / 115）
# ---------------------------------------------------------------------------

def _make_runtime(cfg, log):  # pragma: no cover - 需要真实环境
    import init
    from app.core import sehuatang_spider as sh
    from app.core import missav_spider as mv
    from app.core.selenium_browser import SeleniumBrowser
    from app.core.emby_hot import normalize_number

    state = {}

    async def _sehua_browser():
        if "sh" not in state:
            b = SeleniumBrowser(sh.get_base_url())
            await b.init_browser()
            if not b.driver:
                raise RuntimeError(getattr(b, "last_error", None) or "sehuatang 浏览器初始化失败")
            sh.browser = b
            await sh.apply_configured_cookies()
            await b.pass_cloudflare_check()
            state["sh"] = b
        return state["sh"]

    async def _missav_browser():
        if "mv" not in state:
            b = SeleniumBrowser(mv.get_base_url())
            await b.init_browser()
            if not b.driver:
                raise RuntimeError(getattr(b, "last_error", None) or "missav 浏览器初始化失败")
            mv.browser = b
            await b.pass_cloudflare_check()
            state["mv"] = b
        return state["mv"]

    async def _goto(b, url, sehua=False):
        await b.goto(url)
        await b.pass_cloudflare_check()
        if sehua:
            await sh.safeid_check()
            await sh.age_check()
        return await b.get_page_source() or ""

    async def find_sehuatang(number):
        b = await _sehua_browser()
        html = await _goto(b, sh._build_full_url(f"search.php?mod=forum&searchsubmit=yes&srchtxt={number}"), True)
        cands = rank_sehua_candidates(parse_sehua_search(html), number, normalize_number)
        for c in cands[:3]:
            await asyncio.sleep(random.uniform(2, 4))
            url = sh._build_full_url(f"forum.php?mod=viewthread&tid={c['tid']}")
            section = SEHUA_FID_NAMES.get(c["fid"], "高清中文字幕")
            page = await _goto(b, url, True)
            reason = sehua_topic_skip_reason(page)
            if reason:
                log.info(f"[emby_hot] {number} 跳过 sehuatang tid={c['tid']} ({section}): {reason}")
                continue
            res = await sh.parse_topic(section, page, url,
                                       datetime.datetime.now().strftime("%Y-%m-%d"))
            if res and res.get("magnet"):
                res["section_name"] = section
                res["av_number"] = number
                return res
        return None

    async def find_missav(number):
        b = await _missav_browser()
        url = mv._build_full_url(f"cn/{number.lower()}")
        html = await _goto(b, url)
        if len(html) < 1000:
            return None
        res = mv.parse_detail(html, url, cfg.get("missav_list_name", "Emby热门补全"))
        res["av_number"] = number
        return res if res.get("magnet") else None

    def submit(source, number, res):
        from app.utils.sqlitelib import SqlLiteLib
        from app.utils.utils import check_magnet
        if init.openapi_115 is None:
            return False, "115 未授权"
        magnet = res["magnet"]
        if check_magnet(magnet) is False:
            return False, "magnet 格式不正确"
        if source == "sehuatang":
            table, key = "sehua_data", "section_name"
            save_path = cfg.get("download_save_path") or sh.get_sehua_save_path(res["section_name"])
        else:
            table, key = "missav_data", "list_name"
            save_path = cfg.get("download_save_path") or mv.get_save_path(res.get("list_name", ""))
        if not init.openapi_115.offline_download_specify_path(magnet, save_path):
            return False, f"115 离线提交失败 ({save_path})"
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with SqlLiteLib() as sqlite:
            sqlite.execute_sql(
                f"""INSERT INTO {table} ({key}, av_number, title, movie_type, size, magnet, post_url,
                    publish_date, pub_url, image_path, save_path, is_download, submitted_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,1,?)""",
                (res.get(key), number, res.get("title") or number, res.get("movie_type"), res.get("size"), magnet,
                 res.get("post_url"), res.get("publish_date") or now[:10], res.get("pub_url"),
                 res.get("image_path"), save_path, now))
        if source == "sehuatang":
            from app.core.offline_task_retry import start_post_process_watcher
        else:
            from app.core.missav_offline import start_post_process_watcher
        start_post_process_watcher()
        return True, save_path

    def notify(text):
        from app.utils.message_queue import add_task_to_queue
        from telegram.helpers import escape_markdown
        add_task_to_queue(init.get_allowed_user(), None, escape_markdown(text, version=2))

    async def close():
        for b in state.values():
            try:
                await b.close()
            except Exception:
                pass

    finders = {"sehuatang": find_sehuatang, "missav": find_missav}
    return finders, submit, notify, close


def download_missing(missing: List[str], cfg: dict):  # pragma: no cover - 需要真实环境
    import init
    if not missing:
        return []
    store = AttemptStore(init.DB_FILE)
    finders, submit, notify, close = _make_runtime(cfg, init.logger)

    async def _go():
        try:
            return await HotDownloader(cfg, store, finders, submit, notify, init.logger).run(missing)
        finally:
            await close()
    return asyncio.run(_go())
