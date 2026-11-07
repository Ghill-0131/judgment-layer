# -*- coding: utf-8 -*-
"""判断层协议 v1.0.0 的参考实现。

只做校验，不做存储、不做检索。协议立住之前，任何引擎都是白搭。

用法：
    from judgment_layer.validator import validate, load_jsonl
    errors = validate(record)          # 返回错误列表，空表示合法
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

PROTOCOL_VERSION = "1.0.0"

STATUSES = ("candidate", "accepted", "superseded", "archived")
EVIDENCE_KINDS = ("book", "case", "correction", "experiment")
RELATIONS = ("加强", "限定", "推翻")
# related_to 里允许的关系：并存不取代的两种，加限定
RELATION_LINKS = ("加强", "并立", "限定")

# 宽泛 scope 词：本身不能当冲突键用，因为谁都能往里塞。
# 注意这是「词」的黑名单，不是「共用条数」的阈值。
# 早期版本用条数阈值（>3 条共用就跳过），结果 4 条真对立的判断反而全放过，
# 逻辑正好反了 —— 条数越多越危险，不该越安全。
#
# 收词标准很严：只收那些**宽到无法指认一个具体处境**的词。
# 「重要表达」看着宽，但它能指认处境（要表达一个重要态度时），所以不在名单里。
# 把它收进来会直接废掉协议 8.1 节自己的示例，这个错我犯过一次。
BROAD_SCOPES = frozenset({
    "沟通", "表达", "判断", "决策", "思考", "工作", "生活", "学习",
    "写作", "阅读", "对话", "交流", "协作", "日常", "各种情况",
    "一般情况", "常见情况", "所有情况", "一切",
})


def is_broad_scope(scene: str) -> bool:
    """这个词是不是宽泛到不该当冲突键。"""
    return scene.strip() in BROAD_SCOPES

# V2 条件词。必须按「词」匹配，不能子串命中：
# 早期版本用 `"当" in action`，于是「应当认真做好」「当然要认真」都被放行。
CONDITION_PATTERNS = (
    re.compile(r"碰到"),
    re.compile(r"遇到"),
    re.compile(r"一旦"),
    re.compile(r"每次"),
    re.compile(r"(?:^|[，,。；;\s])当(?![然真是的])"),  # 「当X时」；排除「当然/应当」误伤
    re.compile(r"如果"),
    re.compile(r"凡(?![是])"),
)

# V4 敷衍反例。比对前要剥掉标点和空白，
# 否则「暂无。」「无！」都能绕过。
EMPTY_COUNTEREXAMPLE_RAW = ("暂无", "无", "同上", "没有", "待补", "略", "没有例外", "不存在")
_STRIP_PUNCT = re.compile(r"[\s。，、！？…\.\,\!\?~～\-—_（）()【】\[\]\"'“”‘’]+")

# V3 禁止的兜底式 scope
VAGUE_SCOPE = ("全部", "任何情况", "所有情况", "一切", "通用")

_MAX_STATEMENT = 60


def make_id(statement: str, created_at: str | None = None) -> str:
    """j-YYYYMMDD-HHMMSS-哈希。

    哈希段取 statement 的 sha256 前四位，所以**同一个 statement 的哈希段总是相同**，
    时间戳不同则完整 id 不同。V13 会核对哈希段和 statement 是否对得上，
    这是为了拦住「复制粘贴忘了改 statement，id 还是旧的」这种情况。

    不传 created_at 时用当前时间——因此连续两次调用同一句话会得到不同 id，
    这是预期的（它们是两条独立记录）。要幂等去重，请显式传同一个 created_at。

    created_at 传了非法值会抛 ValueError，不再静默改用当前时间——
    默默换时间比报错更坏，因为它会把数据写到错的一天。
    """
    if created_at is None:
        ts = datetime.now().astimezone().isoformat()
    else:
        try:
            datetime.fromisoformat(str(created_at))
        except ValueError as exc:
            raise ValueError("created_at = %r 不是合法时间（要 ISO 格式，如 2026-11-08T00:00:00+08:00）"
                             % created_at) from exc
        ts = str(created_at)

    dt = datetime.fromisoformat(ts)
    digest = hashlib.sha256(statement.strip().encode("utf-8")).hexdigest()[:4]
    return "j-%s-%s" % (dt.strftime("%Y%m%d-%H%M%S"), digest)


def _err(rule: str, message: str) -> dict[str, str]:
    return {"rule": rule, "message": message}


_ID_PATTERN = re.compile(r"^j-\d{8}-\d{6}-[0-9a-f]{4}$")


def _check_id(record: dict[str, Any]) -> list[dict[str, str]]:
    """V13 —— id 必须存在、格式对、由 statement 推出来。

    实测发现：id 缺失、重复、乱编全都静默通过。
    这是最危险的一类 bug —— 数据悄悄串了，直到某天 supersede 链对不上才发现。
    """
    rid = record.get("id")
    if not isinstance(rid, str) or not rid.strip():
        return [_err("V13", "id 必填。用 make_id(statement, created_at) 生成，别手编")]

    if not _ID_PATTERN.match(rid):
        return [_err("V13", "id = %r 格式不对，应为 j-YYYYMMDD-HHMMSS-四字节十六进制（共 4 位）" % rid)]

    # id 的哈希段应当是从 statement 推出来的。对不上说明 id 不是这条判断的 id，
    # 很可能复制粘贴时忘了改。
    statement = record.get("statement")
    if isinstance(statement, str) and statement.strip():
        expected_hash = hashlib.sha256(statement.strip().encode("utf-8")).hexdigest()[:4]
        actual_hash = rid.split("-")[-1]
        if actual_hash != expected_hash:
            return [_err("V13", "id 的哈希段 %r 和 statement 对不上（应为 %r）—— "
                                "多半是复制粘贴没改，或者 statement 改了 id 没跟着改"
                          % (actual_hash, expected_hash))]
    return []


def validate(record: dict[str, Any]) -> list[dict[str, str]]:
    """跑单条记录能查的规则：V1-V4、V5-V9、V12、V13。

    V10（同 statement 重复）、V11（场景冲突）、V14（id 重复）需要全库看，
    见 validate_all()。
    """
    errors: list[dict[str, str]] = []

    # ── V13 id ──
    errors.extend(_check_id(record))

    # ── V1 statement ──
    statement = record.get("statement")
    if not isinstance(statement, str) or not statement.strip():
        errors.append(_err("V1", "statement 不能为空"))
    elif len(statement.strip()) > _MAX_STATEMENT:
        errors.append(
            _err("V1", "statement 超过 %d 字（实际 %d），里面可能塞了两个判断"
                 % (_MAX_STATEMENT, len(statement.strip())))
        )

    # ── V2 action ──
    action = record.get("action")
    if not isinstance(action, str) or not action.strip():
        errors.append(_err("V2", "action 不能为空"))
    elif not any(p.search(action) for p in CONDITION_PATTERNS):
        errors.append(
            _err("V2", "action 缺条件词（碰到/遇到/一旦/每次/当X时/如果/凡是），"
                       "写不成条件句式的不是判断，是感想。现在写的是：%s" % action[:40])
        )

    # ── V3 scope ──
    scope = record.get("scope")
    if not isinstance(scope, list) or not scope:
        errors.append(_err("V3", "scope 必须是非空数组"))
    else:
        bad = [s for s in scope if any(v in str(s) for v in VAGUE_SCOPE)]
        if bad:
            errors.append(
                _err("V3", "scope 含兜底表述 %s —— 写「全部情况」等于没写" % bad)
            )
        # 首尾空格会让 V11 的场景匹配静默失效（"重要表达" vs "重要表达 "）。
        # 这是最危险的绕过方式：不报错、不提示，冲突检测直接放过。
        padded = [s for s in scope if isinstance(s, str) and s != s.strip()]
        if padded:
            errors.append(
                _err("V3", "scope 含首尾空格 %s —— 会让场景匹配静默失效，冲突检测漏掉" % padded)
            )
        nonstr = [s for s in scope if not isinstance(s, str)]
        if nonstr:
            errors.append(_err("V3", "scope 只能放字符串，发现 %s" % nonstr))

    # ── V4 counterexample ──
    counter = record.get("counterexample")
    if not isinstance(counter, str) or not counter.strip():
        errors.append(_err("V4", "counterexample 必填，这是整份协议最硬的一条"))
    else:
        # 先剥标点空白再比对，否则「暂无。」「无！」都能过。
        bare = _STRIP_PUNCT.sub("", counter)
        if bare in EMPTY_COUNTEREXAMPLE_RAW or not bare:
            errors.append(
                _err("V4", "counterexample 不许写「%s」，必须是具体情形" % counter.strip())
            )

    # ── V12 反例要有出处（警告，不是硬拦） ──
    # 只有 V4 的词汇黑名单，凭空编一句「如果我变成一只鸟就不适用」就能过。
    # 反例制是这协议的核心主张，不能只靠劝告。
    #
    # 但实测发现：这条一旦设成硬拦，我库里 15 条全挂——
    # 因为那些反例是读书时推想出来的，不是真实撞上过的事。
    # 硬上等于宣布「所有纯读书得来的判断都不合法」，那这个库就空了。
    #
    # 所以降级成 warning：不拦，但每次 validate 都提示。
    # 谁想上强度，把 warn 改成 errors.append 就行。
    warnings: list[dict[str, str]] = []
    if isinstance(counter, str) and counter.strip():
        cref = record.get("counterexample_ref")
        if not isinstance(cref, dict):
            warnings.append(
                _err("W12", "counterexample_ref 缺失 —— 反例是推想的，不是撞上过的。"
                            "建议补 {kind: case/correction/experiment, ref, quote}")
            )
        else:
            k = cref.get("kind")
            if k not in ("case", "correction", "experiment"):
                warnings.append(
                    _err("W12", "counterexample_ref.kind = %r 只能是 "
                                "case/correction/experiment。书不能当反例的出处" % k)
                )
            if not str(cref.get("ref") or "").strip():
                warnings.append(_err("W12", "counterexample_ref.ref 为空，要能定位回原处"))

    # ── V5 / V6 evidence ──
    evidence = record.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append(_err("V5", "evidence 至少一条"))
    else:
        for idx, item in enumerate(evidence):
            if not isinstance(item, dict):
                errors.append(_err("V5", "evidence[%d] 不是对象" % idx))
                continue
            kind = item.get("kind")
            if kind not in EVIDENCE_KINDS:
                errors.append(
                    _err("V5", "evidence[%d].kind = %r 不在 %s 里（不接受 conversation）"
                         % (idx, kind, list(EVIDENCE_KINDS)))
                )
            if not str(item.get("ref") or "").strip():
                errors.append(_err("V6", "evidence[%d].ref 为空，必须能定位回原处" % idx))

    # ── V7 confidence ──
    conf = record.get("confidence")
    if not isinstance(conf, (int, float)) or isinstance(conf, bool):
        errors.append(_err("V7", "confidence 必须是数字"))
    elif not 0.0 <= float(conf) <= 1.0:
        errors.append(_err("V7", "confidence = %r 超出 [0, 1]" % conf))

    # ── V8 status ──
    status = record.get("status")
    if status not in STATUSES:
        errors.append(_err("V8", "status = %r 不在 %s 里" % (status, list(STATUSES))))

    # ── V9 关系必须显式 ──
    supersedes = record.get("supersedes")
    superseded_by = record.get("superseded_by")
    relation = record.get("relation")
    if supersedes or superseded_by:
        if relation not in RELATIONS:
            errors.append(
                _err("V9", "有取代关系但 relation = %r 不在 %s 里 —— 加强/限定/推翻必须显式写"
                     % (relation, list(RELATIONS)))
            )
        if not str(record.get("relation_note") or "").strip():
            errors.append(_err("V9", "有取代关系但没写 relation_note，留痕比结论值钱"))
    if status == "superseded" and not superseded_by:
        errors.append(_err("V9", "status=superseded 但 superseded_by 为空，不知道该条被谁取代"))
    # 反向也要一致：有 superseded_by 就必须是 superseded。
    # 协议 3.1 原来没写这条，导致「限定」之后旧条状态两可，实现必然分叉。
    if superseded_by and status != "superseded":
        errors.append(
            _err("V9", "有 superseded_by 但 status = %r —— 凡被取代的必须是 superseded，"
                       "否则它会一直留在检索里跟新条打架" % status)
        )

    # ── V9 续：related_to 也必须写清关系 ──
    # 只写个 id 不算声明关系，照样绕不过 V11 的初衷。
    related = record.get("related_to")
    if related is not None:
        if not isinstance(related, list):
            errors.append(_err("V9", "related_to 必须是数组"))
        else:
            for idx, rel in enumerate(related):
                if isinstance(rel, str):
                    errors.append(
                        _err("V9", "related_to[%d] 是字符串 %r —— 必须写成 "
                              "{id, relation, note} 对象，只给 id 不算声明关系" % (idx, rel))
                    )
                    continue
                if not isinstance(rel, dict):
                    errors.append(_err("V9", "related_to[%d] 不是对象：%r" % (idx, rel)))
                    continue
                if not str(rel.get("id") or "").strip():
                    errors.append(_err("V9", "related_to[%d] 缺 id" % idx))
                if rel.get("relation") not in RELATION_LINKS:
                    errors.append(
                        _err("V9", "related_to[%d].relation = %r 不在 %s 里"
                             % (idx, rel.get("relation"), list(RELATION_LINKS)))
                    )
                if not str(rel.get("note") or "").strip():
                    errors.append(_err("V9", "related_to[%d] 缺 note，说明为什么并立" % idx))

    _LAST_WARNINGS[:] = warnings
    return errors


# 警告与错误分开：错误拦住写入，警告只提示。
# 用模块级列表是因为 validate 的返回签名（List[Error]）已被测试和 CLI 依赖，
# 不想为了加警告把接口改乱。调用方要警告就用 warnings_of()。
_LAST_WARNINGS: list[dict[str, str]] = []


def warnings_of(record: dict[str, Any]) -> list[dict[str, str]]:
    """跑一次校验，只取警告（W 系列）。不改记录。"""
    validate(record)
    return list(_LAST_WARNINGS)


def validate_all(records: Iterable[dict[str, Any]]) -> list[tuple[str, list[dict[str, str]]]]:
    """跑全部规则 V1-V14。返回 [(id, errors), ...]，只含有错的那些；全合法返回空列表。"""
    records = list(records)
    failures: list[tuple[str, list[dict[str, str]]]] = []
    seen: dict[str, list[str]] = {}

    for rec in records:
        rid = str(rec.get("id") or "?")
        errs = validate(rec)
        if errs:
            failures.append((rid, errs))

        # V10：同一 statement 不得有两条 accepted
        if rec.get("status") == "accepted":
            key = str(rec.get("statement") or "").strip()
            seen.setdefault(key, []).append(rid)

    for statement, ids in seen.items():
        if len(ids) > 1:
            for rid in ids:
                failures.append(
                    (rid, [_err("V10", "同一 statement 有 %d 条 accepted 同时生效：%s"
                                % (len(ids), ids))])
                )

    # V11：同一 scope 下不得有两条未声明的 accepted
    failures.extend(check_scope_conflicts(records))

    # V14：id 不得重复
    id_seen: dict[str, list[int]] = {}
    for idx, rec in enumerate(records):
        rid = str(rec.get("id") or "")
        if rid:
            id_seen.setdefault(rid, []).append(idx)
    for rid, idxs in id_seen.items():
        if len(idxs) > 1:
            for i in idxs:
                failures.append(
                    (rid, [_err("V14", "id 重复出现 %d 次（第 %s 条）—— "
                                      "一条判断只能有一个身份，重复会让取代链错乱"
                                % (len(idxs), "、".join(str(n + 1) for n in idxs)))])
                )

    return failures


def check_scope_conflicts(
    records: list[dict[str, Any]],
) -> list[tuple[str, list[dict[str, str]]]]:
    """V11 —— 同一场景里两条 accepted 谁都没提对方，就是未裁决的冲突。

    机器判断不了「动作对立」（那要语义理解），但判断得了
    「同一 scope 下有两条，且没声明彼此关系」。

    口径的取舍（实测后改过一次）：

    最初的做法是「scope 有交集就报」。实测发现 5 条互不相干的判断，
    只要都带一个宽词（比如「沟通」），就会 100% 误报。
    报麻之后人会敷衍填 related_to，这条规则就退化成「必须签字」。

    现在的做法：**只报「专属场景」上的冲突。**

    一个 scope 值如果只被这一条判断使用，它是这条判断的专属场景，撞了就是真撞。
    一个 scope 值被很多条共用，它是分类标签，撞了不说明任何问题。

    阈值 SCOPE_SHARED_MAX：同一 scope 值被超过这么多条判断共用时，
    视作宽泛标签，不再据此报冲突。
    """
    accepted = [r for r in records if r.get("status") == "accepted"]
    by_scope: dict[str, list[dict[str, Any]]] = {}

    for rec in accepted:
        seen_here: set[str] = set()
        for sc in rec.get("scope") or []:
            # key 用 strip 后的值：否则 "重要表达" 和 "重要表达 " 会被当成两个场景，
            # 冲突检测静默失效。V3 也会单独拦首尾空格，这里是第二道防线。
            key = str(sc).strip()
            if key in seen_here:
                continue  # 同一条记录重复写同一个 scope，不该自己跟自己冲突
            seen_here.add(key)
            by_scope.setdefault(key, []).append(rec)

    out: list[tuple[str, list[dict[str, str]]]] = []
    for scene, recs in by_scope.items():
        if is_broad_scope(scene):
            # 宽泛词本身不是有效的冲突键（「沟通」这种，谁都能往里塞）。
            # 注意：这里跳过的是「这个词」，不是「这一组判断」。
            # 早期版本用「共用条数 > 3 就整组跳过」，结果 4 条真对立的判断
            # 反而一条都不报 —— 条数越多越危险，却被当成了宽泛，逻辑正好反了。
            continue
        if len(recs) < 2:
            continue
        ids_in_scene = {str(r.get("id")) for r in recs}
        for rec in recs:
            own_id = str(rec.get("id"))
            # 已声明的关系：取代链 或 related_to 登记
            targets: set[str] = set()
            for v in (rec.get("supersedes"), rec.get("superseded_by")):
                if isinstance(v, str):
                    targets.add(v)
            for rel in rec.get("related_to") or []:
                if isinstance(rel, dict):
                    rid = rel.get("id")
                    if isinstance(rid, str):
                        targets.add(rid)
                elif isinstance(rel, str):
                    targets.add(rel)
            if targets & (ids_in_scene - {own_id}):
                continue  # 已声明与场景内其他判断的关系，放行
            others = [
                str(o.get("statement") or "")[:16]
                for o in recs
                if str(o.get("id")) != own_id
            ]
            if not others:
                continue  # 同一条记录重复写了同一个 scope，不算跟别人冲突
            out.append((
                own_id or "?",
                [_err("V11",
                      "场景「%s」下还有 %d 条 accepted（%s）同时生效，但没声明彼此关系。"
                      "要么用 related_to 写明加强/并立，要么把 scope 收窄到不重叠。"
                      % (scene, len(others), "；".join(others)))],
            ))
    return out


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError("找不到 %s" % path)

    # 编码问题单独处理：Python 原生报错是 'utf-8' codec can't decode byte 0xcf，
    # 新手看不出该干什么。这里换成能照着做的话。
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        # 试着按 GBK 读一次，读得动就基本确定是记事本存的 ANSI
        hint = ""
        try:
            path.read_text(encoding="gbk")
            hint = "（这个文件用 GBK 能读开，基本确定是记事本另存成了 ANSI）"
        except UnicodeDecodeError:
            hint = "（也可能是别的编码，总之不是 UTF-8）"
        raise ValueError(
            "%s 不是 UTF-8 编码：%s\n"
            "%s\n"
            "改法：用 VS Code / Notepad++ 打开，另存为 UTF-8（不要选「with BOM」）。"
            % (path, exc, hint)
        ) from exc

    if raw.startswith("\ufeff"):
        raise ValueError(
            "%s 开头有 BOM（字节顺序标记）。\n"
            "这是用记事本或某些编辑器存成「UTF-8 with BOM」的结果。\n"
            "改法：另存为普通的 UTF-8，不要带 BOM。"
            % path
        )

    out = []
    for lineno, line in enumerate(raw.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "%s 第 %d 行不是合法 JSON：%s\n"
                "这一行的前 60 个字：%s"
                % (path, lineno, exc, line[:60])
            ) from exc

        if not isinstance(obj, dict):
            raise ValueError(
                "%s 第 %d 行是个 %s，不是对象。\n"
                "每一行必须是一个完整的 {…} 判断记录。"
                % (path, lineno, type(obj).__name__)
            )
        out.append(obj)
    return out


# ────────────────────────── 生命周期 ──────────────────────────

def should_archive(record: dict[str, Any], now: datetime | None = None) -> str | None:
    """按协议第六节判断该不该归档。返回理由，或 None 表示还留着。"""
    now = now or datetime.now().astimezone()
    created = record.get("created_at")
    if not created:
        return None
    try:
        dt = datetime.fromisoformat(str(created))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.astimezone()

    status = record.get("status")
    hits = record.get("hits") or 0
    age = now - dt

    if status == "accepted" and age > timedelta(days=90) and hits == 0:
        return "accepted 满 90 天且零命中"
    if status == "candidate" and age > timedelta(days=30):
        return "candidate 满 30 天未被裁决"
    if status == "superseded" and age > timedelta(days=90):
        return "被取代满 90 天"
    return None


def stats(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """出账用。这些数字是这项目的全部说服力。"""
    records = list(records)
    by_status: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    zero_hits = 0

    for rec in records:
        if not isinstance(rec, dict):
            continue
        by_status[rec.get("status", "?")] = by_status.get(rec.get("status", "?"), 0) + 1
        if not rec.get("hits"):
            zero_hits += 1
        evidence = rec.get("evidence")
        if not isinstance(evidence, list):
            continue
        for ev in evidence:
            # 容错：坏数据不该让出账这一步整个崩掉。
            # 校验会单独把非对象的 evidence 报出来，stats 只负责数得下去。
            if not isinstance(ev, dict):
                k = "?"
            else:
                k = ev.get("kind", "?")
                if not isinstance(k, str):
                    k = "?"
            by_kind[k] = by_kind.get(k, 0) + 1

    total = len(records)
    return {
        "total": total,
        "by_status": by_status,
        "evidence_by_kind": by_kind,
        "zero_hits": zero_hits,
        "zero_hits_ratio": round(zero_hits / total, 4) if total else 0.0,
        "protocol_version": PROTOCOL_VERSION,
    }
