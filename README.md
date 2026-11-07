# 判断层 · Judgment Layer

> 记忆系统存**事实**（世界是什么）。这个协议存**判断**（碰到这种情况该怎么做）。
> 而判断可以被后来的证据推翻——全程留痕。

## 这东西解决什么问题

你要让一个 AI 长期跟着你。存事实那套（mem0、letta、cogito）能记住「用户喜欢蓝色」。

但它记不住「不理解约束条件，评价就是空的」——因为那不是一条事实，是一条**行动准则**。

而且当一条判断被推翻的时候，事实型记忆系统没有办法表达「我昨天说错了」。它只能让两个矛盾的版本一起躺着，检索时随机捞出一个，人就分裂了。

那 atlas 呢？

[atlas](https://github.com/RichSchefren/atlas) 已经做了很难的那部分：AGM 信念修正、Ripple 传播引擎（上游事实变了自动重算下游）、哈希链账本、adjudication 三档路由。它有 68 个测试文件，做得比我好。

**但它和这个协议的分歧在准入。**

atlas 用佐证制：至少两个独立来源互相印证，置信度过 0.80，才许提升。这适合存「世界是什么」——事实本来就能被多来源独立验证。

书只有一个来源。一本《反脆弱》，过不了那道闸。

而且它的主语类型只收人、程序、项目、决定、信念、承诺、市场主体、资产这八种。我那条「不理解的评价是空的」主语是什么？它没有主语。八个格子装不进去。

所以这不是「又造一遍轮子」，是**不是同一台机器**：

| | 事实型记忆 | 本协议 |
|---|---|---|
| 单位 | 事实 | 判断 |
| 起点 | 对话、笔记、录音 | 书、案例、纠错、实验 |
| 准入 | 多源佐证 | **反例制** |
| 冲突 | 检索时随机 | 加强 / 限定 / 推翻 / 并立，必须显式写 |
| 淘汰 | 重要性 × 新鲜度打分 | **命中数**（真的影响过一次行为） |

## 反例制：这是全部主张

判断是行动准则。多个来源都这么说，不构成正确，只构成流行。

判断的正确性来自**边界清不清楚**，而边界只能靠反例划出来。

所以本协议把 `counterexample` 设成硬门槛：不许空、不许写「暂无」、不许写「以上情况除外」。必须是一个具体的、可能真发生的情形。

这也意味着一件反直觉的事：**知道一条判断何时错，比知道它为何对更重要。**

## 一条判断长什么样

```json
{
  "id": "j-20261103-135806-da37",
  "statement": "不理解约束条件，评价就是空的。",
  "action": "碰到要评价一个自己看不惯的做法时，先把对方受的约束条件说清楚，说不出约束就不下评价。",
  "scope": ["评价他人决策", "跨行业判断", "政策与商业分析"],
  "counterexample": "纯道德层面、不涉及约束权衡的事不适用，此时可以直接给评价。",
  "evidence": [
    {
      "kind": "book",
      "ref": "置身事内（兰小欢）读书笔记 · 上篇",
      "quote": "作者全书不写「这样不好」，只写「为什么这样做」——先解释，再评判。",
      "read_at": "2026-11-03"
    }
  ],
  "confidence": 0.8,
  "source_protocol": "1.0.0",
  "status": "accepted",
  "hits": 0,
  "created_at": "2026-11-03T13:58:06+08:00",
  "supersedes": null,
  "superseded_by": null
}
```

七个必需字段：`statement`、`action`、`scope`、`counterexample`、`evidence`、`confidence`、`status`。

其中两个最有区分度：

- `action` 必须写成条件句式（碰到 X 时做 Y）。写不成条件句式的，是感想不是判断。
- `evidence.kind` 只允许 `book` / `case` / `correction` / `experiment`。**明确不接受 `conversation`。**

## 状态机

```
candidate ──人裁决──► accepted ──新证据──► superseded
                          │                    │
                          └──长期零命中────────┴──► archived
```

**没有「删除」这个动作。** 只能归档。

被推翻的判断降权保留，写清为什么变。留痕比结论值钱——三个月后你想知道自己为什么改口，只有这条链能回答。

## 快速开始

本项目零依赖，只用 Python 标准库。**三个命令都能跑，从最简单的开始。**

### 方式一：不安装，直接跑（推荐先试这个）

Windows PowerShell：

```powershell
$env:PYTHONPATH = "src"
python -m judgment_layer validate data/judgments.jsonl
```

macOS / Linux：

```bash
PYTHONPATH=src python -m judgment_layer validate data/judgments.jsonl
```

这样不用碰 PATH，也不会往系统里装东西。缺点是每次都要先设 `PYTHONPATH`。

### 方式二：装成本地包

```bash
python -m pip install -e .
```

注意两件事：

1. 用 `python -m pip` 而不是光敲 `pip`。如果你的机器上 `pip` 不在 PATH 里，前者照样能用。
2. 装完之后 `judgment-layer` 这个命令**可能在 PATH 之外**——pip 自己会警告一句 `is not on PATH`。遇到这种情况，直接用：

```bash
python -m judgment_layer validate data/judgments.jsonl
```

这个写法不依赖 PATH，永远能用。

### 常用命令

```bash
# 校验（错误拦写入，警告只提示）
python -m judgment_layer validate data/judgments.jsonl

# 新建一条判断，一步步问，边问边校验
python -m judgment_layer new data/judgments.jsonl

# 记一次命中（或一次用错）
python -m judgment_layer hit data/judgments.jsonl "报时间必须查表"
python -m judgment_layer hit data/judgments.jsonl "报时间必须查表" --wrong

# 出账
python -m judgment_layer stats data/judgments.jsonl

# 导出到 imprint（单向下沉，有损，见协议 7.2）
python -m judgment_layer export data/judgments.jsonl --target imprint

# 报告该归档的条目（只报告，不改文件）
python -m judgment_layer archive data/judgments.jsonl

# 一键自检：协议示例 / 数据合规 / 规则会不会拦 / 数字能不能现算
python tools/selfcheck.py
```

### 两个坑，提前说

**一、数据文件必须是 UTF-8，不能带 BOM。**

用记事本另存为时默认是 ANSI/GBK，存完再读会报 `UnicodeDecodeError`；带 BOM 则报 `Unexpected UTF-8 BOM`。两种都在读文件那一刻就炸，不给你任何其他提示。

用 VS Code / Notepad++ 打开，确认编码是 `UTF-8`（不是 `UTF-8 with BOM`）。

**二、`id` 不要手编。**

用 `judgment-layer new` 会自动生成。如果你想手写 JSON，`id` 的规则是 `j-YYYYMMDD-HHMMSS-四字节哈希`，最后四位必须是 `statement` 的 sha256 前四位。

V13 会检查这一点：id 缺失、格式不对、哈希段和语句对不上，都会拦。V14 拦 id 重复。

手工拼错 id 最坏的结果不是报错，是**取代链悄悄错乱**——所以 V13/V14 是硬拦，不给警告的余地。

## 仓库里有什么

```
PROTOCOL.md              协议正文（先读这个）
data/judgments.jsonl     15 条真实判断，全部来自书和真实纠错
src/judgment_layer/      参考实现：校验器 + CLI，不含存储引擎
tests/test_rules.py      40 项规则测试，含负向（必须被拦）和正向（不许误伤）
tools/selfcheck.py       一键四检
docs/                    提案、第二本书实测、吏部攻防、自查记录
examples/                从一本书走到一条判断的完整示例
```

**只有 15 条。** 这是一个从零开始的库，不是一个填满的库。要证明协议能用，15 条够看出形状，不够证明它普适。

## 用第二本书实测过，并因此改了协议

拿《棋王》（阿城，小说）验证「换作者换文体还成不成立」，结果写在 [docs/第二本书实测.md](docs/第二本书实测.md)。

摘要：

- 9 条候选，**7 条过闸、2 条被拦**。拦下的是全书题眼「衣食是本，可囿在其中，终于还不太像人」和诗句「何以解忧，唯有象棋」——它们是主题句和诗，不是行动准则。**拦得对。**
- 小说里照样能长出判断。分界线不是文体，是「能不能落到动作」。
- **测出一个致命漏洞**：两条动作完全相反的判断，各自都写得合规，都过 V1-V10，都进 accepted。判断层在同一个场景里同时持有两个相反指令——这比没有判断层更糟。

于是补了 **V11**：同一 scope 下不得有两条 accepted 而谁都没声明彼此关系。

加上之后，正式库立刻报出「说服」场景那对。它们其实是互补流水线，但没写清，补 `related_to` 才放行。

**这是被自己的规则打败之后补的，不是拍脑袋加的。**

## 这 15 条是真的

全部来自本机长期日志和读书笔记，每条 `ref` 都能顺着查回原文件：

- 《反脆弱》→ 「先问错了亏多少，再问对不对」
- 《穷查理宝典》→ 「遇事先问这事通常是怎么搞砸的」
- 《思考快与慢》→ 「判断之前先把被换掉的那道题换回来」
- 《沉默的大多数》→ 「要人改变，给一个具体的人和场景，比十条数据管用」
- 《人生》（路遥）→ 「判断一个人能不能成事，要问他离开了什么、还剩下什么」
- 《置身事内》→ 「不理解约束条件，评价就是空的」
- 《影响力》→ 「别讲道理，先找那个按下去就响的开关」

还有三条是从真实踩坑里来的（`kind: correction`），其中包括一条被**限定**过的：

`token 消耗贵在步数乘上下文` → 后来发现面板数字不是真扣款 → 被 `比相对结构用 session 日志，说钱用余额接口` 收窄取代。旧条没删，挂着「跟昨天的结论不一样，改口了」。

这条链就是这个协议想证明的全部：**改口不可耻，改口不留痕才可耻。**

## 已知的坑

写在 README 里，不藏。

**一、`hits` 很难准确计数。** 什么算「真正影响了一次行为」靠人判断，人懒得记，计数就虚。这层可能最后退化成手动标记。承认。

**一补、`hits` 还分不出对错。** 一条判断被用错了也算 hit。协议 6.1 节补了 `wrong` 字段的**设计**，但没实现。最危险的是 hits 高且 wrong 高的组合——它在持续产生错误决策，却因为用得多而显得重要。

**二、`action` 的条件词校验能被糊弄。** 加一个「碰到」就过。防君子不防小人。

**三、单来源。** 一条判断只有一本书撑腰，可能那本书本身就错。本协议故意不做多源要求，代价是把某本书的偏见固化成行动准则的风险。

**四、样本只有一个。** 这套规则是从一个人、三个月的真实记录里长出来的（日志条数一直在涨，具体总数见 docs/measurements/hits-distribution.json）。别人用它可能完全不适用。这是最大的漏洞。

**五、映射到 imprint 是有损的。** 它的 Principle 只有 statement / case_ids / reason / reason_status，`action`、`scope`、`counterexample` 在那边没有位置。别当对等互通用。

**六、`可证伪` 在数据模型里没有位置。** 协议第一节说判断要过三个检验，第三个是可证伪。但七个必需字段里没有对应项，V1-V11 里也只有 `counterexample` 沾边——可反例是边界声明，不等于「看到什么就放弃」的观察结果。所以三条检验里实际只有两条能被机器检查。**未修。**

**七、`counterexample` 可以凭空编。** 只有三个黑名单词拦着，写「如果我变成一只鸟就不适用」就能过。协议加了 `counterexample_ref` 要求反例有出处，但**降级成了警告**——因为设成硬拦之后，本库 15 条全挂，那些反例都是读书推想的，不是真撞上过的事。硬上等于宣布纯读书的判断不合法。

## 和哪些项目不一样

认真查过，不是拍脑袋说不像：

- [atlas](https://github.com/RichSchefren/atlas)（86★）：AGM 信念修正 + 传播引擎。**做得比我好**，但进料口只有对话，准入是佐证制，装不下无主语的行动准则。
- [imprint](https://github.com/RichSchefren/imprint)（15★）：对象是 judgment，v3.1.2 已发布，有隔离区和人裁决。**方向最接近**，但同样没有从书出发的路径。本协议可以向它导出。
- [mnemebrain-lite](https://github.com/mnemebrain/mnemebrain-lite)（4★）：Belnap 四值逻辑，矛盾是合法状态。学术上比我干净，但对象仍是 belief 不是 judgment。
- [Midas](https://github.com/vornicx/Midas)（14★）：遗忘按重要性 × 新鲜度打分。我按命中数。
- mem0（68k★）/ cognee（33k★）/ graphiti（32k★）/ letta（25k★）：全是检索型，无判断层。

一句话：判断层的机械结构已经有人造得比我好，我不重造。我做的是**进料口**——从书到判断那一段。

## 协议版本

`1.0.0` · 2026-11-07

协议本身是 v0.1 草案阶段，别急着生产用。看清想法就行。

## License

MIT

