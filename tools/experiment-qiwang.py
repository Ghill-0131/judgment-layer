# -*- coding: utf-8 -*-
"""第二本书验证：用《棋王》（阿城，小说）走一遍协议的四道闸。

目的不是扩库，是测协议在**非社科类书**上还成不成立。

《反脆弱》《穷查理宝典》那批是外国社科：作者在论述，笔记里全是可引用的论点。
《棋王》是中国当代小说：笔记里全是对话原句和读后感悟，没有现成论点。

换一个作者、换一种文体，协议还能不能长出判断——这是这个脚本要回答的。

产物不进 data/judgments.jsonl，单独输出到 data/experiment-qiwang.jsonl，
避免实验污染正式库。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from judgment_layer.validator import make_id, validate  # noqa: E402

OUT = ROOT / "data" / "experiment-qiwang.jsonl"
SRC = "棋王（阿城）读书笔记，books/notes/棋王.md"

# ── 第一轮：把笔记里所有候选都写出来，先不管能不能过 ──
CANDIDATES = [
    {
        "code": "C1",
        "statement": "不接对方的逻辑，就没人能把你拖进他的道理里。",
        "action": "碰到对方用一套自己的框架压过来时，不接他的词，只用自己那句具体的话回应。",
        "scope": ["争论", "被指责", "立场对抗"],
        "counterexample": "需要合作推进、双方必须共用同一套术语时不适用，此时不接话等于谈不下去。",
        "evidence": [{"kind": "book", "ref": SRC + " 感悟一", "quote": "李立讲革命，肖疙瘩只说「这里砍得」；不接逻辑，就没人能把你拖进他的道理里。", "read_at": "2026-11-05"}],
        "confidence": 0.8,
    },
    {
        "code": "C2",
        "statement": "被抬举的时候，最省力的回法是问一句对方做不到的事。",
        "action": "碰到被人抬举或捧高时，不推辞也不接受，反问一件对方自己没做到的事。",
        "scope": ["被捧场", "面对名望者"],
        "counterexample": "对方是真心请教、确实有本事时不适用，此时反问变成刁难。",
        "evidence": [{"kind": "book", "ref": SRC + " 对话采样 3", "quote": "这残局你可走通了？——还未通。——那我为什么要做你的徒弟？", "read_at": "2026-11-05"}],
        "confidence": 0.7,
    },
    {
        "code": "C3",
        "statement": "反对一件抽象的事，就指一个具体位置。",
        "action": "碰到要反对一件抽象的事时，不争论道理，只指一个具体的东西或位置。",
        "scope": ["反对意见", "劝阻"],
        "counterexample": "对方要求的是书面论证、需要留证据时不适用，此时具体指认不够用。",
        "evidence": [{"kind": "book", "ref": SRC + " 树王七", "quote": "肖疙瘩指着自己胸口说「学生，那里不是砍的地方」。", "read_at": "2026-11-05"}],
        "confidence": 0.8,
    },
    {
        "code": "C4",
        "statement": "被人当面顶撞，最狠的一招是请教他怎么做的。",
        "action": "碰到被人当面顶撞或否定时，不辩解，先问他是怎么做的、说说看。",
        "scope": ["被顶撞", "被质疑"],
        "counterexample": "对方明显在拖延或撒谎时不适用，此时请教等于给他台阶继续糊弄。",
        "evidence": [{"kind": "book", "ref": SRC + " 感悟六", "quote": "我被人当面骂混饭吃，回的是「你说说看，李老师是怎么教的」——把对手变成老师。", "read_at": "2026-11-05"}],
        "confidence": 0.75,
    },
    {
        "code": "C5",
        "statement": "想让人知道你在意，别声明，做一件事。",
        "action": "碰到想让对方明白你的态度时，不说出口，做一个具体的小动作。",
        "scope": ["表达态度", "关系维护"],
        "counterexample": "涉及承诺、合同、明确责任时不适用，此时必须写明白，动作顶不了条款。",
        "evidence": [{"kind": "book", "ref": SRC + " 感悟五", "quote": "肖疙瘩把菜叶拾进筐、六爪把糖推到桌子中央。阿城写尊重全靠动作不靠话。", "read_at": "2026-11-05"}],
        "confidence": 0.75,
    },
    {
        "code": "C6",
        "statement": "认输的时候带一句硬道理，输也输得有分量。",
        "action": "碰到要认输认错时，先把东西给出去，再说一句站得住的道理。",
        "scope": ["认错", "认输"],
        "counterexample": "认的是无争议的事实错误（数据算错）时不适用，此时多讲道理像狡辩。",
        "evidence": [{"kind": "book", "ref": SRC + " 孩子王四", "quote": "这字典是我送你的，不是你赢的……记录一件事，永远在事后，这个道理是扳不动的。", "read_at": "2026-11-05"}],
        "confidence": 0.7,
    },
    {
        "code": "C7",
        "statement": "话说得越少，落得越重。",
        "action": "碰到要表达一个重要态度时，只说一句，不加解释。",
        "scope": ["重要表达", "情绪场合"],
        "counterexample": "对方明确要求解释清楚时不适用，此时少说会被当成心虚。",
        "evidence": [{"kind": "book", "ref": SRC + " 感悟二", "quote": "王一生九局下完只说了两个字「和了吧」；肖疙瘩临终只托一封信。", "read_at": "2026-11-05"}],
        "confidence": 0.5,
    },
    # ── 下面两条是我故意放进来测边界的：它们是主题句/价值观，不是行动准则 ──
    {
        "code": "C8",
        "statement": "衣食是本，可囿在其中，终于还不太像人。",
        "action": "碰到只顾谋生的时候，想一想还剩下什么。",
        "scope": ["人生选择"],
        "counterexample": "暂无",
        "evidence": [{"kind": "book", "ref": SRC + " 棋王四", "quote": "衣食是本，自有人类，就是每日在忙这个。可囿在其中，终于还不太像人。", "read_at": "2026-11-05"}],
        "confidence": 0.9,
    },
    {
        "code": "C9",
        "statement": "何以解忧，唯有象棋。",
        "action": "难受的时候去下棋。",
        "scope": ["全部情况"],
        "counterexample": "无",
        "evidence": [{"kind": "book", "ref": SRC + " 棋王一", "quote": "忧这玩意儿，是他妈文人的佐料儿。我们这种人，没有什么忧，顶多有些不痛快。", "read_at": "2026-11-05"}],
        "confidence": 0.95,
    },
]


def main() -> int:
    results = []
    for cand in CANDIDATES:
        rec = {k: v for k, v in cand.items() if k != "code"}
        rec["created_at"] = "2026-11-05T20:00:00+08:00"
        rec["id"] = make_id(rec["statement"], rec["created_at"])
        rec["status"] = "candidate"
        rec["hits"] = 0
        rec["supersedes"] = None
        rec["superseded_by"] = None
        rec["source_protocol"] = "1.0.0"
        errors = validate(rec)
        results.append((cand["code"], rec, errors))

    passed = [r for r in results if not r[2]]
    failed = [r for r in results if r[2]]

    print("《棋王》实验：%d 条候选" % len(CANDIDATES))
    print("  过闸 %d 条 / 被拦 %d 条\n" % (len(passed), len(failed)))

    for code, rec, errors in results:
        if errors:
            print("  %s  [拦住] %s" % (code, rec["statement"]))
            for e in errors:
                print("        %s: %s" % (e["rule"], e["message"]))
        else:
            print("  %s  [通过] %s  (置信 %.2f)" % (code, rec["statement"], rec["confidence"]))
    print()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for code, rec, errors in results:
            if not errors:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("通过的 %d 条写入 %s" % (len(passed), OUT))
    print("被拦的 %d 条不写库 —— 它们留在报告里当证据" % len(failed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
