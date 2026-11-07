# -*- coding: utf-8 -*-
"""编码与格式坑的回归测试。

这三个样本是工部实测时撞出来的，不是编的：
  - gbk-encoded.jsonl  记事本默认 ANSI 另存的结果
  - with-bom.jsonl     存成了「UTF-8 with BOM」
  - bad-json.jsonl     少了个逗号

三种都会在读文件那一刻炸，但炸得不一样。测试的目标不是让它们能读，
是确保**报错信息说的是人话**——新手看得懂怎么改。

跑法：
    python tests/test_encoding.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from judgment_layer.validator import load_jsonl  # noqa: E402

FIXTURES = HERE / "fixtures"


def expect_fail(name: str, path: Path, must_contain: list[str]) -> bool:
    """这个文件必须读失败，且报错里要出现指定的提示词。"""
    if not path.exists():
        print("  SKIP  %s（样本不在）" % name)
        return True
    try:
        load_jsonl(path)
    except Exception as exc:
        msg = str(exc)
        missing = [w for w in must_contain if w.lower() not in msg.lower()]
        if missing:
            print("  FAIL  %s  报错里没提到 %s" % (name, missing))
            print("        实际报错：%s" % msg[:120])
            return False
        print("  PASS  %s  报错：%s" % (name, msg[:60]))
        return True
    print("  FAIL  %s  居然读成功了，应该报错" % name)
    return False


def main() -> int:
    results = []

    print("GBK 编码的文件")
    results.append(expect_fail(
        "gbk-encoded.jsonl",
        FIXTURES / "gbk-encoded.jsonl",
        ["utf-8"],  # 至少要说出是编码问题
    ))

    print("带 BOM 的文件")
    results.append(expect_fail(
        "with-bom.jsonl",
        FIXTURES / "with-bom.jsonl",
        ["bom"],
    ))

    print("JSON 语法错的文件")
    results.append(expect_fail(
        "bad-json.jsonl",
        FIXTURES / "bad-json.jsonl",
        ["第", "行"],  # 要说是第几行出的问题
    ))

    # 正常情况下必须能读
    print("正常的文件")
    good = ROOT / "data" / "judgments.jsonl"
    try:
        records = load_jsonl(good)
        ok = len(records) > 0
        print("  %s  正常文件读了 %d 条" % ("PASS " if ok else "FAIL ", len(records)))
        results.append(ok)
    except Exception as exc:
        print("  FAIL  正常文件读不了：%s" % exc)
        results.append(False)

    passed, total = sum(results), len(results)
    print("\n%d/%d 通过" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
