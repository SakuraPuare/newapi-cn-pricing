#!/usr/bin/env python3
"""
Expand dated snapshot model names into pricing.json.

厂商习惯给同一个模型发日期快照版(qwen3.7-plus-2026-04-20、qwen-max-0107),
价格与主版本一致。若不显式定价,new-api 查不到倍率会静默回落到内置兜底
37.5(≈ ¥75/1M),既贵得离谱又没人会发现 —— 这个脚本就是堵这个洞。

安全约束:**只有剥掉日期后缀得到的 base 名已经在 pricing.json 里有价时,
才生成映射**。误剥(如 `...-preview-12-2025` 被当成 MMDD)得到的 base 名不
存在于价格表,自然被丢弃,不会产出错价。

用法:
    python3 snapshot_aliases.py                    # 读本地 models_live.txt
    python3 snapshot_aliases.py --url <pricing_api_url>   # 从线上拉并缓存

依赖 pricing.json 已由 generate.py + expand_aliases.py 生成。
"""

import argparse
import json
import re
import sys
import urllib.request

MODELS_CACHE = "models_live.txt"

# 日期快照后缀。顺序敏感:先长后短,避免 YYYY-MM-DD 被 MMDD 规则切错。
SUFFIX_PATTERNS = [
    r"-\d{4}-\d{2}-\d{2}$",   # -2026-04-20
    r"-\d{8}$",               # -20250514
    r"-\d{2}-\d{4}$",         # -05-2026 (月-年)
    r"-\d{6}$",               # -202604
    r"-\d{4}$",               # -1106 (月日)
    r"-latest$",
]

# 已知与主版本**不同价**的快照,不做映射(留给 MODELS 显式定价)。
EXCLUDE = set()


def strip_snapshot_suffix(name: str) -> str | None:
    """返回剥掉日期后缀后的 base 名;不是快照名则返回 None。"""
    for pat in SUFFIX_PATTERNS:
        base = re.sub(pat, "", name)
        if base != name:
            return base
    return None


def load_live_models(url: str | None) -> list[str]:
    if url:
        with urllib.request.urlopen(url, timeout=30) as resp:
            payload = json.load(resp)
        names = sorted({m["model_name"] for m in payload["data"]})
        with open(MODELS_CACHE, "w") as f:
            f.write("\n".join(names) + "\n")
        print(f"Fetched {len(names)} live model names → {MODELS_CACHE}")
        return names
    try:
        with open(MODELS_CACHE) as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        sys.exit(f"{MODELS_CACHE} not found; run once with --url to populate it")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="new-api /api/pricing URL to refresh the model list from")
    args = ap.parse_args()

    live = load_live_models(args.url)

    with open("pricing.json") as f:
        data = json.load(f)
    mr = data["data"]["model_ratio"]
    cr = data["data"]["completion_ratio"]
    ca = data["data"]["cache_ratio"]
    bm = data["data"]["billing_mode"]
    be = data["data"]["billing_expr"]

    added, skipped = 0, []
    for name in live:
        if name in mr or name in EXCLUDE:
            continue
        base = strip_snapshot_suffix(name)
        if base is None:
            continue
        if base not in mr:
            skipped.append((name, base))
            continue
        mr[name] = mr[base]
        for section in (cr, ca, bm, be):
            if base in section:
                section[name] = section[base]
        added += 1

    with open("pricing.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Added {added} dated-snapshot aliases")
    print(f"Skipped {len(skipped)} snapshot-looking names whose base has no price:")
    for name, base in skipped[:15]:
        print(f"  {name}  (base {base!r} not priced)")
    if len(skipped) > 15:
        print(f"  ... and {len(skipped) - 15} more")


if __name__ == "__main__":
    main()
