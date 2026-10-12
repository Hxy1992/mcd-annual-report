"""「麦格」人格模型：基于订单数据的原创四维标签体系。

四个维度（刻意避开 MBTI 商标，命名与解释全部原创）：
- 探索型 E ↔ 忠诚型 L：餐品多样度（不同餐品数 / 总件数）
- 晨型 M ↔ 夜型 N：下单时段分布（夜宵单占比）
- 独食 S ↔ 群享 G：单均件数（一件到底 vs 大包大揽）
- 尝鲜型 T ↔ 守旧型 C：复购集中度（TOP1 餐品件数占比）

数据不足时各维度给默认值（L/M/S/C 保守侧），保证 16 型永远有完整解读。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .analyzer import YearStats

# 维度阈值
VARIETY_E_THRESHOLD = 0.30  # 多样度高于此值为探索型
NIGHT_N_THRESHOLD = 0.20  # 夜宵单占比高于此值为夜型
GROUP_G_THRESHOLD = 2.0  # 单均件数高于此值为群享
CLASSIC_C_THRESHOLD = 0.35  # TOP1 餐品占比高于此值为守旧

# 16 型名称与解读（原创文案，趣味但不贬损）
PERSONA_TYPES: dict[str, dict] = {
    "EMST": {"name": "麦门先锋派", "tagline": "清晨的第一口探索，从不安分", "desc": "你是最早到店的那批人，菜单是你的探险地图。别人纠结标配的时候，你已经试完了三个新品。"},
    "EMSC": {"name": "晨间经典猎手", "tagline": "太阳升起时，本命堡也不会缺席", "desc": "清晨的胃口最诚实：永远是那一口经典。你不是不爱尝鲜，只是经典更需要你的守护。"},
    "EMGT": {"name": "早场组局王", "tagline": "早餐也要整整齐齐", "desc": "你的早餐订单从来不止一件。身边人还没醒，你已经替全组规划好了今天的碳水量。"},
    "EMGC": {"name": "晨光固定班底", "tagline": "晨间的舒适区，也是你的统治区", "desc": "固定的时段、固定的搭配、稳定的心安。早餐对你来说不是选择，是仪式。"},
    "ENST": {"name": "深夜探险家", "tagline": "城市的夜，你的第二张菜单", "desc": "夜宵时段的麦门常客。夜色越深，你点单的手越稳，创意搭配也越大胆。"},
    "ENSC": {"name": "守夜经典党", "tagline": "深夜的安慰，还是熟悉的味道", "desc": "深夜的胃最恋旧。别人凌晨emo，你用一份经典组合把夜接住。"},
    "ENGT": {"name": "午夜狂欢发起人", "tagline": "夜生活的加油站，就是你", "desc": "你的夜宵订单量大品类多，朋友们嘴上说不吃，身体都很诚实地接了你的分享。"},
    "ENGC": {"name": "夜宵老根据地", "tagline": "固定的夜，固定的那口", "desc": "深夜档的忠实会员。一家店、几件套，吃的是味道，更是踏实。"},
    "LMST": {"name": "本命店尝鲜家", "tagline": "店不变，味要新", "desc": "你认准一家店，却从不重复自己的餐盘。熟悉的环境里，永远留着给新品的位置。"},
    "LMSC": {"name": "舒适区美食家", "tagline": "把喜欢的事情做到极致", "desc": "本命门店加经典搭配，你把一顿快餐吃成了个人流派。稳定，是一种天赋。"},
    "LMGT": {"name": "熟人局发动机", "tagline": "你出现，这局就稳了", "desc": "你可能不是点最多的人，但一定是让大家都能吃上饭的那个人。拼单群不能没有你。"},
    "LMGC": {"name": "麦门老伙计", "tagline": "老位置、老搭档、老味道", "desc": "店员认得你，你也认得菜单。这份熟络，是日复一日点出来的交情。"},
    "LNST": {"name": "夜间新品尝鲜员", "tagline": "白天的克制，交给深夜放纵", "desc": "白天随意对付，深夜认真尝鲜。你的账单里藏着麦门另一半秘密。"},
    "LNSC": {"name": "深夜固定档", "tagline": "夜再深，也有固定的陪伴", "desc": "夜宵只点那几样，不是无趣，是知道自己要什么。深夜的确定性最珍贵。"},
    "LNGT": {"name": "夜局新晋红人", "tagline": "入局不久，已是焦点", "desc": "你的夜晚热闹又新鲜，新品和好友都不错过。夜宵局有你在，冷场是不可能的。"},
    "LNGC": {"name": "老位置夜猫子", "tagline": "深夜的老地方，留着老习惯", "desc": "固定的深夜时段、固定的几样餐品。你的夜，比很多人的白天都规律。"},
}


@dataclass
class Persona:
    code: str
    dims: dict = field(default_factory=dict)  # {"explore": "E", ...}
    type_name: str = ""
    tagline: str = ""
    desc: str = ""
    highlights: list = field(default_factory=list)  # 支撑该标签的数据亮点


def _variety_ratio(stats: YearStats) -> float:
    if stats.total_items <= 0:
        return 0.0
    return stats.unique_items / stats.total_items


def infer_persona(stats: YearStats) -> Persona:
    """由统计结果推导麦格人格；无数据时返回默认型。"""
    if stats.total_orders == 0:
        p = PERSONA_TYPES["LMGC"]
        return Persona(code="LMGC", dims={"loyalty": "L", "rhythm": "M", "social": "S", "taste": "C"},
                       type_name=p["name"], tagline=p["tagline"], desc=p["desc"],
                       highlights=["还没有订单数据，先从一单开始认识自己"])

    dims = {
        "loyalty": "E" if _variety_ratio(stats) >= VARIETY_E_THRESHOLD else "L",
        "rhythm": "N" if stats.night_ratio >= NIGHT_N_THRESHOLD else "M",
        "social": "G" if stats.avg_items_per_order >= GROUP_G_THRESHOLD else "S",
        "taste": "C" if stats.top_item_ratio >= CLASSIC_C_THRESHOLD else "T",
    }
    code = dims["loyalty"] + dims["rhythm"] + dims["social"] + dims["taste"]
    t = PERSONA_TYPES.get(code, PERSONA_TYPES["LMGC"])

    highlights: list[str] = []
    if stats.unique_items:
        highlights.append(f"吃过的餐品 {stats.unique_items} 种")
    if stats.top_items:
        name, qty, _ = stats.top_items[0]
        highlights.append(f"最常点「{name}」×{qty}")
    top_slot = max(stats.time_slots.items(), key=lambda x: x[1])[0] if stats.time_slots else "午餐"
    highlights.append(f"最常在「{top_slot}」时段出没")
    if stats.top_stores:
        highlights.append(f"根据地：{stats.top_stores[0][0]}")

    return Persona(
        code=code,
        dims=dims,
        type_name=t["name"],
        tagline=t["tagline"],
        desc=t["desc"],
        highlights=highlights,
    )


DIM_LABELS = {
    "loyalty": ("探索型", "忠诚型"),
    "rhythm": ("晨型", "夜型"),
    "social": ("独食", "群享"),
    "taste": ("尝鲜型", "守旧型"),
}
