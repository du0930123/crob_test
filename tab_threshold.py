import math
import streamlit as st
from typing import Dict, Any
from boss_limits_store import get_limits_store, save_limits

# ✅ clear_judge.py에 아래 함수가 있어야 함:
# - party_to_mp_share_vector(party) -> Dict[str, float]
from clear_judge import party_to_mp_share_vector


def render_threshold_tab(COLOR_OPTIONS, build_party_from_text, calculate_party, admin_mode: bool = False):
    st.subheader("📌 파티사이클 클리어 여부 경계값 (정규화 적용)")

    # 보스 목록
    BOSS_LIST = ["사마귀", "두억시니"]

    # (표시용) 경험적 가이드: 파티유형 라벨별 텍스트
    BOSS_GUIDE = {
        "사마귀": {
            "빨강(주로 비트 구성)": "105 ~ 110회",
            "파랑(눈설탕, 캡아 구성)": "105 ~ 110회",
            "노랑(주로 스네 구성)": "155회 내외",
            "빨강(주로 인삼 구성)": "데이터 없음",
        },
        "두억시니": {
            "빨강(주로 비트 구성)": "120 ~ 125회",
            "파랑(눈설탕, 캡아 구성)": "120 ~ 125회",
            "노랑(주로 스네 구성)": "170회 내외",
            "빨강(주로 인삼 구성)": "데이터 없음",
        }
    }

    boss = st.selectbox("보스 선택", BOSS_LIST, index=0)

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

    # ✅ party_type은 '표시/추천용 라벨'로만 유지 (판정에서는 무시)
    party_type_label = st.radio(
        "파티 유형 선택(표시/추천용)",
        ["빨강(주로 비트 구성)", "빨강(주로 인삼 구성)",
         "파랑(눈설탕, 캡아 구성)", "노랑(주로 스네 구성)"],
        index=0
    )

    st.markdown("### 경험적 파티사이클 경계(표시용)")
    guide = BOSS_GUIDE.get(boss, {})
    cycle_text = guide.get(party_type_label, "데이터 없음")
    st.write(f"- 기준: **{cycle_text}**")
    st.markdown("---")

    # 🔒 관리자 영역
    if admin_mode:
        st.markdown("### ✅ 정규화 기준 저장(캘리브레이션)")
        st.caption("관리자가 기준 파티/경계 사이클을 저장하면 boss_limits.json에 반영되어 모든 접속자에게 동일하게 적용돼요.")
        st.caption("※ 저장은 party_type을 '분류로 쓰지 않고', 보스별 profiles 풀에 누적 저장됩니다. (판정 시 자동 거리/가중치로 사용)")

        # 기준 파티 기본값(라벨에 따라 추천만)
        default_party = {
            "빨강(주로 비트 구성)": "비트 1 레판 4",
            "빨강(주로 인삼 구성)": "인삼 3 비트 1 레판 1",
            "파랑(눈설탕, 캡아 구성)": "눈설탕 3 캡틴아이스 1",
            "노랑(주로 스네 구성)": "스네이크 3 캡틴아이스 1",
        }.get(party_type_label, "스네이크 3 캡틴아이스 1")

        ref_party_text = st.text_input(
            "기준 파티(텍스트)",
            value=default_party,
            key=f"ref_party_{boss}_{party_type_label}"
        )

        # 기본 경계 사이클(라벨 기준 추천만)
        default_cycles_map = {
            "사마귀": {
                "빨강(주로 비트 구성)": 110,
                "파랑(눈설탕, 캡아 구성)": 110,
                "노랑(주로 스네 구성)": 155,
                "빨강(주로 인삼 구성)": 110,
            },
            "두억시니": {
                "빨강(주로 비트 구성)": 125,
                "파랑(눈설탕, 캡아 구성)": 125,
                "노랑(주로 스네 구성)": 170,
                "빨강(주로 인삼 구성)": 125,
            }
        }
        default_cycles = default_cycles_map.get(boss, {}).get(party_type_label, 110)

        threshold_cycles = st.number_input(
            "경계 파티사이클(회)",
            min_value=1,
            value=int(default_cycles),
            step=1,
            key=f"threshold_cycles_{boss}_{party_type_label}"
        )

        st.markdown("#### 기준 파티 계산 옵션(탭1/2와 동일하게 맞추는 게 권장)")

        weakness_colors = st.multiselect(
            "보스 약점 색 선택(최대 2개)",
            options=COLOR_OPTIONS,
            default=[],
            key=f"ref_weak_{boss}_{party_type_label}"
        )
        if len(weakness_colors) > 2:
            weakness_colors = weakness_colors[:2]

        weakness_bonus_by_color: Dict[str, float] = {}
        energy_decrease_by_color: Dict[str, float] = {}

        if weakness_colors:
            st.markdown("##### 약점 색별 조건부 피해증가율(%) / 에너지획득량감소(%)")
            for wc in weakness_colors:
                pct = st.number_input(
                    f"{wc} 색 피해증감율(%)",
                    min_value=-300.0, max_value=300.0,
                    value=0.0, step=1.0,
                    key=f"ref_weak_pct_{boss}_{party_type_label}_{wc}"
                )
                weakness_bonus_by_color[wc] = pct / 100.0

                e_on = st.checkbox(
                    f"{wc}색 에너지획득량감소 적용",
                    key=f"ref_energy_on_{boss}_{party_type_label}_{wc}"
                )
                if e_on:
                    e_pct = st.number_input(
                        f"{wc}색 에너지 획득량 감소(%)",
                        min_value=0.0, max_value=300.0,
                        value=0.0, step=1.0,
                        key=f"ref_energy_pct_{boss}_{party_type_label}_{wc}"
                    )
                    energy_decrease_by_color[wc] = e_pct / 100.0

        col1, col2 = st.columns(2)
        with col1:
            common_damage_buff_pct = st.number_input(
                "공통 피해증가율(%)",
                min_value=0.0, max_value=1000.0,
                value=42.0, step=1.0,
                key=f"ref_common_{boss}_{party_type_label}"
            )
        with col2:
            stone_crit_buff_pct = st.number_input(
                "돌옵션 치명타 피해 증가율(%)",
                min_value=0.0, max_value=1000.0,
                value=0.0, step=1.0,
                key=f"ref_crit_{boss}_{party_type_label}"
            )

        # ✅ 저장 버튼
        if st.button("✅ 이 보스 기준 프로필 저장(party_type 무시)", key=f"save_profile_{boss}_{party_type_label}"):
            try:
                party = build_party_from_text(ref_party_text)

                total_dmg, total_dmg_per_mp_sum, total_mp, _, _, _ = calculate_party(
                    party=party,
                    common_damage_buff=common_damage_buff_pct / 100.0,
                    stone_crit_buff=stone_crit_buff_pct / 100.0,
                    weakness_bonus_by_color=weakness_bonus_by_color,
                    energy_decrease_by_color=energy_decrease_by_color,
                )

                # ENERGY_LIMIT = 경계 회수 * (기준 파티 1사이클 총 MP)
                energy_limit = float(threshold_cycles) * float(total_mp)

                # ✅ 핵심: ref_vec 저장(거리/가중치 계산에 사용)
                ref_vec = party_to_mp_share_vector(party)

                store = get_limits_store()
                store.setdefault(boss, {})
                store[boss].setdefault("profiles", [])

                store[boss]["profiles"].append({
                    # 판정에 직접 쓰는 핵심 3개
                    "energy_limit": float(energy_limit),
                    "ref_party": ref_party_text,
                    "ref_vec": ref_vec,

                    # 나머지는 참고/디버그/관리용 메타
                    "label": party_type_label,  # ✅ 분류로 저장하되 판정에는 사용 안 함
                    "threshold_cycles": int(threshold_cycles),
                    "ref_total_mp": int(total_mp),
                    "ref_P": float(total_dmg_per_mp_sum),
                    "ref_common": float(common_damage_buff_pct / 100.0),
                    "ref_stone_crit": float(stone_crit_buff_pct / 100.0),
                    "ref_weakness_bonus_by_color": dict(weakness_bonus_by_color),
                    "ref_energy_decrease_by_color": dict(energy_decrease_by_color),
                })

                save_limits(store)  # ✅ JSON에 영구 저장 (모든 접속자 공유)

                st.success(f"저장 완료! ENERGY_LIMIT = {energy_limit:,.0f}")
                st.caption(f"- 기준 파티 1사이클 총 MP = {total_mp:,}")
                st.caption(f"- 기준 파티 P(Σ(dmg/eff_mp)) = {total_dmg_per_mp_sum:,.2f}")

            except Exception as e:
                st.error(str(e))

        # ✅ 현재 저장된 값 표시(관리자만)
        st.markdown("---")
        st.markdown("### 📦 현재 저장된 프로필(관리자)")

        store = get_limits_store()
        profs = store.get(boss, {}).get("profiles", [])

        if profs:
            st.write(f"- 보스: **{boss}** / 저장된 프로필 수: **{len(profs)}개**")
            # 너무 길어지면 최신 10개만 보여주기
            show_n = min(10, len(profs))
            st.caption(f"최근 {show_n}개만 표시")
            for i, p in enumerate(profs[-show_n:], start=max(1, len(profs) - show_n + 1)):
                st.write(
                    f"{i}. [{p.get('label','-')}] ENERGY_LIMIT={float(p.get('energy_limit',0)):,.0f}  |  기준파티=`{p.get('ref_party','')}`"
                )
        else:
            st.info("아직 저장된 프로필이 없어요. 위에서 저장해줘.")

    else:
        st.info("기준값 설정은 관리자만 가능해요.")
