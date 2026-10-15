import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("organize", pathlib.Path(__file__).parents[1] / "app/core/organize.py")
org = importlib.util.module_from_spec(spec); spec.loader.exec_module(org)
import pytest

@pytest.mark.parametrize("fn,num,ver,part,target", [
    ("MIDA-752-C.mp4", "MIDA-752", "C", None, "MIDA-752 - C.mp4"),
    ("MIDA-117-UC.mp4", "MIDA-117", "UC", None, "MIDA-117 - UC.mp4"),
    ("ATID-689-U.mkv", "ATID-689", "U", None, "ATID-689 - U.mkv"),
    ("489155.com@FWAY-104.mp4", "FWAY-104", None, None, "FWAY-104.mp4"),
    ("FC2-PPV-1234567.mp4", "FC2-PPV-1234567", None, None, "FC2-PPV-1234567.mp4"),
    ("fc2ppv_1234567-C.MP4", "FC2-PPV-1234567", "C", None, "FC2-PPV-1234567 - C.mp4"),
    ("mida-752-c.mp4", "MIDA-752", "C", None, "MIDA-752 - C.mp4"),
    ("HEYZO-1234.mp4", "HEYZO-1234", None, None, "HEYZO-1234.mp4"),
    ("010123-001.mkv", "010123-001", None, None, "010123-001.mkv"),
    ("ABP-123-CD1.mp4", "ABP-123", None, 1, "ABP-123 - cd1.mp4"),
    ("ABP-123-C-cd2.mp4", "ABP-123", "C", 2, "ABP-123 - C-cd2.mp4"),
])
def test_parse(fn, num, ver, part, target):
    p = org.parse_video_name(fn)
    assert (p.number, p.version, p.part, p.target_name()) == (num, ver, part, target)

def test_non_video():
    assert org.parse_video_name("MIDA-752.nfo") is None
    assert org.parse_video_name("readme.txt") is None

@pytest.mark.parametrize("fn,num,ver,cat", [
    ("FC2PPV- 4819241-C.mp4", "FC2-PPV-4819241", "C", "FC2"),
    ("[中文字幕]Blacked.26.08.16.Gypsy.Rose.And.Anna.Claire-C.mp4", "Blacked.26.08.16.Gypsy.Rose.And.Anna.Claire", "C", "欧美"),
    ("[中文字幕]Deeper.26.08.20.Kenna.James.4K-C.mp4", "Deeper.26.08.20.Kenna.James", "C", "欧美"),
    ("[中文字幕]Blacked.14.03.10.Jillian.Janson.mp4", "Blacked.14.03.10.Jillian.Janson", None, "欧美"),
    ("300MIUM-1405.mp4", "300MIUM-1405", None, "素人"),
    ("259LUXU-1800-C.mp4", "259LUXU-1800", "C", "素人"),
    ("200GANA-3000.mp4", "200GANA-3000", None, "素人"),
    ("SIRO-5000.mp4", "SIRO-5000", None, "素人"),
    ("Tokyo-hot n0800-C.mp4", "N0800", "C", "日本无码"),
    ("H0930-ki200618-C.mp4", "H0930-ki200618", "C", "日本无码"),
    ("HEYZO-3405-C.mp4", "HEYZO-3405", "C", "日本无码"),
    ("010123-001.mkv", "010123-001", None, "日本无码"),
    ("MIDA-117-UC.mp4", "MIDA-117", "UC", "日本有码"),
    ("[中文字幕]Blacked.17.01.30.Megan.Rain 4K-C.mp4", "Blacked.17.01.30.Megan.Rain", "C", "欧美"),
    ("Blacked.21.12.25.Liz.Jordan-4K.mp4", "Blacked.21.12.25.Liz.Jordan", None, "欧美"),
    ("[中文字幕]Blacked.14.03.24.Scarlet Red.mp4", "Blacked.14.03.24.Scarlet.Red", None, "欧美"),
    ("[中文字幕]Vixen.26.06.06.Vixi.Rafi.Pull.Chapter.4.Touch.Move-C.mp4", "Vixen.26.06.06.Vixi.Rafi.Pull.Chapter.4.Touch.Move", "C", "欧美"),
    ("C0930-hitozuma1492-C.mp4", "C0930-hitozuma1492", "C", "日本无码"),
])
def test_extended(fn, num, ver, cat):
    p = org.parse_video_name(fn)
    assert (p.number, p.version, org.categorize(p.number)) == (num, ver, cat)

@pytest.mark.parametrize("num,cat", [("MIDA-752","日本有码"),("FC2-PPV-1234567","FC2"),("HEYZO-1234","日本无码"),("010123-001","日本无码"),("XYZ123","未知")])
def test_category(num, cat):
    assert org.categorize(num) == cat

def test_plan():
    plan = org.plan_for_files("/in/x", ["MIDA-752-C.mp4", "ad.txt"], {"root": "/涩花/整理"})
    assert [x[:3] for x in plan] == [("/in/x/MIDA-752-C.mp4", "/涩花/整理/日本有码/MIDA-752", "MIDA-752 - C.mp4")]

class FakeApi:
    def __init__(s): s.calls=[]
    def get_file_info(s,p): return {"file_id":"1"} if p=="/in/x" else None
    def get_file_list(s,params): return [{"fn":"MIDA-752-C.mp4","fc":"1"}]
    def __getattr__(s,n): return lambda *a: s.calls.append((n,a)) or True

def test_dry_run_no_writes():
    import logging; api=FakeApi()
    lg=logging.getLogger("t"); lg.warn=lg.warning
    out = org.Organizer(api, {"dry_run": True, "api_interval_sec": 0}, lg).organize_dir("/in/x")
    assert out and api.calls == []


# ---- 移植自 media-pipeline 的解析规则 ----
P = org.parse_video_name

def _names(src, files):
    return [x[2] for x in org.plan_for_files(src, files, {"root": "/涩花/整理"})]

@pytest.mark.parametrize("fn,target", [
    ("FC2PPV-3123245-C1.mp4", "FC2-PPV-3123245 - C-cd1.mp4"),
    ("FC2PPV-3123245-C2.mp4", "FC2-PPV-3123245 - C-cd2.mp4"),
    ("MIDA-117-UC2.mp4", "MIDA-117 - UC-cd2.mp4"),
    ("NHDTC-224_3.mp4", "NHDTC-224 - cd3.mp4"),
    ("ABC-123-PT1.mp4", "ABC-123 - cd1.mp4"),
    ("070220_324-paco-C.mp4", "070220_324-PACO - C.mp4"),
    ("050723-001-carib-1080p-C.mp4", "050723-001-CARIB - C.mp4"),
    ("H4610-TK0058-FHD-C.mp4", "H4610-TK0058 - C.mp4"),
])
def test_ported_targets(fn, target):
    assert P(fn).target_name() == target

def test_studio_aliases_and_context():
    assert P("052425_01-10MUSU-C.mp4").number == "052425_01-10MU"
    assert P("053125_100-pacopacom.mp4").number == "053125_100-PACO"
    assert P("052425_001-1PON-C.mp4").number == "052425_001-1PON"
    assert P("063020-001-C.mp4", "063020-001 Carib  t").number == "063020-001-CARIB"
    assert P("080826-001-C.mp4").number == "080826-001"
    assert org.categorize("063020-001-CARIB") == "日本无码"

def test_categories():
    c = org.categorize
    assert (c("MIDA-752"), c("FC2-PPV-1234567"), c("300MIUM-123"), c("HEYZO-1234"), c("H4610-TK0058"), c("Blacked.26.08.16.X"), c("T38-067")) == \
        ("日本有码", "FC2", "素人", "日本无码", "日本无码", "欧美", "未知")

def test_plan_letter_parts_and_fc2_parts():
    assert _names("/in/MIRD-281 t", ["MIRD-281-A.mp4", "MIRD-281-B.mp4", "MIRD-281-D.mp4"]) == \
        ["MIRD-281 - cd1.mp4", "MIRD-281 - cd2.mp4", "MIRD-281 - cd4.mp4"]
    assert _names("/in/x", ["FC2PPV-3074549-1-C.mp4", "FC2PPV-3074549-2-C.mp4"]) == \
        ["FC2-PPV-3074549 - C-cd1.mp4", "FC2-PPV-3074549 - C-cd2.mp4"]
    # 单个字母后缀不当分段（-C 仍是中字）
    assert _names("/in/x", ["MIDA-752-C.mp4"]) == ["MIDA-752 - C.mp4"]

def test_plan_true_dups():
    assert _names("/in/x", ["SNOS-275-C.mp4", "snos-275-c.mkv".replace(".mkv", ".mp4"), "ATID-691.mp4", "atid691.mp4"]) == \
        ["SNOS-275 - C.mp4", "SNOS-275 - C2.mp4", "ATID-691.mp4", "ATID-691 - 2.mp4"]

class _Log:
    def __getattr__(self, n): return lambda *a, **k: None

class _FakeApi:
    def __init__(self, tree): self.tree, self.ops = tree, []
    def get_file_info(self, path): return {"file_id": path} if path in self.tree else None
    def get_file_list(self, q): return [{"fn": n, "fc": "1"} for n in self.tree[q["cid"]]]
    def create_dir_recursive(self, d): self.tree[d] = []; self.ops.append(("mkdir", d))
    def rename(self, src, name): self.ops.append(("rename", src, name)); return True
    def move_file(self, src, d): self.tree[d].append(src.rsplit("/", 1)[1]); self.ops.append(("move", src, d)); return True
    def delete_single_file(self, p): self.ops.append(("rm", p))

def test_organizer_existing_target_becomes_c2():
    api = _FakeApi({"/in/SNOS-275 y": ["SNOS-275-C.mp4"], "/涩花/整理/日本有码/SNOS-275": ["SNOS-275 - C.mp4"]})
    done = org.Organizer(api, {"dry_run": False, "api_interval_sec": 0}, _Log()).organize_dir("/in/SNOS-275 y")
    assert done[0][2] == "SNOS-275 - C2.mp4"
    assert ("rename", "/in/SNOS-275 y/SNOS-275-C.mp4", "SNOS-275 - C2.mp4") in api.ops
