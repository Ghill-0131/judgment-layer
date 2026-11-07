# -*- coding: utf-8 -*-
"""第三层实验：故意造一对对立的判断，看协议拦不拦得住。

前两层证明了：
  一、小说上也能长出判断（7/9 过闸）
  二、字面 scope 重叠只找到 1 对，且是互补不是矛盾

但真正的考验是：**两条动作相反的判断，能同时过闸吗？**

如果能，说明协议有一个致命漏洞——它管得住单条判断的质量，
管不住一个库里判断之间的关系。

这个测试就是拿自己写的规则去打自己。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from judgment_layer.validator import make_id, validate, validate_all  # noqa: E402

# 一对真正对立的判断。两条都写得完全合规。
PAIR = [
    {
        "tag": "A",
        "statement": "重要的话只说一句，不加解释。",
        "action": "碰到要表达一个重要的态度时，只说最关键的那一句，不补充来龙去脉。",
        "scope": ["重要表达"],
        "counterexample": "对方明确要求把前因后果讲清楚时不适用，此时少说会被当成心虚。",
        "evidence": [{"kind": "book", "ref": "棋王 · 感悟二", "quote": "话说得越少，落得越重。", "read_at": "2026-11-05"}],
        "confidence": 0.7,
    },
    {
        "tag": "B",
        "statement": "重要的话必须说透，否则一定被误解。",
        "action": "碰到要表达一个重要的态度时，把来龙去脉、边界条件一次讲清楚，不留空白。",
        "scope": ["重要表达"],
        "counterexample": "对方已经烦了、再讲只会起反效果时不适用，此时该停。",
        "evidence": [{"kind": "experiment", "ref": "多次沟通失败复盘", "quote": "话只说半句，对方按自己的理解补了另一半。", "read_at": "2026-11-06"}],
        "confidence": 0.7,
    },
]

for item in PAIR:
    rec = {k: v for k, v in item.items() if k != "tag"}
    rec["created_at"] = "2026-11-07T20:00:00+08:00"
    rec["id"] = make_id(rec["statement"], rec["created_at"])
    rec["status"] = "accepted"
    rec["hits"] = 0
    rec["supersedes"] = None
    rec["superseded_by"] = None
    rec["source_protocol"] = "1.0.0"
    item["record"] = rec

records = [item["record"] for item in PAIR]

print("对立判断测试\n")
for item in PAIR:
    errs = validate(item["record"])
    print("  %s: %s" % (item["tag"], item["record"]["statement"]))
    print("     动作: %s" % item["record"]["action"])
    print("     scope: %s" % item["record"]["scope"])
    print("     校验: %s" % ("全部通过" if not errs else errs))
    print()

failures = validate_all(records)
print("-" * 60)
if failures:
    print("协议拦住了：")
    for rid, errs in failures:
        for e in errs:
            print("  [%s] %s" % (e["rule"], e["message"]))
else:
    print("协议没拦住。")
    print()
    print("两条动作完全相反的判断，同时状态为 accepted，同时作用在「重要表达」这一个场景上。")
    print("V1-V10 全部通过，因为它们各自都写得合规。")
    print()
    print("这不是理论漏洞。真实使用中，两个人在两本书里会读到相反的答案，")
    print("两条都会过闸，然后判断层对同一个场景同时给出两个相反指令——")
    print("那就是它比没有判断层更糟的时刻。")
print()
print("-" * 60)
print("结论：协议缺一条 V11 —— 同一 scope 下不得有两条动作对立的 accepted。")
print("难点在于「动作对立」无法用字符串规则判断，只能用语义判断。")
print("这意味着 V11 不能靠校验器自动执行，必须靠人的裁决。")
