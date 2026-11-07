# -*- coding: utf-8 -*-
"""一条命令跑完全部自检。

任何改动之后都跑一遍。八项检查，任一失败返回非零。
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run(cmd: list[str]) -> tuple[int, str]:
    # 子进程的 stdout 编码跟着系统走（Windows 上常是 GBK，CI 上是 UTF-8）。
    # 这里强制子进程也用 UTF-8 输出，否则父进程按 utf-8 解码会炸在中文上。
    #
    # PYTHONPATH 也由这里统一给：本机装过 editable 包所以 `python -m judgment_layer`
    # 直接能跑，CI 里没装就报 No module named。自检不该依赖「本机装没装」这个变量。
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def check_protocol_examples() -> tuple[bool, str]:
    """协议里的完整判断记录，必须**真的能过校验**，不只是字段齐全。

    早期版本只查「能解析 + 七字段齐全」，于是文档里 5 个手编的 id
    和真实规则打架（哈希段对不上、action 缺条件词）都没被发现。
    文档示例必须自己先合规，否则就是教人写错。
    """
    sys.path.insert(0, str(ROOT / "src"))
    from judgment_layer.validator import validate  # noqa: E402

    md = (ROOT / "PROTOCOL.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)```", md, re.S)
    need = {"statement", "action", "scope", "counterexample", "evidence", "confidence", "status"}
    if not blocks:
        return False, "PROTOCOL.md 里没找到 JSON 示例"

    full = 0
    fragment = 0
    for i, block in enumerate(blocks, 1):
        try:
            obj = json.loads(block)
        except Exception as exc:
            return False, "示例 %d 解析失败：%s" % (i, exc)
        if "statement" in obj or "id" in obj:
            miss = need - set(obj)
            if miss:
                return False, "完整记录 %d 缺字段：%s" % (i, miss)
            # 关键：文档示例必须自己先过校验
            errs = validate(obj)
            if errs:
                detail = "；".join("%s: %s" % (e["rule"], e["message"][:44]) for e in errs)
                return False, "完整记录 %d 自己就不合规：%s" % (i, detail)
            full += 1
        else:
            fragment += 1
    return True, "%d 条完整记录（全部自合规）+ %d 个字段片段" % (full, fragment)


def check_examples_file() -> tuple[bool, str]:
    """examples/ 目录下的示例也得能过校验。"""
    sys.path.insert(0, str(ROOT / "src"))
    from judgment_layer.validator import validate  # noqa: E402

    target = ROOT / "examples" / "book-to-judgment.md"
    if not target.exists():
        return True, "（没有 examples 文件）"
    text = target.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)```", text, re.S)
    checked = 0
    for i, block in enumerate(blocks, 1):
        try:
            obj = json.loads(block)
        except Exception as exc:
            return False, "示例 %d 解析失败：%s" % (i, exc)
        if "statement" not in obj:
            continue
        errs = validate(obj)
        if errs:
            detail = "；".join("%s: %s" % (e["rule"], e["message"][:44]) for e in errs)
            return False, "示例 %d 不合规：%s" % (i, detail)
        checked += 1
    return True, "%d 条示例全部合规" % checked


def check_real_data() -> tuple[bool, str]:
    code, out = run([PY, "-m", "judgment_layer", "validate", "data/judgments.jsonl"])
    # 取「全部通过」或「N 条有问题」那一行，别抓到警告列表尾巴
    conclusion = ""
    for line in out.splitlines():
        if "全部通过" in line or "条有问题" in line:
            conclusion = line.strip()
    if not conclusion:
        conclusion = out.strip().splitlines()[-1] if out.strip() else "(无输出)"
    warn = ""
    for line in out.splitlines():
        if "条警告" in line:
            warn = "，" + line.strip().rstrip("：:")
    return code == 0, conclusion + warn


def check_rules_bite() -> tuple[bool, str]:
    code, out = run([PY, "tests/test_rules.py"])
    last = out.strip().splitlines()[-1] if out.strip() else ""
    return code == 0, last


def check_encoding_errors() -> tuple[bool, str]:
    """编码坑的报错必须是人话。样本是工部实测时撞出来的真文件。"""
    code, out = run([PY, "tests/test_encoding.py"])
    last = out.strip().splitlines()[-1] if out.strip() else ""
    return code == 0, last


def check_all_md_json() -> tuple[bool, str]:
    """所有 markdown 里的 json 代码块都必须能解析。

    这条是户部核查时加的：docs/第二本书实测.md 和 docs/自查记录.md 里
    各有片段不是合法 JSON（字段片段单独成块），但 selfcheck 只扫 PROTOCOL.md，没暴露。
    """
    files = (
        list(ROOT.glob("*.md"))
        + list((ROOT / "docs").glob("*.md"))
        + list((ROOT / "examples").glob("*.md"))
    )
    total = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        for i, m in enumerate(re.finditer(r"```json\n(.*?)```", text, re.S), 1):
            total += 1
            try:
                json.loads(m.group(1))
            except Exception as exc:
                return False, "%s 第 %d 个 json 块不合法：%s" % (f.name, i, str(exc)[:60])
    return True, "%d 个文件里 %d 个 json 块全部可解析" % (len(files), total)


def check_self_distilled() -> tuple[bool, str]:
    """自我蒸馏出来的那批，反例必须有真出处。

    这是整个项目最硬的一条对照：
      书里抄来的判断 —— 反例是推想的，全是 W12 警告
      自己撞出来的判断 —— 反例有真出处，零警告
    """
    sys.path.insert(0, str(ROOT / "src"))
    from judgment_layer.validator import load_jsonl, validate, warnings_of  # noqa: E402

    path = ROOT / "data" / "self-distilled.jsonl"
    if not path.exists():
        return True, "SKIP 没有自我蒸馏文件"
    records = load_jsonl(path)
    problems = []
    for rec in records:
        errs = validate(rec)
        if errs:
            problems.append("%s 不合规" % rec.get("statement", "")[:16])
        if not isinstance(rec.get("counterexample_ref"), dict):
            problems.append("%s 反例无出处" % rec.get("statement", "")[:16])
    if problems:
        return False, "；".join(problems[:3])
    return True, "%d 条全部合规，且反例都有真出处" % len(records)


def check_numbers_fresh() -> tuple[bool, str]:
    """如果本机有日志，核对图上的数字能不能现算出来。

    开源仓库里没有个人日志（那是隐私），所以这一项在没有日志时跳过，
    标成 SKIP 而不是 FAIL —— 跳过不等于通过，输出里会明说。
    """
    journal = os.environ.get("JOURNAL", "")
    if not journal:
        return True, "SKIP 没有设置 JOURNAL 环境变量（开源仓库不含个人日志，正常）"
    if not Path(journal).exists():
        return True, "SKIP JOURNAL 指向的文件不存在：%s" % journal

    code, out = run([PY, "tools/reproduce.py"])
    if code != 0:
        return False, out.strip().splitlines()[-1] if out.strip() else "重算失败"
    try:
        data = json.loads((ROOT / "docs/measurements/hits-distribution.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return False, "读不到 hits-distribution.json：%s" % exc
    return True, "总数 %d，零命中 %d（%.1f%%），最高 %d 次" % (
        data["total"], data["zero_hits"],
        data["zero_hits_ratio"] * 100, data["max_hits"],
    )


def main() -> int:
    checks = [
        ("协议示例自合规", check_protocol_examples),
        ("examples 自合规", check_examples_file),
        ("真实数据合规", check_real_data),
        ("规则真的会拦", check_rules_bite),
        ("编码报错是人话", check_encoding_errors),
        ("md 里 json 能解析", check_all_md_json),
        ("自我蒸馏反例有出处", check_self_distilled),
        ("数字能现算", check_numbers_fresh),
    ]
    results = []
    for name, fn in checks:
        try:
            ok, detail = fn()
        except Exception as exc:
            ok, detail = False, "异常：%s" % exc
        mark = "PASS" if ok else "FAIL"
        print("  [%s] %-14s %s" % (mark, name, detail))
        results.append(ok)

    passed, total = sum(results), len(results)
    print("\n%d/%d" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
