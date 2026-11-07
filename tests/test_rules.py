# -*- coding: utf-8 -*-
"""负向测试：每一条规则都必须能真的拦住东西。

校验器全部放行等于没有校验器。这个文件就是证明它没睡着。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from judgment_layer.validator import make_id, validate, validate_all  # noqa: E402


def base(**over) -> dict:
    rec = {
        "statement": "测试用的判断。",
        "action": "碰到测试时，做测试该做的事。",
        "scope": ["测试场景"],
        "counterexample": "这个判断在没有任何测试的情况下不成立。",
        "evidence": [{"kind": "book", "ref": "某本书 p.1", "quote": "原句"}],
        "confidence": 0.7,
        "status": "accepted",
    }
    rec.update(over)
    # id 必须是 statement 推出来的，否则 V13 会拦（这正是它该干的）。
    # 所以没显式给 id 的用例，这里自动补一个正确的。
    if "id" not in over:
        rec["id"] = make_id(str(rec["statement"]), "2026-11-08T00:00:00+08:00")
    return rec


def rules_of(errors) -> set[str]:
    return {e["rule"] for e in errors}


def check(name: str, rec: dict, expect_rule: str, should_pass: bool = False) -> bool:
    errors = validate(rec)
    got = rules_of(errors)
    if should_pass:
        ok = not errors
        print(("  PASS  " if ok else "  FAIL  ") + name + ("" if ok else "  实际报错: %s" % got))
        return ok
    ok = expect_rule in got
    print(("  PASS  " if ok else "  FAIL  ") + name + ("" if ok else "  期望 %s，实际 %s" % (expect_rule, got)))
    return ok


def main() -> int:
    results = []

    print("V1 · statement")
    results.append(check("空 statement 被拦", base(statement=""), "V1"))
    results.append(check("超 60 字被拦", base(statement="这是一句话" * 15), "V1"))

    print("V2 · action 必须条件句式")
    results.append(check("感想式 action 被拦", base(action="要认真做事。"), "V2"))
    results.append(check("条件式 action 放行", base(action="碰到要做事时，先想清楚再做。"), "", should_pass=True))

    print("V3 · scope")
    results.append(check("空 scope 被拦", base(scope=[]), "V3"))
    results.append(check("写「全部」被拦", base(scope=["全部情况"]), "V3"))
    results.append(check("写「任何情况」被拦", base(scope=["任何情况下"]), "V3"))

    print("V4 · counterexample 是硬门槛")
    results.append(check("空反例被拦", base(counterexample=""), "V4"))
    results.append(check("写「暂无」被拦", base(counterexample="暂无"), "V4"))
    results.append(check("写「无」被拦", base(counterexample="无"), "V4"))
    results.append(check("具体反例放行", base(counterexample="对方明确要求严谨论证时不成立。"), "", should_pass=True))

    print("V5 / V6 · evidence")
    results.append(check("空 evidence 被拦", base(evidence=[]), "V5"))
    results.append(check("conversation 被拒", base(evidence=[{"kind": "conversation", "ref": "某次聊天"}]), "V5"))
    results.append(check("ref 为空被拦", base(evidence=[{"kind": "book", "ref": ""}]), "V6"))
    results.append(check("experiment 放行", base(evidence=[{"kind": "experiment", "ref": "实测记录"}]), "", should_pass=True))

    print("V7 · confidence")
    results.append(check("超上限被拦", base(confidence=1.5), "V7"))
    results.append(check("负数被拦", base(confidence=-0.1), "V7"))
    results.append(check("字符串被拦", base(confidence="高"), "V7"))

    print("V8 · status")
    results.append(check("未知状态被拦", base(status="done"), "V8"))

    print("V9 · 关系必须显式")
    results.append(check("有取代无 relation 被拦",
                         base(supersedes="j-old"), "V9"))
    results.append(check("有取代无 relation_note 被拦",
                         base(supersedes="j-old", relation="限定"), "V9"))
    results.append(check("superseded 但没写被谁取代被拦",
                         base(status="superseded"), "V9"))
    results.append(check("关系齐全放行",
                         base(supersedes="j-old", relation="限定",
                              relation_note="范围收窄", status="candidate"), "", should_pass=True))

    print("V10 · 同一 statement 不得两条 accepted")
    a = base(id="j-a", statement="重复的判断。")
    b = base(id="j-b", statement="重复的判断。")
    fails = validate_all([a, b])
    got_ids = {rid for rid, errs in fails if "V10" in rules_of(errs)}
    ok = got_ids == {"j-a", "j-b"}
    print(("  PASS  " if ok else "  FAIL  ") + "两条重复 accepted 都被点名" + ("" if ok else "  实际: %s" % got_ids))
    results.append(ok)

    print("make_id · 同一句话撞同一个 id（天然去重）")
    ok = make_id("同样的话", "2026-11-07T10:00:00+08:00") == make_id("同样的话", "2026-11-07T10:00:00+08:00")
    print(("  PASS  " if ok else "  FAIL  ") + "同句同 id")
    results.append(ok)

    print("V11 · 同一 scope 下的未声明冲突")
    scene_a = base(id="j-s1", statement="重要的话只说一句。", scope=["重要表达"])
    scene_b = base(id="j-s2", statement="重要的话必须说透。", scope=["重要表达"])
    fails = validate_all([scene_a, scene_b])
    got_ids = {rid for rid, errs in fails if "V11" in rules_of(errs)}
    ok = got_ids == {"j-s1", "j-s2"}
    print(("  PASS  " if ok else "  FAIL  ") + "同场景两条无声明都被拦" + ("" if ok else "  实际: %s" % got_ids))
    results.append(ok)

    # 登记了 related_to 就放行
    scene_a2 = base(id="j-s3", statement="第一步。", scope=["重要表达"])
    scene_b2 = base(id="j-s4", statement="第二步。", scope=["重要表达"],
                    related_to=[{"id": "j-s3", "relation": "并立", "note": "流水线"}])
    scene_a2["related_to"] = [{"id": "j-s4", "relation": "并立", "note": "流水线"}]
    fails = validate_all([scene_a2, scene_b2])
    got_ids = {rid for rid, errs in fails if "V11" in rules_of(errs)}
    ok = not got_ids
    print(("  PASS  " if ok else "  FAIL  ") + "登记了 related_to 就放行" + ("" if ok else "  仍报: %s" % got_ids))
    results.append(ok)

    # 不同 scope 不该报
    scene_c = base(id="j-s5", statement="甲。", scope=["场景甲"])
    scene_d = base(id="j-s6", statement="乙。", scope=["场景乙"])
    fails = validate_all([scene_c, scene_d])
    got_ids = {rid for rid, errs in fails if "V11" in rules_of(errs)}
    ok = not got_ids
    print(("  PASS  " if ok else "  FAIL  ") + "scope 不重叠不误报" + ("" if ok else "  误报: %s" % got_ids))
    results.append(ok)

    print("V11 · 已知绕过路径必须被堵死")
    # 绕过 1：scope 尾随空格，让场景匹配静默失效
    a = base(id="j-sp1", statement="甲。", scope=["重要表达"])
    b = base(id="j-sp2", statement="乙。", scope=["重要表达 "])
    errs_b = validate(b)
    ok = "V3" in rules_of(errs_b)
    print(("  PASS  " if ok else "  FAIL  ") + "scope 尾随空格被 V3 拦" + ("" if ok else "  实际: %s" % rules_of(errs_b)))
    results.append(ok)

    fails = validate_all([a, b])
    hit = {rid for rid, errs in fails if "V11" in rules_of(errs)}
    ok = hit == {"j-sp1", "j-sp2"}
    print(("  PASS  " if ok else "  FAIL  ") + "带空格也照样报冲突" + ("" if ok else "  实际: %s" % hit))
    results.append(ok)

    # 绕过 2：related_to 只给 id，不给 relation
    rec = base(id="j-r1", statement="甲。", scope=["场景"])
    rec["related_to"] = [{"id": "j-r2"}]
    errs = validate(rec)
    ok = "V9" in rules_of(errs)
    print(("  PASS  " if ok else "  FAIL  ") + "related_to 缺 relation 被 V9 拦" + ("" if ok else "  实际: %s" % rules_of(errs)))
    results.append(ok)

    # 绕过 3：relation 乱填
    rec = base(id="j-r3", statement="甲。", scope=["场景"])
    rec["related_to"] = [{"id": "j-r4", "relation": "随便写写", "note": "x"}]
    errs = validate(rec)
    ok = "V9" in rules_of(errs)
    print(("  PASS  " if ok else "  FAIL  ") + "related_to 的 relation 乱填被 V9 拦" + ("" if ok else "  实际: %s" % rules_of(errs)))
    results.append(ok)

    # 绕过 4：related_to 是字符串数组
    rec = base(id="j-r5", statement="甲。", scope=["场景"])
    rec["related_to"] = ["j-r6"]
    errs = validate(rec)
    ok = "V9" in rules_of(errs)
    print(("  PASS  " if ok else "  FAIL  ") + "related_to 写成字符串数组被 V9 拦" + ("" if ok else "  实际: %s" % rules_of(errs)))
    results.append(ok)

    # 合规的 related_to 必须放行
    good_r7 = make_id("甲。", "2026-11-08T00:00:00+08:00")
    rec = base(id=good_r7, statement="甲。", scope=["场景"])
    rec["related_to"] = [{"id": good_r7, "relation": "并立", "note": "流水线第一步"}]
    errs = validate(rec)
    ok = not errs
    print(("  PASS  " if ok else "  FAIL  ") + "合规 related_to 放行" + ("" if ok else "  实际: %s" % rules_of(errs)))
    results.append(ok)

    print("V13 / V14 · id 必须存在、格式对、不重复")
    good_id = make_id("测试语句", "2026-11-08T00:00:00+08:00")
    rec = base(id=good_id, statement="测试语句")
    errs = validate(rec)
    ok = not errs
    print(("  PASS  " if ok else "  FAIL  ") + "正确 id 放行" + ("" if ok else "  实际: %s" % rules_of(errs)))
    results.append(ok)

    rec = base(id=good_id, statement="测试语句")
    rec.pop("id")
    errs = validate(rec)
    ok = "V13" in rules_of(errs)
    print(("  PASS  " if ok else "  FAIL  ") + "缺 id 被 V13 拦" + ("" if ok else "  实际: %s" % rules_of(errs)))
    results.append(ok)

    # 这是工部实测发现的：手编 id 完全没人管
    rec = base(id="whatever", statement="测试语句")
    errs = validate(rec)
    ok = "V13" in rules_of(errs)
    print(("  PASS  " if ok else "  FAIL  ") + "乱编 id 被 V13 拦" + ("" if ok else "  实际: %s" % rules_of(errs)))
    results.append(ok)

    # id 格式对但哈希段和 statement 对不上 —— 复制粘贴忘了改的典型
    rec = base(id="j-20260101-000000-zzzz", statement="测试语句")
    errs = validate(rec)
    ok = "V13" in rules_of(errs)
    print(("  PASS  " if ok else "  FAIL  ") + "哈希段对不上被 V13 拦" + ("" if ok else "  实际: %s" % rules_of(errs)))
    results.append(ok)

    # id 重复
    id_a = make_id("甲。", "2026-11-08T00:00:00+08:00")
    id_b = make_id("乙。", "2026-11-08T00:00:00+08:00")
    a = base(id=id_a, statement="甲。", scope=["场景甲"])
    b = base(id=id_a, statement="乙。", scope=["场景乙"])
    fails = validate_all([a, b])
    got = {r for r, errs in fails if "V14" in rules_of(errs)}
    ok = got == {id_a}
    print(("  PASS  " if ok else "  FAIL  ") + "id 重复被 V14 拦" + ("" if ok else "  实际: %s" % got))
    results.append(ok)

    # 不同 id 不该误报
    a = base(id=id_a, statement="甲。", scope=["场景甲"])
    b = base(id=id_b, statement="乙。", scope=["场景乙"])
    fails = validate_all([a, b])
    got = {r for r, errs in fails if "V14" in rules_of(errs)}
    ok = not got
    print(("  PASS  " if ok else "  FAIL  ") + "不同 id 不误报" + ("" if ok else "  误报: %s" % got))
    results.append(ok)

    print("V11 · 宽泛词与条数（刑部查出的断崖式失效）")
    # 4 条及以上同场景必须照样报。早期版本用「共用条数 > 3 就跳过」，导致 4 条真对立全放过。
    for n in (2, 3, 4, 5):
        recs = [
            base(id=make_id("判%d" % i, "2026-11-08T00:00:00+08:00"),
                 statement="判%d" % i, scope=["专属场景Q"], action="碰到时做第%d种" % i)
            for i in range(n)
        ]
        fails = validate_all(recs)
        got = {r for r, errs in fails if "V11" in rules_of(errs)}
        ok = len(got) == n
        print(("  PASS  " if ok else "  FAIL  ") + "%d 条同场景全报" % n + ("" if ok else "  实际: %d 条" % len(got)))
        results.append(ok)

    # 宽泛词不该报：谁都能往里塞的标签不是冲突键
    recs = [
        base(id=make_id("宽%d" % i, "2026-11-08T00:00:00+08:00"),
             statement="宽%d" % i, scope=["沟通"])
        for i in range(5)
    ]
    fails = validate_all(recs)
    got = {r for r, errs in fails if "V11" in rules_of(errs)}
    ok = not got
    print(("  PASS  " if ok else "  FAIL  ") + "宽泛词「沟通」不误报" + ("" if ok else "  误报: %s" % got))
    results.append(ok)

    # 「重要表达」是有具体处境的词，不能被当宽泛词豁免
    # （我一度把它列进黑名单，直接废掉了协议 8.1 自己的示例）
    a = base(id=make_id("重甲", "2026-11-08T00:00:00+08:00"), statement="重甲", scope=["重要表达"])
    b = base(id=make_id("重乙", "2026-11-08T00:00:00+08:00"), statement="重乙", scope=["重要表达"])
    fails = validate_all([a, b])
    got = {r for r, errs in fails if "V11" in rules_of(errs)}
    ok = len(got) == 2
    print(("  PASS  " if ok else "  FAIL  ") + "「重要表达」仍要报（不是宽泛词）" + ("" if ok else "  实际: %s" % got))
    results.append(ok)

    print("V2 · 条件词不能子串命中")
    for bad_action in ("应当认真做好每一件事。", "当然要认真做事。"):
        rec = base(action=bad_action)
        errs = validate(rec)
        ok = "V2" in rules_of(errs)
        print(("  PASS  " if ok else "  FAIL  ") + "「%s」被拦" % bad_action[:8] + ("" if ok else "  实际: %s" % rules_of(errs)))
        results.append(ok)
    for good_action in ("碰到测试时做测试。", "当X发生时做Y。", "每次遇到都停。"):
        rec = base(action=good_action)
        errs = validate(rec)
        ok = "V2" not in rules_of(errs)
        print(("  PASS  " if ok else "  FAIL  ") + "「%s」放行" % good_action[:8] + ("" if ok else "  实际: %s" % rules_of(errs)))
        results.append(ok)

    print("V4 · 敷衍反例加标点也绕过不了")
    for bad_counter in ("暂无", "暂无。", "无！", "同上...", "  暂无  "):
        rec = base(counterexample=bad_counter)
        errs = validate(rec)
        ok = "V4" in rules_of(errs)
        print(("  PASS  " if ok else "  FAIL  ") + "%r 被拦" % bad_counter + ("" if ok else "  实际: %s" % rules_of(errs)))
        results.append(ok)

    total = len(results)
    passed = sum(results)
    print("\n%d/%d 通过" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
