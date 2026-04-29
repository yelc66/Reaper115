"""
测试各版块解析结果能否通过入库完整性校验。

运行方式：
    python tests/test_parse_completeness.py
"""

import sys
import os

# 不依赖 init / config，只测纯函数逻辑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.sehuatang_spider import get_av_number_from_title

# ──────────────────────────────────────────────────────────────
# 各版块的典型标题样本（来自真实爬取结果）
# ──────────────────────────────────────────────────────────────
SECTION_TITLE_SAMPLES = {
    "国产原创":      ["【国产】某某某合集 720P", "【麻豆】某某某 4K"],
    "亚洲无码原创":  ["FC2-PPV-1234567 某某某", "HEYZO-1234 某某某"],
    "亚洲有码原创":  ["SSIS-123 某某某", "MIDV-456 某某某", "ABC-789 某某某"],
    "高清中文字幕":  ["SSIS-123 无码字幕 某某某", "MIDV-456 无码破解 某某某"],
    "素人有码系列":  ["CAWD-123 某某某", "HND-456 某某某"],
    "4K原版":       ["IPVR-123 某某某 4K", "siro-5678"],  # siro 无空格
    "VR视频区":     ["IPVR-123 某某某 VR", "kavr-456 某某某", "vrkm-789"],  # vrkm 无空格
    "欧美无码":     [
        "officepov.26.04.20.amalia.davis.and.amber.slassh",   # 无空格
        "nurumassage.26.04.20.river.lynn.4k",                  # 无空格
        "brazzers.26.04.20.some.actress",                      # 无空格
        "Blacked 2026 Some Title",                             # 有空格
    ],
}

# 入库完整性校验所需字段（对应 save_sehua2db 里的判断）
REQUIRED_FIELDS = ["section_name", "title", "magnet", "size", "movie_type",
                   "post_url", "publish_date", "pub_url"]


def make_mock_result(section_name: str, title: str) -> dict:
    """构造一个字段尽量完整的 mock 解析结果，仅 av_number 来自真实提取逻辑。"""
    if section_name == "国产原创":
        av_number = "N/A"
    else:
        av_number = get_av_number_from_title(title)

    return {
        "section_name": section_name,
        "title": title,
        "av_number": av_number,
        "size": "1.00G",
        "movie_type": "无码",
        "post_url": "https://example.com/cover.jpg",
        "magnet": "magnet:?xt=urn:btih:AABBCCDD",
        "publish_date": "2026-04-28",
        "pub_url": "https://www.sehuatang.net/forum.php?mod=viewthread&tid=1",
        "save_path": f"/AV/涩花/{section_name}",
    }


def check_completeness(result: dict, specify_path: str = "/AV/涩花/test") -> list[str]:
    """返回未通过校验的字段名列表（空列表表示全部通过）。"""
    missing = []
    for field in REQUIRED_FIELDS:
        if not result.get(field):
            missing.append(field)
    if not specify_path:
        missing.append("specify_path")
    return missing


def run():
    print("=" * 60)
    print("各版块解析结果完整性检查")
    print("=" * 60)

    all_passed = True

    for section, titles in SECTION_TITLE_SAMPLES.items():
        print(f"\n【{section}】")
        for title in titles:
            result = make_mock_result(section, title)
            missing = check_completeness(result)
            av = result["av_number"]
            if missing:
                all_passed = False
                print(f"  ✗  {title!r}")
                print(f"       av_number={av!r}  缺失字段: {missing}")
            else:
                status = f"av_number={av!r}" if av else "av_number='' (空，已允许)"
                print(f"  ✓  {title!r}  →  {status}")

    print("\n" + "=" * 60)
    if all_passed:
        print("全部通过")
    else:
        print("存在问题，见上方 ✗ 标记")
    print("=" * 60)


if __name__ == "__main__":
    run()
