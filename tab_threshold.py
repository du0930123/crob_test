import math
import streamlit as st
from typing import Dict

def render_threshold_tab():
    st.subheader("📌 파티사이클 클리어 여부 경계값 (정규화 적용)")

    # 보스 선택 (확장 가능)
    boss = st.selectbox("보스 선택", ["사마귀"], index=0)

    # 조건 표시(참고 문구 유지)
    st.markdown("### 조건")
    conditions = [
        "게임속도 증가 없음",
        "보스 약화에 따른 딜량 증가를 반영하지 않음",
        "빌드에 능숙한 5인 파티",
        "4페를 어느정도 버틸 수 있을 만큼, 체력 여유가 있는 상태",
    ]
    for c in conditions:
        st.write(f"- {c}")
    st.markdown("---")

    # 파티 유형
    party_type = st.radio(
        "파티 유형 선택",
        ["빨강(주로 비트 구성)", "빨강(주로 인삼 구성)", "파랑(눈설탕, 캡아 구성)", "노랑(주로 스네 구성)"],
        index=0
    )

    # ✅ 기존 경험적 가이드(표시용)
    st.markdown("### (표시용) 기존 경험적 파티사이클 경계")
    if party_type in ["빨강(주로 비트 구성)", "파랑(눈설탕, 캡아 구성)"]:
        st.write("- 기준: **105 ~ 110회**")
    elif party_type == "노랑(주로 스네 구성)":
        st.write("- 기준: **155회 내외**")
    else:
        st.write("- 기준: **데이터 없음**")
    st.markdown("---")

    st.markdown("### ✅ 정규화 기준 저장(캘리브레이션)")
    st.caption("이 탭에서 '기준 파티'와 '경계 파티사이클(예: 110)'을 입력하면, 보스/파티유형별 ENERGY_LIMIT(총 에너지 예산)이 저장돼요.")
    st.caption("이후 탭1/2에서 required_energy(=boss_hp/P) 와 ENERGY_LIMIT 를 비교해서 클리어 판정을 합니다.")

    # 기준 파티 입력
    default_party = {
        "빨강(주로 비트 구성)": "비트 1 레판 4",
        "빨강(주로 인삼 구성)": "인삼 3 비트 1 레판 1",
        "파랑(눈설탕, 캡아 구성)": "눈설탕 3 캡틴아이스 1",
        "노랑(주로 스네 구성)": "스네이크 3 캡틴아이스 1",
    }.get(party_type, "스네이크 3 캡틴아이스 1")

    ref_party_text = st.text_input("기준 파티(텍스트)", value=default_party, key=f"ref_party_{boss}_{party_type}")

    # 경계 파티사이클(입력)
    threshold_cycles = st.number_input(
        "경계 파티사이클(회) (예: 110 또는 155)",
        min_value=1,
        value=110 if party_type in ["빨강(주로 비트 구성)", "파랑(눈설탕, 캡아 구성)"] else 155,
        step=1,
        key=f"threshold_cycles_{boss}_{party_type}"
    )

    # 기준 파티 계산에 필요한 옵션들(탭1/2와 동일 축)
    st.markdown("#### 기준 파티 계산 옵션(탭1/2와 동일하게 맞추는 게 권장)")
    weakness_colors = st.multiselect("보스 약점 색 선택(최대 2개)", options=COLOR_OPTIONS, default=[], key=f"ref_weak_{boss}_{party_type}")
    if len(weakness_colors) > 2:
        weakness_colors = weakness_colors[:2]

    weakness_bonus_by_color: Dict[str, float] = {}
    energy_decrease_by_color: Dict[str, float] = {}

    if weakness_colors:
        st.markdown("##### 약점 색별 조건부 피해증가율(%)")
        for wc in weakness_colors:
            pct = st.number_input(
                f"{wc} 색 피해증감율(%)",
                min_value=-300.0, max_value=300.0, value=0.0, step=1.0,
                key=f"ref_weak_pct_{boss}_{party_type}_{wc}"
            )
            weakness_bonus_by_color[wc] = pct / 100.0

            energy_on = st.checkbox(f"{wc}색 에너지획득량감소 적용", key=f"ref_energy_on_{boss}_{party_type}_{wc}")
            if energy_on:
                e_pct = st.number_input(
                    f"{wc}색 에너지 획득량 감소(%)",
                    min_value=0.0, max_value=300.0, value=0.0, step=1.0,
                    key=f"ref_energy_pct_{boss}_{party_type}_{wc}"
                )
                energy_decrease_by_color[wc] = e_pct / 100.0

    col1, col2 = st.columns(2)
    with col1:
        common_damage_buff_pct = st.number_input(
            "공통 피해증가율(%)",
            min_value=0.0, max_value=1000.0, value=42.0, step=1.0,
            key=f"ref_common_{boss}_{party_type}"
        )
    with col2:
        stone_crit_buff_pct = st.number_input(
            "돌옵션 치명타 피해 증가율(%)",
            min_value=0.0, max_value=1000.0, value=0.0, step=1.0,
            key=f"ref_crit_{boss}_{party_type}"
        )

    # 저장 버튼
    if st.button("✅ 이 보스/파티유형 기준값 저장", key=f"save_limit_{boss}_{party_type}"):
        try:
            party = build_party_from_text(ref_party_text)

            total_dmg, total_dmg_per_mp_sum, total_mp, _, _, _ = calculate_party(
                party=party,
                common_damage_buff=common_damage_buff_pct / 100.0,
                stone_crit_buff=stone_crit_buff_pct / 100.0,
                weakness_bonus_by_color=weakness_bonus_by_color,
                energy_decrease_by_color=energy_decrease_by_color,
            )

            # ✅ ENERGY_LIMIT = 경계 회수 * (기준 파티의 1사이클 총 MP)
            energy_limit = float(threshold_cycles) * float(total_mp)

            store = get_limits_store()
            if boss not in store:
                store[boss] = {}
            store[boss][party_type] = {
                "energy_limit": energy_limit,
                "ref_party": ref_party_text,
                "threshold_cycles": int(threshold_cycles),
                "ref_total_mp": int(total_mp),
                "ref_P": float(total_dmg_per_mp_sum),
                "ref_common": float(common_damage_buff_pct / 100.0),
                "ref_stone_crit": float(stone_crit_buff_pct / 100.0),
                "ref_weakness_bonus_by_color": dict(weakness_bonus_by_color),
                "ref_energy_decrease_by_color": dict(energy_decrease_by_color),
            }

            st.success(f"저장 완료! ENERGY_LIMIT = {energy_limit:,.0f} (총 에너지 예산)")
            st.caption(f"- 기준 파티 1사이클 총 MP = {total_mp:,}")
            st.caption(f"- 기준 파티 P(Σ(dmg/eff_mp)) = {total_dmg_per_mp_sum:,.2f}")

        except Exception as e:
            st.error(str(e))

    # 현재 저장된 값 표시
    st.markdown("---")
    st.markdown("### 📦 현재 저장된 기준값")
    store = get_limits_store()
    cur = store.get(boss, {}).get(party_type)
    if cur:
        st.write(f"- 보스: **{boss}** / 유형: **{party_type}**")
        st.write(f"- ENERGY_LIMIT(총 에너지 예산): **{cur['energy_limit']:,.0f}**")
        st.write(f"- 기준 파티: `{cur['ref_party']}`")
        st.write(f"- 경계 파티사이클: **{cur['threshold_cycles']}회**")
        st.write(f"- 기준 파티 1사이클 총 MP: **{cur['ref_total_mp']:,}**")
    else:
        st.info("아직 이 보스/유형에 저장된 기준값이 없어요. 위에서 저장해줘.")
