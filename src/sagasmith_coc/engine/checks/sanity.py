"""
CoC 7e 理智系统 (Sanity) — 理智损失、临时/不定期疯狂、狂乱发作。

核心规则:
    - SAN max = 99 - CthulhuMythos 技能值
    - 损失 ≥ 5 → 临时疯狂 (Temporary Insanity)
    - 当日累计 ≥ daily_limit → 不定期疯狂 (Indefinite Insanity)
    - 狂乱发作 (Bout of Madness): 投表决定具体症状
    - Pulp 规则: 可消耗 Luck 减半理智损失
"""

from enum import IntEnum
from typing import Any

from sagasmith_coc.engine.dice.rolls import roll_d100, roll_dice_expression
from sagasmith_coc.random_stream import randint
from sagasmith_coc.system import validate_investigator_sheet


class InsanityType(IntEnum):
    """疯狂类型"""
    NONE = 0
    TEMPORARY = 1      # 临时疯狂
    INDEFINITE = 2     # 不定期疯狂
    PERMANENT = 3      # 永久疯狂 (极端情况)


BOUT_TABLE_REAL = [
    ("失忆", "陷入失忆状态，不知道自己是谁。"),
    ("躯体症状", "出现身体症状如失明、失聪、颤抖。"),
    ("暴力倾向", "对周围人或物进行暴力攻击。"),
    ("偏执", "严重偏执，认为所有人都在迫害自己。"),
    ("重大人格", "人格发生重大改变。"),
    ("恐惧", "被强烈的恐惧支配。"),
    ("狂躁", "出现狂躁行为。"),
    ("幻觉", "出现强烈的幻觉。"),
    ("心理依赖", "对某人或某物产生心理依赖。"),
    ("昏厥", "直接昏厥。"),
]

BOUT_TABLE_SUMMARY = [
    ("失忆 / 神游", "茫然而行，无法记起自己的行为。"),
    ("躯体症状", "心脏狂跳、视力模糊、肌肉痉挛。"),
    ("退缩", "蜷缩哭泣，无法行动。"),
    ("暴力倾向", "对最近的人或物进行暴力攻击。"),
    ("偏执", "认为有人正在追杀自己，表现出极度的不信任。"),
    ("重大人格", "人格特质发生永久或半永久的改变。"),
    ("恐惧", "被强烈的恐惧支配，表现出回避行为。"),
    ("狂躁", "表现出难以自控的狂躁冲动。"),
    ("幻觉", "持续的幻觉影响正常判断。"),
    ("昏厥 / 假性死亡", "进入类似昏迷的状态。"),
]


def calculate_sanity_max(cthulhu_mythos_value: int = 0) -> int:
    """计算 SAN 上限 = 99 - CthulhuMythos"""
    return max(0, 99 - cthulhu_mythos_value)


def resolve_sanity_loss(
    current_san: int,
    san_max: int,
    loss_amount: int,
    daily_loss_accumulated: int = 0,
    daily_limit: int | None = None,
    cthulhu_mythos_value: int = 0,
    is_mythos_hardened: bool = False,
    pulp_rules: bool = False,
    investigator_name: str = "",
    source: str = "",
    int_check_success: bool | None = None,
) -> dict:
    """
    理智损失完整结算。

    参数:
        current_san: 当前 SAN 值
        san_max: SAN 上限
        loss_amount: 理智损失量
        daily_loss_accumulated: 当日已累计损失
        daily_limit: 当日上限 (默认 = current_san // 5)
        cthulhu_mythos_value: Cthulhu Mythos 技能值 (影响上限)
        is_mythos_hardened: 是否已对 Mythos 产生免疫
        pulp_rules: 是否启用 Pulp 规则 (可 Luck 减半)
        investigator_name: 调查员名称
        source: 损失来源描述

    返回:
        {
            "new_san": int,
            "actual_loss": int,       # 实际损失量
            "indef_insanity_daily_limit": int,
            "temp_insanity": bool,     # 是否进入临时疯狂
            "indef_insanity": bool,    # 是否进入不定期疯狂
            "insanity_type": str,      # "none" / "temporary" / "indefinite"
            "bout_of_madness": bool,   # 是否需要狂乱发作
            "detail_lines": list[str],
            "summary_line": str,
        }
    """
    detail_lines = []
    actual_loss = loss_amount

    # 应用 hardness 减免
    if is_mythos_hardened:
        actual_loss = max(0, actual_loss // 2)
        detail_lines.append(f"  (Mythos Hardened: 损失减半为 {actual_loss})")

    # 新 SAN 值
    new_san = max(0, current_san - actual_loss)
    new_san = min(new_san, san_max)

    # 单次损失 5+ 先触发 INT 检定；理解恐怖（INT 成功）才进入临时疯狂。
    requires_int_check = actual_loss >= 5
    temp_insanity = requires_int_check and int_check_success is True

    # 不定期疯狂判定
    new_daily_loss = daily_loss_accumulated + actual_loss
    daily_limit = daily_limit if daily_limit is not None else max(1, current_san // 5)
    indef_insanity = new_daily_loss >= daily_limit

    # 确定疯狂类型
    if new_san == 0:
        insanity_type = "permanent"
    elif indef_insanity:
        insanity_type = "indefinite"
    elif temp_insanity:
        insanity_type = "temporary"
    else:
        insanity_type = "none"

    bout_of_madness = temp_insanity or indef_insanity

    detail_lines.append(
        f"【理智损失】{investigator_name}：{source or '未知来源'}"
    )
    detail_lines.append(f"  → SAN {current_san} - {actual_loss} = {new_san}（上限 {san_max}）")

    if requires_int_check and int_check_success is None:
        detail_lines.append("  ⚠️ 单次损失 ≥ 5 → 需要 INT 检定")
    if temp_insanity:
        detail_lines.append("  ⚠️ INT 检定成功 → 临时疯狂")
        if indef_insanity:
            detail_lines.append(f"  ⚠️⚠️ 当日累计 {new_daily_loss}/{daily_limit} → 不定期疯狂！")
        else:
            detail_lines.append(f"  当日累计 {new_daily_loss}/{daily_limit}")

    summary = (
        f"{investigator_name} SAN: {current_san} → {new_san}"
        f" (损失 {actual_loss})"
    )
    if insanity_type == "indefinite":
        summary += " ⚠️ 不定期疯狂"
    elif insanity_type == "temporary":
        summary += " ⚠️ 临时疯狂"

    return {
        "new_san": new_san,
        "actual_loss": actual_loss,
        "daily_loss_accumulated": new_daily_loss,
        "daily_limit": daily_limit,
        "indef_insanity_daily_limit": daily_limit,
        "temp_insanity": temp_insanity,
        "indef_insanity": indef_insanity,
        "requires_int_check": requires_int_check and int_check_success is None,
        "int_check_success": int_check_success,
        "insanity_type": insanity_type,
        "bout_of_madness": bout_of_madness,
        "detail_lines": detail_lines,
        "summary_line": summary,
    }


def roll_bout_of_madness(real_time: bool = True) -> dict:
    """
    狂乱发作表掷骰。

    参数:
        real_time: True = 实时发作 (战斗轮中), False = 总结型 (幕间)

    返回:
        {
            "type": str,         # 狂乱类型名称
            "description": str,  # 症状描述
            "roll": int,         # d10 结果
            "is_phobia": bool,   # 是否恐惧症
            "is_mania": bool,    # 是否狂躁症
        }
    """
    table = BOUT_TABLE_REAL if real_time else BOUT_TABLE_SUMMARY
    roll = randint(1, 10)
    name, desc = table[roll - 1]

    return {
        "type": name,
        "description": desc,
        "roll": roll,
        "is_phobia": name in ("恐惧", "偏执"),
        "is_mania": name in ("狂躁", "暴力倾向"),
    }


def is_temporary_insanity(san_loss: int) -> bool:
    """判断是否触发临时疯狂（损失 ≥ 5）"""
    return san_loss >= 5


def calculate_daily_limit(current_san: int) -> int:
    """计算每日理智损失上限"""
    return max(1, current_san // 5)


def resolve_sanity_check(
    sheet: dict[str, Any],
    *,
    success_loss: str,
    failure_loss: str,
    source: str,
    context: str,
    investigator_name: str = "",
    event_id: str | None = None,
) -> dict[str, Any]:
    """Roll and apply one complete source-explicit SAN encounter.

    The caller owns random-stream persistence.  Installing a campaign stream
    with ``use_random_stream`` makes every roll in this transition auditable
    without moving stream authority into the system package.
    """

    source_value = " ".join(str(source or "").split()).strip()
    if not source_value or len(source_value) > 500:
        raise ValueError("source must contain 1 to 500 characters")
    if context not in {"real_time", "summary"}:
        raise ValueError("context must be real_time or summary")
    formulas = {
        "success": str(success_loss or "").strip(),
        "failure": str(failure_loss or "").strip(),
    }
    if not all(formulas.values()) or any(len(value) > 100 for value in formulas.values()):
        raise ValueError("success_loss and failure_loss must contain 1 to 100 characters")
    value = validate_investigator_sheet(sheet)
    current_san = int(value["san"])
    if current_san <= 0:
        raise ValueError("an actor with zero SAN cannot make another SAN check")

    sanity_roll = roll_d100()
    succeeded = int(sanity_roll["total"]) <= current_san
    selected_formula = formulas["success" if succeeded else "failure"]
    loss_roll = roll_dice_expression(selected_formula)
    if int(loss_roll["total"]) < 0:
        raise ValueError("SAN loss expressions must not produce a negative result")
    int_roll = None
    int_success = None
    if int(loss_roll["total"]) >= 5:
        int_roll = roll_d100()
        int_success = int(int_roll["total"]) <= int(value["characteristics"]["int"])
    outcome = resolve_sanity_loss(
        current_san=current_san,
        san_max=int(value["san_max"]),
        loss_amount=int(loss_roll["total"]),
        daily_loss_accumulated=int(value.get("san_daily_loss", 0)),
        daily_limit=int(value.get("san_daily_limit", max(1, current_san // 5))),
        cthulhu_mythos_value=int(value.get("cthulhu_mythos", 0)),
        is_mythos_hardened=bool(value.get("mythos_hardened", False)),
        pulp_rules=str(value.get("ruleset") or "classic") == "pulp",
        investigator_name=investigator_name,
        source=source_value,
        int_check_success=int_success,
    )
    bout = None
    if outcome["bout_of_madness"]:
        bout = {
            **roll_bout_of_madness(real_time=context == "real_time"),
            "duration": roll_dice_expression("1D10"),
            "duration_unit": "rounds" if context == "real_time" else "hours",
        }
    conditions = dict(value.get("conditions") or {})
    conditions["temporary_insanity"] = bool(outcome["temp_insanity"])
    conditions["indefinite_insanity"] = bool(outcome["indef_insanity"])
    conditions["permanent_insanity"] = outcome["insanity_type"] == "permanent"
    event = {
        "source": source_value,
        "context": context,
        "sanity_roll": sanity_roll,
        "succeeded": succeeded,
        "loss_formula": selected_formula,
        "loss_roll": loss_roll,
        "int_roll": int_roll,
        "outcome": outcome,
        "bout": bout,
    }
    if str(event_id or "").strip():
        event["idempotency_key"] = str(event_id).strip()
    value["conditions"] = conditions
    value["san"] = int(outcome["new_san"])
    value["san_daily_loss"] = int(outcome["daily_loss_accumulated"])
    value["sanity_loss_events"] = [
        *list(value.get("sanity_loss_events") or [])[-499:],
        event,
    ]
    return {
        "sheet": validate_investigator_sheet(value),
        "event": event,
        "san": int(outcome["new_san"]),
        "conditions": conditions,
    }
