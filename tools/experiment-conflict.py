# -*- coding: utf-8 -*-
"""第二本书验证的第二层：冲突检测。

上一轮证明了协议能在小说上长出判断，也拦得住主题句和诗句。

但有个更大的问题没测：**两条都合法的判断，在同一个场景里给出相反动作，怎么办？**

V10 只拦「同一句话两条 accepted」，拦不住这个。
如果这个漏洞补不上，判断层的可靠性就是空的——因为真实生活里冲突远比重复多。

这个脚本把《棋王》里长出来的 7 条，和第一批 15 条放一起，
按 scope 找重叠，把可能在同一个场景里打架的挑出来。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

BASE = ROOT / "data" / "judgments.jsonl"
QIWANG = ROOT / "data" / "experiment-qiwang.jsonl"


def load(path):
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def overlap(a: dict, b: dict) -> list[str]:
    """scope 字面重叠。粗糙，但先看有没有再谈准不准。"""
    sa, sb = set(a.get("scope") or []), set(b.get("scope") or [])
    return sorted(sa & sb)


def main() -> int:
    records = load(BASE) + load(QIWANG)
    print("合库 %d 条（正式库 %d + 棋王实验 %d）\n"
          % (len(records), len(load(BASE)), len(load(QIWANG))))

    pairs = []
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            hit = overlap(records[i], records[j])
            if hit:
                pairs.append((records[i], records[j], hit))

    if not pairs:
        print("scope 字面零重叠 —— 但这不代表没有冲突，只代表我写的 scope 颗粒度太粗。")
        return 0

    print("scope 重叠 %d 对：\n" % len(pairs))
    for a, b, hit in pairs:
        print("  共同场景: %s" % hit)
        print("    A: %s" % a["statement"])
        print("       → %s" % a["action"][:60])
        print("    B: %s" % b["statement"])
        print("       → %s" % b["action"][:60])
        print()

    # 按共同场景分组，看同一场景下有几条不同动作
    by_scene: dict[str, list[dict]] = {}
    for a, b, hit in pairs:
        for sc in hit:
            for rec in (a, b):
                lst = by_scene.setdefault(sc, [])
                if rec not in lst:
                    lst.append(rec)

    print("=" * 60)
    print("按场景聚类，看谁真的会打架：\n")
    risky = 0
    for scene, recs in sorted(by_scene.items(), key=lambda kv: -len(kv[1])):
        if len(recs) < 2:
            continue
        print("场景「%s」下有 %d 条判断同时生效：" % (scene, len(recs)))
        for rec in recs:
            print("  - %s" % rec["statement"])
            print("    动作: %s" % rec["action"])
        risky += 1
        print()

    print("=" * 60)
    print("%d 个场景里同时有多条判断在生效。" % risky)
    print("协议现在没有任何机制处理这个。这是真漏洞，不是理论问题。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
