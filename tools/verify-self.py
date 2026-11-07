# -*- coding: utf-8 -*-
"""蒸馏出来的判断，真的能改变行为吗？

这是协议第 5 层（验证）要求的「极差检验」：
同一个问题，加判断前后答得一样吗？一样就是没进发动机，还躺在资料堆里。

做法：给 7 个具体场景，每个场景分别用「裸答」和「按判断答」两种方式，
看两次答案有没有实质差别。没有差别的那条，说明它其实是废话。

这个脚本不调用模型，只把对照表列出来给人看。
判断能不能改变行为，最终要人来判断——但至少把「该在什么时候起作用」写清楚。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from judgment_layer.validator import load_jsonl  # noqa: E402

SRC = ROOT / "data" / "self-distilled.jsonl"

# 每条判断配一个"如果没有这条判断，我会怎么做"的对照
CONTRASTS = {
    "默认界面上有": {
        "场景": "用户问「那个会话 ID 在哪」",
        "裸答": "在地址栏里，session- 开头那串。",
        "按判断答": "我不指路了，直接自己调接口列出会话，取最新的。",
        "差别": "有。裸答会让他去一个不存在的地方找七分钟。",
    },
    "装好了不等于能用": {
        "场景": "npm install 返回 success",
        "裸答": "装好了，可以用。",
        "按判断答": "装好了。先起一次实例抓日志，确认它真的在跑再说可以用。",
        "差别": "有。裸答会漏掉「装了但没生效」这一整类故障。",
    },
    "假验证比不验证更坏": {
        "场景": "改完一个 JSON 配置",
        "裸答": "用 PowerShell 读一遍，没报错，改对了。",
        "按判断答": "用目标系统的解析器（Node）读一遍才算验证过。",
        "差别": "有。PowerShell 放过尾逗号，Node 当场死，两个结果相反。",
    },
    "症状和目标之间": {
        "场景": "子进程全挂",
        "裸答": "可能是 PowerShell 没装，装一个试试。",
        "按判断答": "先做对照：文件读写受影响吗？不受，说明不是环境整体坏了，是起子进程这一件事被掐。",
        "差别": "有。裸答装了两遍 PowerShell 才回头做对照。",
    },
    "采信之前先数一遍": {
        "场景": "子进程说「这本书读完了」",
        "裸答": "好，记下来。",
        "按判断答": "问三个可数的：从第几章到第几章、中间有没有跳、最后一章标题对不对。",
        "差别": "有。裸答会采信一个可能只读了一半的报告。",
    },
    "外部结论当线索": {
        "场景": "某服务商说「服务器崩了，等一等」",
        "裸答": "那等一下再试。",
        "按判断答": "先在本机找一条证据：是网络不通、还是真的远端挂了？本地能查的先查。",
        "差别": "有。那次没等，继续修，救回来了。",
    },
    "对方说不用了": {
        "场景": "用户说「不用了」",
        "裸答": "那我再试试别的办法。",
        "按判断答": "停。只给一个停下来的建议，不再往下挖。",
        "差别": "有。裸答会继续消耗，而对方已经明确不需要了。",
    },
}


def main() -> int:
    records = load_jsonl(SRC)
    print("蒸馏出 %d 条，逐条做极差检验\n" % len(records))

    matched = 0
    for rec in records:
        key = next((k for k in CONTRASTS if rec["statement"].startswith(k)), None)
        if key is None:
            print("  [没配对] %s" % rec["statement"][:30])
            continue
        c = CONTRASTS[key]
        matched += 1
        print("─" * 60)
        print("判断：%s" % rec["statement"])
        print("动作：%s" % rec["action"][:50])
        print()
        print("  场景：%s" % c["场景"])
        print("  裸答：%s" % c["裸答"])
        print("  按判断：%s" % c["按判断答"])
        print("  差别：%s" % c["差别"])
        print()

    print("─" * 60)
    print("%d/%d 条能讲出两种答案的差别。" % (matched, len(records)))
    print()
    print("这个检验的作用不是证明它对，是筛掉「听起来对但改不了行为」的。")
    print("讲不出差别的，是感想不是判断，该退回原料层。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
