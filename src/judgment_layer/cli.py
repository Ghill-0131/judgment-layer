# -*- coding: utf-8 -*-
"""judgment-layer 命令行入口。

    python -m judgment_layer validate data/judgments.jsonl
    python -m judgment_layer stats    data/judgments.jsonl
    python -m judgment_layer export   data/judgments.jsonl --target imprint
    python -m judgment_layer archive  data/judgments.jsonl          # 只报告，不改文件
"""
from __future__ import annotations

import argparse
import json
import sys


from .validator import PROTOCOL_VERSION, load_jsonl, should_archive, stats, validate_all, warnings_of


def cmd_validate(args) -> int:
    try:
        records = load_jsonl(args.path)
    except FileNotFoundError as exc:
        print("找不到文件：%s" % exc)
        print("检查路径对不对。当前目录是：%s" % Path.cwd())
        return 1
    except ValueError as exc:
        print("读这个文件时卡住了：%s" % exc)
        print()
        print("三种最常见的原因：")
        print("  1. 某一行不是合法 JSON（少了逗号、多了逗号、引号不配对）")
        print("  2. 文件不是 UTF-8 编码 —— 用记事本另存过就是 ANSI，要改回 UTF-8")
        print("  3. 文件带 BOM —— 存成「UTF-8 with BOM」了，要选不带 BOM 的 UTF-8")
        return 1

    failures = validate_all(records)
    print("协议版本 %s · 共 %d 条" % (PROTOCOL_VERSION, len(records)))

    if not records:
        print("文件里一条都没有。0 条通过不算通过——先放点东西进去再跑。")
        return 1

    # 警告不拦，但要说。不说等于不存在。
    warn_count = 0
    warn_details: list[tuple[str, dict]] = []
    for rec in records:
        for w in warnings_of(rec):
            warn_count += 1
            warn_details.append((str(rec.get("id")), w))

    if not failures:
        print("全部通过 V1-V11")
    else:
        for rid, errs in failures:
            print("\n%s" % rid)
            for e in errs:
                print("  [%s] %s" % (e["rule"], e["message"]))
        print("\n%d 条有问题" % len({rid for rid, _ in failures}))

    if warn_count:
        print("\n%d 条警告（不阻塞，但该处理）：" % warn_count)
        by_rule: dict[str, list[tuple[str, str]]] = {}
        for rid, w in warn_details:
            by_rule.setdefault(w["rule"], []).append((rid, w["message"]))

        for rule, items in by_rule.items():
            print("\n  [%s] %d 条命中" % (rule, len(items)))
            print("       %s" % items[0][1])
            if len(items) <= 5:
                for rid, _ in items:
                    print("       - %s" % rid)
            else:
                for rid, _ in items[:3]:
                    print("       - %s" % rid)
                print("       - ……还有 %d 条" % (len(items) - 3))

    return 0 if not failures else 1


def cmd_stats(args) -> int:
    try:
        records = load_jsonl(args.path)
    except FileNotFoundError as exc:
        print("找不到文件：%s" % exc)
        return 1
    except ValueError as exc:
        print("读这个文件时卡住了：%s" % exc)
        return 1

    result = stats(records)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    total = result["total"]
    zero = result["zero_hits"]
    print()
    print("怎么读这几个数：")
    print("  total          一共几条判断")
    print("  by_status      accepted 在生效 / superseded 被取代 / candidate 待裁决 / archived 归档")
    print("  zero_hits      %d 条从没被用过（%.1f%%）" % (zero, result["zero_hits_ratio"] * 100))
    if total and zero / total > 0.8:
        print("                比例偏高。说明这个库刚建，或者大部分判断还没派上用场——")
        print("                两种都正常，别急着删。")
    print("  evidence_by_kind  证据从哪来：book 读书 / case 案例 / correction 纠错 / experiment 实验")
    return 0


def cmd_export(args) -> int:
    records = load_jsonl(args.path)
    accepted = [r for r in records if r.get("status") == "accepted"]

    if args.target == "native":
        for rec in accepted:
            print(json.dumps(rec, ensure_ascii=False))
        return 0

    if args.target == "imprint":
        # 有损映射，见 PROTOCOL.md 7.2
        out = []
        for rec in accepted:
            cases = [
                ev.get("ref", "")
                for ev in rec.get("evidence") or []
                if ev.get("kind") == "case"
            ]
            out.append({
                "statement": rec.get("statement", ""),
                "case_ids": cases,
                "reason": rec.get("counterexample", ""),
                "reason_status": "inferred",
            })
        print(json.dumps(out, ensure_ascii=False, indent=2))
        print(
            "\n注意：action / scope / confidence 在 imprint 本体里没有位置，已丢弃。"
            "这是单向下沉，不是对等互通。",
            file=sys.stderr,
        )
        return 0

    print("未知导出目标 %r，可选 native / imprint" % args.target, file=sys.stderr)
    return 1


def cmd_archive(args) -> int:
    records = load_jsonl(args.path)
    hit = []
    for rec in records:
        reason = should_archive(rec)
        if reason:
            hit.append((rec.get("id"), rec.get("statement", "")[:30], reason))
    if not hit:
        print("没有需要归档的")
        return 0
    for rid, stmt, reason in hit:
        print("%s  %s  —— %s" % (rid, stmt, reason))
    print("\n共 %d 条建议归档（本命令只报告，不改文件）" % len(hit))
    return 0


def cmd_new(args) -> int:
    from .newjudgment import main as new_main

    return new_main(args.path)


def cmd_hit(args) -> int:
    from .hit import main as hit_main

    return hit_main(args.args)


def main(argv=None) -> int:
    # Windows 控制台默认 GBK，中文输出到 UTF-8 终端会变乱码。
    # 这里把标准输出/错误都强制成 UTF-8，失败就静默跳过（有些环境不支持）。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(prog="judgment_layer", description="判断层协议参考实现")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate", help="校验 V1-V11")
    p.add_argument("path")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("stats", help="出账")
    p.add_argument("path")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("export", help="导出到别的系统")
    p.add_argument("path")
    p.add_argument("--target", default="native", choices=["native", "imprint"])
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("archive", help="报告该归档的条目")
    p.add_argument("path")
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser("new", help="交互式新建一条判断")
    p.add_argument("path")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("hit", help="记一次命中（或一次用错）")
    p.add_argument("args", nargs=argparse.REMAINDER)
    p.set_defaults(func=cmd_hit)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
