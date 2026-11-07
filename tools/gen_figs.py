# -*- coding: utf-8 -*-
"""立项书配图生成。

统计数字不写死——每次从 journal.jsonl 现算，避免过期。
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "img")
os.makedirs(OUT, exist_ok=True)
JOURNAL = os.environ.get("JOURNAL", r"journal.jsonl")


def load_stats():
    """从真实日志现算命中分布，不写死数字。"""
    rows = []
    with open(JOURNAL, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    active = [r for r in rows if r.get("status", "active") == "active"]
    hist = {}
    for r in active:
        h = r.get("hits") or 0
        hist[h] = hist.get(h, 0) + 1
    zero = hist.get(0, 0)
    total = len(active)
    return {
        "total": total,
        "zero": zero,
        "ratio": round(100 * zero / total, 1) if total else 0,
        "max": max(hist) if hist else 0,
        "hist": sorted(hist.items()),
    }


STATS = load_stats()

F = "C:/Windows/Fonts/msyh.ttc"
FB = "C:/Windows/Fonts/msyhbd.ttc"
INK, MUT, ACC, WARN, RED, GRN = "#111827", "#6b7280", "#2563eb", "#d97706", "#dc2626", "#059669"
BG, SOFT, BORD, ACCS = "#ffffff", "#f8fafc", "#e2e8f0", "#eff6ff"


def f(sz, bold=False):
    return ImageFont.truetype(FB if bold else F, sz)


def wrap(d, text, fnt, maxw):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        if d.textlength(cur + ch, font=fnt) <= maxw:
            cur += ch
        else:
            lines.append(cur); cur = ch
    if cur:
        lines.append(cur)
    return lines


def text_block(d, xy, text, fnt, fill=INK, maxw=None, lh=None):
    x, y = xy
    lh = lh or int(fnt.size * 1.55)
    lines = wrap(d, text, fnt, maxw) if maxw else text.split("\n")
    for ln in lines:
        d.text((x, y), ln, font=fnt, fill=fill)
        y += lh
    return y


def card(d, box, fill=BG, outline=BORD, r=14, w=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=w)


def down_arrow(d, cx, y1, y2, color=BORD, w=3):
    d.line([(cx, y1), (cx, y2 - 10)], fill=color, width=w)
    d.polygon([(cx - 8, y2 - 12), (cx + 8, y2 - 12), (cx, y2)], fill=color)


# ---------------- 图 1 ----------------
def fig1():
    W, H = 1600, 1260
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((80, 60), "判断层：五层流水线", font=f(46, True), fill=INK)
    d.text((80, 124), "左边是发动机，右边是数据库。同一个问题的两种解法。", font=f(22), fill=MUT)

    d.text((90, 196), "判 断 层", font=f(20, True), fill=ACC)
    d.text((1100, 196), "记 忆 库（现有方案）", font=f(20, True), fill=MUT)

    left = [
        ("单位", "存判断，不存事实", "事实只能被引用；判断能改我下一步怎么做"),
        ("入库", "写不成动作的，不许进", "命题 · 条件 · 反例 · 出处，缺反例会长成教条"),
        ("改写", "加强 / 限定 / 推翻", "旧条不删，降级挂靠，留痕比结论值钱"),
        ("生效", "改指令，不是塞参考", "塞进上下文我能不理会；改成指令我照做"),
        ("验证", "同问一句，答得不一样", "答得一样，说明它还躺在资料堆里当参考"),
    ]
    right = [
        ("存事实", "「用户喜欢蓝色」"),
        ("全量入库", "能记的都记，不做取舍"),
        ("无版本", "两条矛盾的数一起躺着"),
        ("塞进上下文", "检索出来当参考材料"),
        ("无从验证", "不知道有没有真的改变行为"),
    ]

    y = 236
    RH, GAP = 160, 22
    for i, (t, s, body) in enumerate(left):
        box = (90, y, 1060, y + RH)
        card(d, box, fill=ACCS, outline="#bfdbfe")
        cy = y + 40
        d.ellipse([110, cy - 20, 150, cy + 20], fill=ACC)
        n = str(i + 1)
        d.text((130 - d.textlength(n, font=f(21, True)) / 2, cy - 15), n, font=f(21, True), fill="#ffffff")
        d.text((172, cy - 18), t, font=f(27, True), fill=ACC)
        d.text((262, cy - 16), s, font=f(23, True), fill=INK)
        yy = y + 74
        text_block(d, (172, yy), body, f(20), MUT, maxw=850)
        if i < 4:
            down_arrow(d, 575, y + RH + 2, y + RH + GAP - 2, color="#93c5fd")
        y += RH + GAP

    y = 236
    for i, (t, s) in enumerate(right):
        box = (1100, y, 1510, y + RH)
        card(d, box, fill=SOFT, outline=BORD)
        d.text((1128, y + 34), t, font=f(25, True), fill="#374151")
        yy = y + 88
        text_block(d, (1128, yy), s, f(19), MUT, maxw=350)
        y += RH + GAP

    d.text((80, 1152), "数据：本机 %d 条日志，其中 %d 条（%s%%）从未被检索命中过。"
           % (STATS["total"], STATS["zero"], STATS["ratio"]),
           font=f(21), fill="#475569")

    im.save(os.path.join(OUT, "01-five-layers.png"))


# ---------------- 图 2 ----------------
def fig2():
    W, H = 1600, 880
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((80, 60), "一条判断必须带四样", font=f(46, True), fill=INK)
    d.text((80, 124), "实例句：贵在步数 × 上下文，不在缓存失效（2026-11-05）", font=f(22), fill=MUT)

    items = [
        ("命题", "它到底说什么", "贵在步数 × 上下文，不在缓存失效。", ACC, ACCS, "#bfdbfe"),
        ("成立条件", "什么时候这话算数", "长会话 / 大上下文 / 单步重读。脱离这三条它会反过来误导人。", WARN, "#fffbeb", "#fde68a"),
        ("反例", "什么情况下它会错", "缓存失效重计 0.8M，占当日 254M 的 0.3%，可以忽略。缺反例的判断会变教条。", RED, "#fef2f2", "#fecaca"),
        ("出处", "能查到它怎么来的", "usage.json 的 events 逐条计价 + 19 个 session 日志重算。", GRN, "#ecfdf5", "#a7f3d0"),
    ]
    CW, CH, GX, GY = 700, 176, 40, 44
    for i, (t, q, body, col, fill, outl) in enumerate(items):
        cx = 80 + (i % 2) * (CW + GX)
        cy = 220 + (i // 2) * (CH + GY)
        card(d, (cx, cy, cx + CW, cy + CH), fill=fill, outline=outl)
        d.text((cx + 32, cy + 26), t, font=f(28, True), fill=col)
        qx = cx + 32 + d.textlength(t, font=f(28, True)) + 18
        d.text((qx, cy + 33), q, font=f(19), fill=MUT)
        text_block(d, (cx + 32, cy + 88), body, f(20), "#374151", maxw=CW - 64)

    by = 220 + 2 * (CH + GY) + 6
    card(d, (80, by, 1560, by + 156), fill=INK, outline=INK)
    d.text((112, by + 24), "必须能落到动作", font=f(26, True), fill="#ffffff")
    d.text((112, by + 76), "长书合并读  ·  上下文到 20% 换会话  ·  能一条命令干完的别拆三条",
           font=f(23), fill="#cbd5e1")
    d.text((112, by + 118), "写不成动作的，只准进知识层，不准进判断层。", font=f(19), fill="#94a3b8")

    im.save(os.path.join(OUT, "02-judgment-anatomy.png"))


# ---------------- 图 2b：书到判断的链条 ----------------
def fig2b():
    W, H = 1600, 720
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((80, 58), "书怎么长成判断：原料 → 判断 → 行为", font=f(44, True), fill=INK)
    d.text((80, 120), ("16 本书、50 条知识条目、%d 条日志，同一条链上的三种形态。" % STATS["total"]), font=f(21), fill=MUT)

    stages = [
        ("原料", "16 本书", "读 25% 一段，每段落笔记\n先做目录索引", MUT, SOFT, BORD),
        ("提炼", "50 条知识", "每段只留方法论和价值观\n写不成动作的不进", WARN, "#fffbeb", "#fde68a"),
        ("判断", "落进指令", "改 AGENTS.md 和画像\n我照做，不照做要理由", ACC, ACCS, "#bfdbfe"),
        ("行为", ("%d 条日志" % STATS["total"]), "每次怎么答都留痕\n命中次数决定留不留", GRN, "#ecfdf5", "#a7f3d0"),
    ]
    CW, GAP = 330, 40
    x = 80
    for i, (t, big, body, col, fill, outl) in enumerate(stages):
        card(d, (x, 208, x + CW, 208 + 330), fill=fill, outline=outl)
        d.text((x + 28, 232), t, font=f(20, True), fill=col)
        d.text((x + 28, 272), big, font=f(34, True), fill=INK)
        text_block(d, (x + 28, 344), body, f(19), "#475569", maxw=CW - 56, lh=34)
        if i < 3:
            ax = x + CW + 8
            d.line([(ax, 373), (ax + GAP - 24, 373)], fill="#94a3b8", width=3)
            d.polygon([(ax + GAP - 26, 365), (ax + GAP - 26, 381), (ax + GAP - 8, 373)], fill="#94a3b8")
        x += CW + GAP

    card(d, (80, 580, 1520, 664), fill="#fffbeb", outline="#fde68a")
    d.text((112, 602), "闭环：行为产生日志 → 日志命中次数高的回流为判断 → 低的不删，软删到 archive。",
           font=f(21), fill="#92400e")

    im.save(os.path.join(OUT, "02b-book-to-judgment.png"))


# ---------------- 图 3 ----------------
def fig3():
    W, H = 1500, 880
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((90, 60), ("%d 条日志的检索命中分布" % STATS["total"]), font=f(44, True), fill=INK)
    d.text((90, 120), "本机真实数据 · 2026-11-07 · S/A/B/C/K/E 六层", font=f(21), fill=MUT)

    data = [(h, n) for h, n in STATS["hist"]]
    X0, X1, Y0, Y1 = 190, 1400, 210, 720
    mx = 160
    d.line([(X0, Y1), (X1, Y1)], fill=BORD, width=2)
    for gv in (0, 40, 80, 120, 160):
        yy = Y1 - (gv / mx) * (Y1 - Y0)
        d.line([(X0, yy), (X1, yy)], fill="#f1f5f9", width=1)
        d.text((X0 - 18 - d.textlength(str(gv), font=f(17)), yy - 11), str(gv), font=f(17), fill="#94a3b8")

    n = len(data)
    slot = (X1 - X0) / n
    bw = slot * 0.5
    for i, (h, v) in enumerate(data):
        cx = X0 + slot * (i + 0.5)
        bh = (v / mx) * (Y1 - Y0)
        col = "#94a3b8" if h == 0 else ACC
        d.rounded_rectangle([cx - bw / 2, Y1 - bh, cx + bw / 2, Y1 - 2], radius=6, fill=col)
        d.text((cx - d.textlength(str(v), font=f(22, True)) / 2, Y1 - bh - 34),
               str(v), font=f(22, True), fill=col)
        lab = f"{h} 次"
        d.text((cx - d.textlength(lab, font=f(19)) / 2, Y1 + 16), lab, font=f(19), fill="#475569")

    d.text((X0 - 60, Y1 + 56), "被 journal search 回头找到的次数", font=f(18), fill=MUT)

    card(d, (90, 780, 1410, 854), fill="#fffbeb", outline="#fde68a")
    d.text((118, 800), ("%d 条（%s%%）从未被回头找过  →  遗忘由「用不用」决定，不由「感觉重要」决定。" % (STATS["zero"], STATS["ratio"])),
           font=f(21), fill="#92400e")

    im.save(os.path.join(OUT, "03-hits-distribution.png"))


# ---------------- 图 4 ----------------
def fig4():
    W, H = 1600, 1110
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((80, 60), "一条判断怎么被推翻：全程有文件", font=f(44, True), fill=INK)
    d.text((80, 122), "token 那件事，我从 11-05 说错到 11-06 改口，旧条没删。", font=f(22), fill=MUT)

    rows = [
        ("V1", "2026-11-05", "贵在步数 × 上下文，不在缓存失效。", "置信 0.90", ACC, ACCS, "#bfdbfe"),
        ("V2", "2026-11-06", "相对结构用 session 日志；说钱用余额接口。\n12.57 元是 usage.json 的计价口径，不是真扣款。", "置信 0.75 · 限定", WARN, "#fffbeb", "#fde68a"),
        ("现状", "至今", "两条共存。V1 挂着「跟昨天的结论不一样，改口了」。", "并列 · 不删", GRN, "#ecfdf5", "#a7f3d0"),
    ]

    y = 200
    RH = 200
    for i, (tag, date, body, meta, col, fill, outl) in enumerate(rows):
        card(d, (80, y, 1520, y + RH), fill=fill, outline=outl)
        d.rounded_rectangle([110, y + 30, 210, y + 88], radius=10, fill=col)
        tw = d.textlength(tag, font=f(24, True))
        d.text((160 - tw / 2, y + 43), tag, font=f(24, True), fill="#ffffff")
        d.text((236, y + 36), date, font=f(20), fill=MUT)
        yy = text_block(d, (236, y + 74), body, f(23), INK, maxw=980)
        d.text((1250, y + 36), meta, font=f(19), fill=col)
        if i < 2:
            down_arrow(d, 800, y + RH + 4, y + RH + 44, color="#cbd5e1", w=3)
            label = "限定：不是推翻，是把适用范围收窄" if i == 0 else "留痕：下次掉同一个坑，能查到为什么"
            d.text((822, y + RH + 12), label, font=f(18), fill=MUT)
        y += RH + 56

    card(d, (80, y + 10, 1520, y + 96), fill=INK, outline=INK)
    d.text((112, y + 34), "换成存事实的记忆库：两个矛盾的数一起躺着，检索时随机捞出一个，人就分裂了。",
           font=f(22), fill="#ffffff")
    im.save(os.path.join(OUT, "04-version-chain.png"))


fig1(); fig2(); fig2b(); fig3(); fig4()
print("ok", os.listdir(OUT))
