
import streamlit as st
from typing import Dict, Tuple, Optional


# ----------------------------
# 세션 저장소 접근
# ----------------------------
def get_limits_store() -> Dict:
    if "BOSS_LIMITS" not in st.session_state:
        st.session_state["BOSS_LIMITS"] = {}
    return st.session_state["BOSS_LIMITS"]


# ----------------------------
# 정규화 기반 필요 총 에너지
# required_energy = boss_hp / P
# P = Σ(dmg / eff_mp) = total_dmg_per_mp_sum
# ----------------------------
def compute_required_energy(boss_hp: float, P: float) -> float:
    if boss_hp <= 0:
        return 0.0
    if P <= 0:
        return float("inf")
    return boss_hp / P


def get_energy_limit(boss: str, party_type: str) -> Optional[float]:
    store = get_limits_store()
    pack = store.get(boss, {}).get(party_type)
    if not pack:
        return None
    return float(pack.get("energy_limit", 0.0))


def judge_clear(boss_hp: float, P: float, energy_limit: float) -> Tuple[bool, float, float]:
    """
    Returns:
      clear_ok (bool),
      required_energy (float),
      margin_pct (float)  # (+)면 여유, (-)면 부족
    """
    required_energy = compute_required_energy(boss_hp, P)
    if energy_limit <= 0 or required_energy == float("inf"):
        return False, required_energy, float("-inf")

    margin_pct = (energy_limit - required_energy) / energy_limit * 100.0
    clear_ok = required_energy <= energy_limit
    return clear_ok, required_energy, margin_pct


# ----------------------------
# ✅ 탭1/탭2에서 공통으로 쓰는 "판정 UI + 출력"
# ----------------------------
def render_clear_judge_box(
    boss: str,
    boss_hp: float,
    P: float,  # total_dmg_per_mp_sum
    party_type_options,
    default_party_type_index: int = 0,
    key_prefix: str = "judge",
):
    """
    boss: "사마귀" 등
    boss_hp: 최종 적용 보스 체력(증가옵/5인옵 반영 완료된 값)
    P: total_dmg_per_mp_sum
    party_type_options: ["빨강...", "파랑...", ...]
    """
    st.markdown("### ✅ 정규화 클리어 판정")

    party_type = st.selectbox(
        "클리어 기준 파티유형(정규화 판정용)",
        party_type_options,
        index=default_party_type_index,
        key=f"{key_prefix}_party_type",
    )

    energy_limit = get_energy_limit(boss, party_type)
    if energy_limit is None:
        st.info("선택한 보스/파티유형의 기준값(ENERGY_LIMIT)이 없어요. 탭3에서 먼저 저장해줘.")
        return

    clear_ok, required_energy, margin_pct = judge_clear(boss_hp=boss_hp, P=P, energy_limit=energy_limit)

    st.write(f"- 필요 총 에너지(required_energy = boss_hp / P): **{required_energy:,.0f}**")
    st.write(f"- ENERGY_LIMIT(총 에너지 예산): **{energy_limit:,.0f}**")

    if clear_ok:
        st.success(f"판정: **클리어 가능** (여유율 **{margin_pct:.1f}%**)")
    else:
        st.error(f"판정: **클리어 어려움** (부족 **{abs(margin_pct):.1f}%**)")


def judge_clear_for_table(
    boss: str,
    boss_hp: float,
    P: float,
    party_type: str,
):
    """
    탭2(비교 테이블)용: UI 없이 결과만 반환
    """
    energy_limit = get_energy_limit(boss, party_type)
    if energy_limit is None:
        return {
            "필요총에너지(boss_hp/P)": None,
            "ENERGY_LIMIT": None,
            "정규화판정": "NO_LIMIT",
            "여유율": None,
        }

    clear_ok, required_energy, margin_pct = judge_clear(boss_hp=boss_hp, P=P, energy_limit=energy_limit)
    return {
        "필요총에너지(boss_hp/P)": int(required_energy) if required_energy != float("inf") else None,
        "ENERGY_LIMIT": int(energy_limit),
        "정규화판정": "CLEAR" if clear_ok else "FAIL",
        "여유율": float(f"{margin_pct:.1f}"),
    }
