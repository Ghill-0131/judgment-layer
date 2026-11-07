# -*- coding: utf-8 -*-
"""重算 240 条日志的命中分布，输出 hits-distribution.json

用法：python reproduce.py
输入：journal.jsonl（可用 JOURNAL 环境变量覆盖）
"""
import json
import os
import sys
from collections import Counter

JOURNAL = os.environ.get("JOURNAL", r"journal.jsonl")
OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "measurements",
    "hits-distribution.json",
)


def main():
    if not os.path.exists(JOURNAL):
        sys.exit(f"找不到日志文件：{JOURNAL}")

    rows = []
    with open(JOURNAL, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    active = [r for r in rows if r.get("status", "active") == "active"]
    hits = Counter(r.get("hits", 0) for r in active)
    zero = hits.get(0, 0)

    by_level = {}
    for r in active:
        lv = r.get("level", "?")
        by_level.setdefault(lv, {"total": 0, "zero_hits": 0, "max_hits": 0})
        b = by_level[lv]
        b["total"] += 1
        if not r.get("hits"):
            b["zero_hits"] += 1
        b["max_hits"] = max(b["max_hits"], r.get("hits", 0) or 0)

    result = {
        "generated_from": JOURNAL,
        "total": len(active),
        "zero_hits": zero,
        "zero_hits_ratio": round(zero / len(active), 4) if active else 0,
        "max_hits": max(hits) if hits else 0,
        "distribution": {str(k): v for k, v in sorted(hits.items())},
        "by_level": by_level,
        "note": "hits 由 journal search 命中时自增；null 视为 0。",
    }

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    print(f"总数 {result['total']}，零命中 {zero}（{result['zero_hits_ratio']:.1%}），最高 {result['max_hits']} 次")
    for lv, b in sorted(by_level.items()):
        print(f"  {lv}: {b['total']} 条，零命中 {b['zero_hits']}，最高 {b['max_hits']}")
    print(f"已写入 {OUT}")


if __name__ == "__main__":
    main()
