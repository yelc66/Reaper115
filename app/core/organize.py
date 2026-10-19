"""按番号整理 115 离线下载结果（可选功能，默认关闭）。

目标结构: {root}/{category}/{number}/{number} - {version}.{ext}
无版本后缀时: {root}/{category}/{number}/{number}.{ext}

版本后缀约定:
  -C  -> C   中文字幕
  -UC -> UC  无码破解 + 中文字幕
  -U  -> U   无码破解
多分段 -CD1 / -cd2 / -pt1 会追加为 cd1/cd2 ... (例如 "MIDA-752 - C-cd1.mp4")
"""
import os
import re
import time
from dataclasses import dataclass
from typing import Optional

VIDEO_EXTS = {"mp4", "mkv", "avi", "wmv", "mov", "ts", "m2ts", "flv", "rmvb", "webm", "m4v", "iso", "mpg"}

AD_PREFIX_RE = re.compile(r'^(?:\d{6}\.com@|[a-z0-9.-]+\.(?:com|net|org|xyz|cc)@)', re.IGNORECASE)

# 素人系列品番（片商数字前缀如 300MIUM/259LUXU/200GANA 会被去掉，靠品番本身归入素人）
AMATEUR_LABELS = ["SIRO", "ARA", "KNB", "DCV", "MAAN", "SCUTE", "MIUM", "LUXU", "GANA", "NTK", "KIRAY",
                  "ORECO", "SIMM", "JAC", "ERK", "MFC", "OREC", "STCV", "HHL", "CUTE", "NAMA", "SWEET",
                  "MGMQ", "INSTV", "HMDNC", "EWDX", "PAK", "NAEN", "BSKC", "SGK", "MIUMN", "LUXUW"]

# 分类名与 MDC-NG naming.category_mapping 保持一致:
# jp_censored=日本有码 jp_uncensored=日本无码 jp_amateur=素人 jp_fc2=FC2 cn=国产 ea=欧美 unknown=未知
DEFAULT_CATEGORIES = [
    {"name": "FC2", "pattern": r"^FC2-PPV-"},
    {"name": "欧美", "pattern": r"^[A-Za-z][A-Za-z0-9]*\.\d{2}\.\d{2}\.\d{2}"},
    {"name": "日本无码", "pattern": r"^(?:HEYZO-|\d{6}[-_]\d{2,3}(?:-[A-Z0-9]+)?$|[NK]\d{4}$|[HC]\d{4}-|CARIB|1PON|10MU|PACOPACOMAMA)"},
    {"name": "素人", "pattern": r"^(?:\d{3,4}[A-Z]{2,6}-\d{3,5}$|(?:" + "|".join(AMATEUR_LABELS) + r")-\d{3,5}$)"},
    {"name": "日本有码", "pattern": r"^[A-Z]{2,6}-\d{2,5}$"},
]
DEFAULT_CATEGORY = "未知"

# 顺序重要：先匹配特殊格式，再匹配通用格式
_NUMBER_PATTERNS = [
    ("fc2", re.compile(r'FC2[-_ ]*(?:PPV[-_ ]*)?(\d{5,8})', re.I)),
    ("heyzo", re.compile(r'HEYZO[-_ ]?(\d{3,5})', re.I)),
    ("ea", re.compile(r"^(?:\[[^\]]*\])?([A-Za-z][A-Za-z0-9]*\.\d{2}\.\d{2}\.\d{2}(?:[. ][^\[\]]*?)?)(?=[ ._-](?:4K|2160p|1080p|720p)(?:-(?:UC|C|U))?$|-(?:UC|C|U)$|$)", re.I)),
    ("h4", re.compile(r'(?<![A-Za-z0-9])([HC]\d{4})[-_]([A-Za-z]{2,10}\d{3,6})', re.I)),
    ("tokyohot", re.compile(r'(?:tokyo[-_ ]?hot[-_ ]?)([nk]\d{4})(?!\d)', re.I)),
    ("date", re.compile(r'(?<![\d])(\d{6})[-_](\d{2,3})(?![\d])')),
    ("amateur", re.compile(r'(?<![A-Za-z0-9])(\d{3,4})([A-Za-z]{2,6})[-_ ]?(\d{3,5})(?![\d])')),
    ("std", re.compile(r'(?<![A-Za-z])([A-Za-z]{2,6})[-_ ]?(\d{2,5})(?![\d])')),
]
# 版本后可跟分段: -C1/-UC2 (版本+分段)、-CD1/-PT1/-PART1、纯数字 -1/_2
_SUFFIX_RE = re.compile(r'^(?:[-_ ]?(?P<ver>UC|C|U)(?![A-Za-z]))?(?:(?:[-_ ]?(?:CD|PT|PART)|(?<=[CU])|[-_])(?P<part>\d{1,2})(?!\d)(?:[-_ ]?(?P<ver2>UC|C|U)(?![A-Za-z]))?)?', re.I)

# 无码日期番号片商: 别名 -> (标准标签, 日期与编号的分隔符)
STUDIOS = [
    (re.compile(r'CARIB(?:BEAN)?(?:COM)?PR|CARIBPR', re.I), "CARIBPR", "_"),
    (re.compile(r'CARIB(?:BEAN)?(?:COM)?', re.I), "CARIB", "-"),
    (re.compile(r'1PON(?:DO)?', re.I), "1PON", "_"),
    (re.compile(r'10MU(?:SUME|SU)?', re.I), "10MU", "_"),
    (re.compile(r'PACO(?:PACOMAMA|PACOM)?', re.I), "PACO", "_"),
]
_STUDIO_TAIL_RE = re.compile(r'^[-_ ]*(?:CARIB\w*|1PON\w*|10MU\w*|PACO\w*)', re.I)
_QUALITY_RE = re.compile(r'^(?:[-_ .]?(?:FHD|HD|SD|UHD|4K(?:S|B|60)?|8K|2160p|1080p|720p|GIFT|V(?=[-_]))(?![A-Za-z0-9]))+', re.I)
_RES_RE = re.compile(r'^[-_ .]?(?:4K|2160p|1080p|720p)', re.I)


def detect_studio(*texts):
    for t in texts:
        if not t:
            continue
        for pat, tag, sep in STUDIOS:
            if re.search(r'(?<![A-Za-z])(?:' + pat.pattern + r')(?![A-Za-z])', t, re.I):
                return tag, sep
    return None


@dataclass
class ParsedName:
    number: str
    version: Optional[str]
    part: Optional[int]
    ext: str

    def target_name(self) -> str:
        base = self.number
        tail = []
        if self.version:
            tail.append(self.version)
        if self.part:
            tail.append(f"cd{self.part}")
        if tail:
            base += " - " + "-".join(tail)
        return f"{base}.{self.ext}"


def strip_ad_prefix(name: str) -> str:
    return AD_PREFIX_RE.sub('', name, count=1)


def parse_video_name(filename: str, context: str = "") -> Optional[ParsedName]:
    """从视频文件名解析番号/版本。context 为父目录名(用于识别片商)。非视频或无法识别返回 None。"""
    name = strip_ad_prefix(os.path.basename(filename))
    stem, dot, ext = name.rpartition('.')
    if not dot or ext.lower() not in VIDEO_EXTS:
        return None
    ext = ext.lower()
    for kind, pat in _NUMBER_PATTERNS:
        m = pat.search(stem)
        if not m:
            continue
        if kind == "fc2":
            number = f"FC2-PPV-{m.group(1)}"
        elif kind == "heyzo":
            number = f"HEYZO-{m.group(1)}"
        elif kind == "ea":
            number = m.group(1)
        elif kind == "h4":
            number = f"{m.group(1).upper()}-{m.group(2)}"
        elif kind == "tokyohot":
            number = m.group(1).upper()
        elif kind == "date":
            st = detect_studio(stem, context)
            number = f"{m.group(1)}{st[1]}{m.group(2)}-{st[0]}" if st else f"{m.group(1)}-{m.group(2)}"
        elif kind == "amateur":
            # 片商数字前缀（200GANA/324SRTD）去掉，只保留标准番号
            number = f"{m.group(2).upper()}-{m.group(3)}"
        else:
            number = f"{m.group(1).upper()}-{m.group(2)}"
        rest = stem[m.end():]
        rest = _QUALITY_RE.sub('', rest)
        if kind == "ea":
            number = re.sub(r'\s+', '.', number.strip())
            rest = re.sub(r'^[ ._-](?:4K|2160p|1080p|720p)', '', rest, flags=re.I)
        if kind == "date":
            rest = _STUDIO_TAIL_RE.sub('', rest)
            rest = _RES_RE.sub('', rest)
        s = _SUFFIX_RE.match(rest)
        ver = (s.group('ver') or s.group('ver2')).upper() if s and (s.group('ver') or s.group('ver2')) else None
        part = int(s.group('part')) if s and s.group('part') else None
        return ParsedName(number, ver, part, ext)
    return None


def categorize(number: str, rules=None, default: str = DEFAULT_CATEGORY) -> str:
    for r in (rules or DEFAULT_CATEGORIES):
        if re.search(r["pattern"], number, re.I):
            return r["name"]
    return default


LETTER_PART_RE = re.compile(r"[-_](?P<l>[A-Z])$")
FC2_PART_RE = re.compile(r"^(?P<a>.*FC2[-_ ]?PPV[-_ ]?\d{5,8})[-_](?P<n>[1-9])(?P<b>[-_][A-Za-z]{1,2})?(?P<ext>\.[A-Za-z0-9]+)$", re.I)


def dup_name(p: ParsedName, n: int) -> str:
    """真重复改名: {number} - {version}{n}[-cdK].ext，无版本时 {number} - {n}.ext"""
    tail = f"{p.version or ''}{n}" + (f"-cd{p.part}" if p.part else "")
    return f"{p.number} - {tail}.{p.ext}"


def parse_batch(filenames, context: str = ""):
    """解析同一目录下的一批文件，处理字母分段(>=2 个 A/B/C/D)与 FC2 数字分段。返回 [(fn, ParsedName|None)]。"""
    filenames = list(filenames)
    letters = {}
    for fn in filenames:
        stem = fn.rsplit('.', 1)[0]
        g = LETTER_PART_RE.search(stem)
        if g and g['l'] != 'U':
            letters.setdefault(stem[:g.start()], []).append(fn)
    letter_part = {}
    for base, vs in letters.items():
        if len(vs) >= 2:
            for v in vs:
                letter_part[v] = (base + '.' + v.rsplit('.', 1)[1], ord(LETTER_PART_RE.search(v.rsplit('.', 1)[0])['l']) - 64)
    out = []
    for fn in filenames:
        lp = letter_part.get(fn)
        p = parse_video_name(lp[0] if lp else fn, context)
        if p and lp:
            p.version, p.part = None, lp[1]
        g = FC2_PART_RE.match(fn)
        if p and g and not p.part:
            p2 = parse_video_name(g['a'] + (g['b'] or '') + g['ext'], context)
            if p2:
                p = p2
                p.part = int(g['n'])
        out.append((fn, p))
    return out


def plan_for_files(src_dir: str, filenames, cfg: dict):
    """纯函数：返回计划动作列表 [(src_path, target_dir, target_name, parsed)]，便于测试和 dry-run。
    同批次内目标重名(真重复)时第二份起改名为 ' - C2' / ' - 2'。"""
    root = cfg.get("root", "/涩花/整理").rstrip('/')
    rules = cfg.get("categories") or DEFAULT_CATEGORIES
    default = cfg.get("default_category", DEFAULT_CATEGORY)
    ctx = src_dir.rstrip('/').rsplit('/', 1)[-1]
    plan, seen = [], {}
    for fn, p in parse_batch(filenames, ctx):
        if not p:
            continue
        cat = categorize(p.number, rules, default)
        if cat == default and cfg.get("keep_unknown_in_place", True):
            continue
        tdir = f"{root}/{cat}/{p.number}"
        tname = p.target_name()
        key = (tdir, tname)
        if key in seen:
            seen[key] += 1
            tname = dup_name(p, seen[key])
        else:
            seen[key] = 1
        plan.append((f"{src_dir.rstrip('/')}/{fn}", tdir, tname, p))
    return plan


class Organizer:
    """执行整理。api 为 core.open_115 的实例；所有 115 调用串行并间隔 api_interval_sec。"""

    def __init__(self, api, cfg: dict, logger):
        self.api = api
        self.cfg = cfg or {}
        self.log = logger
        self.dry_run = bool(self.cfg.get("dry_run", True))
        self.interval = float(self.cfg.get("api_interval_sec", 1.0))

    def _sleep(self):
        if self.interval > 0:
            time.sleep(self.interval)

    def _list(self, path):
        info = self.api.get_file_info(path)
        self._sleep()
        if not info or 'file_id' not in info:
            return None
        files = self.api.get_file_list({"cid": info['file_id'], "limit": 1150, "show_dir": 1, "offset": 0}) or []
        self._sleep()
        return files

    def organize_dir(self, src_dir: str):
        files = self._list(src_dir)
        if files is None:
            self.log.warn(f"[整理] 源目录不存在: {src_dir}")
            return []
        names = [f.get('fn', '') for f in files if str(f.get('fc')) == '1']
        plan = plan_for_files(src_dir, names, self.cfg)
        if not plan:
            self.log.info(f"[整理] {src_dir} 未识别到番号视频，跳过")
            return []
        done = []
        for src, tdir, tname, parsed in plan:
            prefix = "[整理][DRY-RUN]" if self.dry_run else "[整理]"
            self.log.info(f"{prefix} {src} -> {tdir}/{tname}")
            if self.dry_run:
                done.append((src, tdir, tname))
                continue
            existing = self._list(tdir)
            if existing is None:
                self.api.create_dir_recursive(tdir)
                self._sleep()
            else:
                names_there = {f.get('fn') for f in existing}
                n = 1
                while tname in names_there:
                    n += 1
                    tname = dup_name(parsed, n)
                if n > 1:
                    self.log.info(f"[整理] 目标已存在同名文件，按重复保留: {tdir}/{tname}")
            cur = src
            if os.path.basename(src) != tname:
                ok = self.api.rename(src, tname)
                self._sleep()
                if ok is not True:
                    self.log.warn(f"[整理] 重命名失败，跳过: {src}")
                    continue
                cur = f"{os.path.dirname(src)}/{tname}"
            if self.api.move_file(cur, tdir) is True:
                done.append((src, tdir, tname))
            else:
                self.log.warn(f"[整理] 移动失败: {cur} -> {tdir}")
            self._sleep()
        if not self.dry_run and done:
            rest = self._list(src_dir) or []
            if not any(str(f.get('fc')) == '1' and parse_video_name(f.get('fn', '')) for f in rest):
                self.log.info(f"[整理] 源目录已无正片，删除: {src_dir}")
                self.api.delete_single_file(src_dir)
                self._sleep()
        return done
