# -*- coding: utf-8 -*-
"""新建一条判断的交互式助手。

协议要求七个字段齐全，手写 JSON 容易漏。这个命令一步步问，边问边校验，
问到全过了才写入。

    python -m judgment_layer new data/judgments.jsonl
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from .validator import (
    EVIDENCE_KINDS,
    RELATIONS,
    make_id,
    validate,
)

PROMPT_HINT = {
    "statement": "一句话，不超 60 字。超过说明塞了两个判断，拆开。",
    "action": "必须写成条件句式：碰到 ____ 时，做 ____。这一项决定它是不是判断。",
    "counterexample": "什么情况下它不成立。不许写「暂无」，必须具体。",
}


def ask(prompt: str, hint: str = "", default: str = "") -> str:
    if hint:
        print("  " + hint)
    suffix = " [%s]" % default if default else ""
    while True:
        raw = input("> %s%s: " % (prompt, suffix)).strip()
        if raw:
            return raw
        if default:
            return default
        print("  不能为空，再填一次。")


def ask_list(prompt: str, hint: str = "", default: list[str] | None = None) -> list[str]:
    if hint:
        print("  " + hint)
    default = default or []
    suffix = " [%s]" % "/".join(default) if default else ""
    while True:
        raw = input("> %s（空格分隔）%s: " % (prompt, suffix)).strip()
        if raw:
            return [x for x in raw.replace("，", " ").split() if x]
        if default:
            return list(default)
        print("  至少填一个。")


def ask_float(prompt: str, default: float) -> float:
    while True:
        raw = input("> %s [%.2f]: " % (prompt, default)).strip()
        if not raw:
            return default
        try:
            val = float(raw)
        except ValueError:
            print("  要填数字。")
            continue
        if not 0 <= val <= 1:
            print("  范围 0 到 1。")
            continue
        return val


def build() -> dict:
    print("\n新建一条判断。七个字段，一个个来。")
    print("=" * 56)

    statement = ask("statement", PROMPT_HINT["statement"])
    action = ask("action", PROMPT_HINT["action"])
    scope = ask_list("scope", "适用场景，至少一个。不许写「全部」。")
    counterexample = ask("counterexample", PROMPT_HINT["counterexample"])

    print("\n  证据至少一条。kind 可选：%s" % " / ".join(EVIDENCE_KINDS))
    evidence = []
    while True:
        kind = ask("  kind", default="book")
        if kind not in EVIDENCE_KINDS:
            print("  只能从 %s 里选。" % "/".join(EVIDENCE_KINDS))
            continue
        ref = ask("  ref", "能定位回原处：书名+章节 / 文件路径 / 会话号")
        quote = ask("  quote", default="（无原句）")
        read_at = ask("  read_at", default=datetime.now().date().isoformat())
        evidence.append({"kind": kind, "ref": ref, "quote": quote, "read_at": read_at})
        more = input("  还要再加一条证据吗？(y/N): ").strip().lower()
        if more != "y":
            break
        print()

    confidence = ask_float("\nconfidence", 0.7)

    now = datetime.now().astimezone()
    record = {
        "statement": statement,
        "action": action,
        "scope": scope,
        "counterexample": counterexample,
        "evidence": evidence,
        "confidence": confidence,
        "status": "candidate",
        "hits": 0,
        "created_at": now.isoformat(),
        "supersedes": None,
        "superseded_by": None,
        "source_protocol": "1.0.0",
    }
    record["id"] = make_id(statement, record["created_at"])
    return record


def show(record: dict) -> None:
    print("\n" + "=" * 56)
    print("即将写入：")
    print(json.dumps(record, ensure_ascii=False, indent=2))


def main(path: str) -> int:
    target = Path(path)
    try:
        record = build()
    except (KeyboardInterrupt, EOFError):
        print("\n取消了，什么都没写。")
        return 1

    errors = validate(record)
    if errors:
        show(record)
        print("\n校验没过，没写入：")
        for e in errors:
            print("  [%s] %s" % (e["rule"], e["message"]))
        return 1

    show(record)
    print("\n注意：状态是 candidate，不进检索。要生效得有人裁决一次（改成 accepted）。")
    confirm = input("\n写入 %s？(y/N): " % target).strip().lower()
    if confirm != "y":
        print("没写入。")
        return 1

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print("已写入 %s" % target)
    print("id: %s" % record["id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "data/judgments.jsonl"))
