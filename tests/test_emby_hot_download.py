import asyncio, datetime, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import test_emby_hot  # noqa: F401,E402  注入 missav_spider 替身
from app.core import emby_hot as eh
from app.core import emby_hot_download as hd


class Log:
    def __getattr__(self, n): return lambda *a, **k: None


async def _nosleep(_): return None


def test_page_url():
    assert eh.page_url("https://missav.ws", "dm296/en/today-hot", 1) == "https://missav.ws/dm296/en/today-hot"
    assert eh.page_url("https://missav.ws/", "/dm296/en/today-hot", 3) == "https://missav.ws/dm296/en/today-hot?page=3"
    assert eh.page_url("https://x", "a?sort=v", 2) == "https://x/a?sort=v&page=2"


def _page(tags):
    return "".join(f'<a href="https://missav.ws/en/{t}">x</a>' for t in tags)


def test_collect_ranked_paginates_until_max():
    pages = {1: _page([f"abc-{i:03d}" for i in range(1, 13)]), 2: _page([f"abc-{i:03d}" for i in range(13, 25)]),
             3: _page([f"abc-{i:03d}" for i in range(25, 37)])}
    calls = []
    async def fetch(p): calls.append(p); return pages.get(p, "")
    out = asyncio.run(eh.collect_ranked(fetch, 20))
    assert len(out) == 20 and out[0] == "ABC-001" and out[-1] == "ABC-020" and calls == [1, 2]


def test_collect_ranked_stops_on_repeat_or_empty():
    same = _page(["abc-001", "abc-002"])
    async def fetch(p): return same
    assert asyncio.run(eh.collect_ranked(fetch, 48)) == ["ABC-001", "ABC-002"]


SEARCH_HTML = '''
<li class="pbw" id="1"><h3 class="xs3"><a href="forum.php?mod=viewthread&amp;tid=111" target="_blank">MIDA-117 无字幕版</a></h3>
<p><a href="forum.php?mod=forumdisplay&amp;fid=37" class="xi1">亚洲有码原创</a></p></li>
<li class="pbw" id="2"><h3 class="xs3"><a href="thread-222-1-1.html"><strong><font color="#ff0000">MIDA-117</font></strong> [中文字幕] 标题</a></h3>
<p><a href="forum-103-1.html">高清中文字幕</a></p></li>
<li class="pbw" id="3"><h3 class="xs3"><a href="thread-333-1-1.html">MIDA-1170 别的片</a></h3><p><a href="forum-37-1.html">x</a></p></li>
'''


def test_parse_and_rank_sehua_search():
    res = hd.parse_sehua_search(SEARCH_HTML)
    assert [(r["tid"], r["fid"]) for r in res] == [("111", 37), ("222", 103), ("333", 37)]
    ranked = hd.rank_sehua_candidates(res, "MIDA-117", eh.normalize_number)
    assert [r["tid"] for r in ranked] == ["222", "111"]


def test_attempt_store(tmp_path):
    st = hd.AttemptStore(str(tmp_path / "db.db"))
    now = datetime.datetime(2026, 10, 19, 12, 0, 0)
    assert not st.recently_tried("ABC-001", 7, now)
    st.record("ABC-001", "missav", "submitted", now=now)
    assert st.recently_tried("ABC-001", 7, now + datetime.timedelta(days=6))
    assert not st.recently_tried("ABC-001", 7, now + datetime.timedelta(days=8))


def _run(tmp_path, cfg, finders, submit_ok=True):
    st = hd.AttemptStore(str(tmp_path / "db.db"))
    submitted, notes = [], []
    def submit(src, n, res):
        submitted.append((src, n, res["magnet"]))
        return (submit_ok, "/AV/x")
    d = hd.HotDownloader(cfg, st, finders, submit, notes.append, Log(), sleep=_nosleep)
    return d, st, submitted, notes


def test_downloader_source_order_and_fallback(tmp_path):
    seen = []
    async def sh(n):
        seen.append(("sehuatang", n))
        return {"magnet": "magnet:?xt=urn:btih:AAA", "title": n} if n == "ABC-001" else None
    async def mv(n):
        seen.append(("missav", n))
        return {"magnet": "magnet:?xt=urn:btih:BBB", "title": n} if n == "ABC-002" else None
    d, st, submitted, notes = _run(tmp_path, {}, {"sehuatang": sh, "missav": mv})
    rep = asyncio.run(d.run(["ABC-001", "ABC-002", "ABC-003"]))
    assert [(r["number"], r["status"], r.get("source")) for r in rep] == [
        ("ABC-001", "submitted", "sehuatang"), ("ABC-002", "submitted", "missav"), ("ABC-003", "not_found", None)]
    assert ("missav", "ABC-001") not in seen  # 涩花命中后不再查 missav
    assert len(notes) == 2 and len(submitted) == 2
    # 再跑一次：全部在 retry_days 内，跳过
    rep2 = asyncio.run(d.run(["ABC-001", "ABC-003"]))
    assert [r["status"] for r in rep2] == ["skipped_recent", "skipped_recent"]


def test_downloader_custom_order_limit_and_errors(tmp_path):
    async def sh(n): raise RuntimeError("cf blocked")
    async def mv(n): return {"magnet": "magnet:?xt=urn:btih:CCC"}
    d, st, submitted, _ = _run(tmp_path, {"download_source_order": ["missav", "sehuatang"], "max_downloads_per_run": 1},
                               {"sehuatang": sh, "missav": mv})
    rep = asyncio.run(d.run(["A-1", "B-2"]))
    assert rep[0]["source"] == "missav" and rep[1]["status"] == "skipped_limit"
    d2, *_ = _run(tmp_path, {"download_source_order": ["sehuatang"]}, {"sehuatang": sh, "missav": mv})
    r = asyncio.run(d2.run(["C-3"]))[0]
    assert r["status"] == "not_found" and "cf blocked" in r["errors"][0]


def test_downloader_submit_failure_recorded(tmp_path):
    async def mv(n): return {"magnet": "magnet:?xt=urn:btih:DDD"}
    d, st, _, notes = _run(tmp_path, {"download_source_order": ["missav"]}, {"missav": mv}, submit_ok=False)
    assert asyncio.run(d.run(["D-4"]))[0]["status"] == "submit_failed" and not notes
    assert st.recently_tried("D-4", 7)


def test_rank_sehua_whitelist_filters_before_topn():
    res = [{"tid": str(i), "title": "MIDA-117 求片", "fid": 143} for i in range(3)] + \
          [{"tid": "9", "title": "MIDA-117 AI", "fid": 166},
           {"tid": "10", "title": "MIDA-117 有码", "fid": 37}]
    ranked = hd.rank_sehua_candidates(res, "MIDA-117", eh.normalize_number)
    assert [r["tid"] for r in ranked] == ["10"]
    assert hd.SEHUA_FID_NAMES[143] == "求片问答" and hd.SEHUA_FID_NAMES[166] == "AI专区"


def test_sehua_topic_skip_reason():
    assert hd.sehua_topic_skip_reason("<div>本帖隐藏的内容</div>")
    assert hd.sehua_topic_skip_reason("") == "页面为空"
    assert hd.sehua_topic_skip_reason('<div class="blockcode">magnet:?xt=urn:btih:abc</div>隐藏') is None
