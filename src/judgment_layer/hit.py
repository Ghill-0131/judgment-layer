# -*- coding: utf-8 -*-
"""hits 计数：把一条判断标记为「用过一次」或「用错了」。

协议第 6 节说命中靠人判断。这个命令就是把那个人判断落盘的动作。
它不智能，也不假装智能——它只是让「用了一次」这件事有个地方可记。

    python -m judgment_layer hit data/judgments.jsonl j-20261103-135806-f795
    python -m judgment_layer hit data/judgments.jsonl <id> --wrong
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from typing import Any

from .validator import load_jsonl


def find(records: list[dict], key: str) -> dict | None:
    for rec in records:
        if rec.get("id") == key:
            return rec
        if str(rec.get("statement", "")).startswith(key):
            return rec
    return None


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("用法: judgment_layer hit <文件> <id 或语句前缀> [--wrong]")
        return 1

    path = Path(argv[0])
    key = argv[1]
    wrong = "--wrong" in argv[2:]

    try:
        records = load_jsonl(path)
    except (FileNotFoundError, ValueError) as exc:
        print("读取失败：%s" % exc)
        return 1

    rec = find(records, key)
    if rec is None:
        print("没找到匹配 %r 的判断。" % key)
        cands = [r for r in records if key in str(r.get("statement", ""))]
        if cands:
            print("相近的有：")
            for c in cands[:5]:
                print("  %s  %s" % (c.get("id"), c.get("statement", "")[:30]))
        return 1

    field = "wrong" if wrong else "hits"
    rec[field] = (rec.get(field) or 0) + 1
    rec["last_hit_at"] = datetime.now().astimezone().isoformat()

    # 只改目标那一行，其余字节原样保留。
    # 早期版本读全量再整文件覆写，会丢掉注释行和空行，中途出错还会把库写坏。
    target_id = rec.get("id")
    ok = _rewrite_one_line(path, target_id, rec)
    if not ok:
        return 1

    hits = rec.get("hits") or 0
    errs = rec.get("wrong") or 0
    print("%s  %s" % (rec.get("id"), str(rec.get("statement") or "(无语句)")[:40]))
    print("  hits=%d  wrong=%d" % (hits, errs))

    # 协议 6.1 的表：hits 高 wrong 高是最危险的组合
    if hits >= 5 and errs >= hits * 0.5:
        print("  ⚠ 用得多也错得多，这条该复审了。")
    elif wrong and errs >= 2:
        print("  ⚠ 已经错过 %d 次，检查一下边界是不是写窄了。" % errs)
    return 0


def _rewrite_one_line(path: Path, target_id: Any, new_obj: dict) -> bool:
    """定位并只替换目标 id 那一行，保留其余所有字节（含注释、空行）。"""
    if not target_id:
        print("这条记录没有 id，不知道要改哪一行。")
        return False

    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    hit_index = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("id") == target_id:
            hit_index = idx
            break

    if hit_index is None:
        print("在文件里没找到 id = %r 的那一行，没写入。" % target_id)
        return False

    trail = "\n" if lines[hit_index].endswith("\n") else ""
    lines[hit_index] = json.dumps(new_obj, ensure_ascii=False) + trail

    # 先写临时文件再替换。中途挂了也不会留下半个库。
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text("".join(lines), encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        print("写入失败：%s" % exc)
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
