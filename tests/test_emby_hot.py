import ast, pathlib, re, sys, types

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

# missav_spider 导入时依赖 init/bs4/telegram/selenium；测试只需要列表解析函数，按 AST 摘出来单独加载
_tree = ast.parse((ROOT / "app/core/missav_spider.py").read_text(encoding="utf-8"))
_keep = [n for n in _tree.body if (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_NAV_WORDS" for t in n.targets))
         or (isinstance(n, ast.FunctionDef) and n.name in ("_to_cn_url", "_extract_detail_links", "_av_number_from_url"))]
_fake = types.ModuleType("app.core.missav_spider")
_fake.re = re
exec(compile(ast.Module(body=_keep, type_ignores=[]), "missav_spider", "exec"), _fake.__dict__)
sys.modules["app.core.missav_spider"] = _fake

from app.core import emby_hot as eh  # noqa: E402


class Resp:
    def __init__(self, data):
        self.data = data
        self.content = b"x" if data is not None else b""
        self.headers = {"Content-Type": "application/json"}

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class FakeEmby:
    """极简 Emby: movies={id:(name,path)}, boxsets={id:(name,[ids])}"""

    def __init__(self, movies, boxsets=None):
        self.movies, self.boxsets, self.calls, self.headers = movies, boxsets or {}, [], {}

    def request(self, method, url, params=None, timeout=None):
        path = url.split("8096", 1)[1]
        p = dict(params or {})
        self.calls.append((method, path, p))
        if method == "GET":
            if "ParentId" in p:
                return Resp({"Items": [{"Id": i} for i in self.boxsets[p["ParentId"]][1]]})
            if p.get("IncludeItemTypes") == "BoxSet":
                return Resp({"Items": [{"Id": k, "Name": v[0]} for k, v in self.boxsets.items()]})
            term = p["SearchTerm"].lower().split("-")[0]
            return Resp({"Items": [{"Id": k, "Name": n, "Path": pa} for k, (n, pa) in self.movies.items()
                                   if term in (n + pa).lower()]})
        ids = p["Ids"].split(",")
        if method == "POST" and path == "/Collections":
            self.boxsets["bs1"] = (p["Name"], ids)
            return Resp({"Id": "bs1"})
        cid = path.split("/")[2]
        name, have = self.boxsets[cid]
        self.boxsets[cid] = (name, have + ids if method == "POST" else [i for i in have if i not in ids])
        return Resp(None)


MOVIES = {
    "m1": ("MIDA-117", "/strm/日本有码/MIDA-117/MIDA-117 - UC.strm"),
    "m2": ("MIDA-117", "/strm/日本有码/MIDA-117/MIDA-117 - C.strm"),
    "m3": ("MIDA-1170 other", "/strm/日本有码/MIDA-1170/MIDA-1170.strm"),
    "m4": ("FC2-PPV-1234567", "/strm/FC2/FC2-PPV-1234567/FC2-PPV-1234567 - C-cd1.strm"),
    "m5": ("old", "/strm/日本有码/SNOS-275/SNOS-275 - C.strm"),
}


def client(fake, uid=""):
    return eh.EmbyClient("http://emby:8096", "k", uid, session=fake)


def test_normalize():
    assert eh.normalize_number("mida-117-uncensored-leak") == "MIDA-117"
    assert eh.normalize_number("start-583-chinese-subtitle") == "START-583"
    assert eh.normalize_number("fc2-ppv-1234567") == "FC2-PPV-1234567"
    assert eh.normalize_number("/x/MIDA-117/MIDA-117 - UC.strm") == "MIDA-117"
    assert eh.normalize_number("063020-001.strm", "063020-001 Carib") == "063020-001-CARIB"
    assert eh.normalize_number("") is None


def test_list_html_ranked_unique():
    html = "".join(f'<a href="https://missav.ws/en/{t}">x</a>' for t in
                   ["today-hot", "mida-117", "mida-117-uncensored-leak", "fc2-ppv-1234567", "start-583", "genres"])
    assert eh.numbers_from_list_html(html, 12) == ["MIDA-117", "FC2-PPV-1234567", "START-583"]


def test_find_items_exact_number_and_versions():
    c = client(FakeEmby(MOVIES))
    assert c.find_items("MIDA-117") == ["m1", "m2"]
    assert c.find_items("ABC-001") == []
    assert c.s.headers["X-Emby-Token"] == "k"


def test_sync_creates_collection():
    fake = FakeEmby(MOVIES)
    r = eh.sync_collection(client(fake), "今日热门", ["MIDA-117", "XYZ-999", "FC2-PPV-1234567"])
    assert fake.boxsets["bs1"] == ("今日热门", ["m1", "m2", "m4"])
    assert (r["owned"], r["added"], r["removed"], r["missing"]) == (3, 3, 0, ["XYZ-999"])


def test_sync_updates_existing_mirrors_ranking():
    fake = FakeEmby(MOVIES, {"bsX": ("本周热门", ["m5", "m1"])})
    r = eh.sync_collection(client(fake), "本周热门", ["MIDA-117"])
    assert sorted(fake.boxsets["bsX"][1]) == ["m1", "m2"]
    assert (r["added"], r["removed"]) == (1, 1)
    assert ("DELETE", "/Collections/bsX/Items", {"Ids": "m5"}) in fake.calls


def test_sync_no_owned_no_create():
    fake = FakeEmby(MOVIES)
    r = eh.sync_collection(client(fake), "本月热门", ["XYZ-999"])
    assert r["id"] is None and not fake.boxsets


def test_user_id_path():
    fake = FakeEmby(MOVIES)
    client(fake, "u1").find_collection("x")
    assert fake.calls[0][1] == "/Users/u1/Items"
