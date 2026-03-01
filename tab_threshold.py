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
        # 🔐 운영자 인증 (비밀번호: 0930)
        if "IS_ADMIN" not in st.session_state:
            st.session_state["IS_ADMIN"] = False

        st.markdown("### 🔐 운영자 인증")
        pw = st.text_input("관리자 비밀번호", type="password", key="admin_pw_input")

        colA, colB = st.columns(2)
        with colA:
            if st.button("로그인", key="admin_login_btn"):
                st.session_state["IS_ADMIN"] = (pw == "0930")
        with colB:
            if st.button("로그아웃", key="admin_logout_btn"):
                st.session_state["IS_ADMIN"] = False

        is_admin = bool(st.session_state["IS_ADMIN"])
        if not is_admin:
            st.info("관리자 기능(저장/삭제)은 비밀번호 인증 후 사용 가능해요.")
            return

        last = st.session_state.get("LAST_CALC_OPTS", {})
        if not last:
            st.info("최근 계산 옵션이 없어요. 탭1 또는 탭2에서 먼저 '계산'을 한 번 실행해줘.")
            return

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

        # ✅ 저장 버튼
        if st.button("✅ 이 보스 기준 프로필 저장(party_type 무시)", key=f"save_profile_{boss}_{party_type_label}"):
            try:
                party = build_party_from_text(ref_party_text)

                # ✅ LAST_CALC_OPTS를 그대로 사용 (A안)
                common_damage_buff_pct = float(last.get("common_damage_buff_pct", 0.0))
                stone_crit_buff_pct = float(last.get("stone_crit_buff_pct", 0.0))
                weakness_bonus_by_color = dict(last.get("weakness_bonus_by_color", {}) or {})
                energy_decrease_by_color = dict(last.get("energy_decrease_by_color", {}) or {})

                total_dmg, total_dmg_per_mp_sum, total_mp, _, _, _ = calculate_party(
                    party=party,
                    common_damage_buff=common_damage_buff_pct / 100.0,
                    stone_crit_buff=stone_crit_buff_pct / 100.0,
                    weakness_bonus_by_color=weakness_bonus_by_color,
                    energy_decrease_by_color=energy_decrease_by_color,
                )

                energy_limit = float(threshold_cycles) * float(total_mp)
                ref_vec = party_to_mp_share_vector(party)

                store = get_limits_store()
                store.setdefault(boss, {})
                store[boss].setdefault("profiles", [])

                store[boss]["profiles"].append({
                    "energy_limit": float(energy_limit),
                    "ref_party": ref_party_text,
                    "ref_vec": ref_vec,
                    "label": party_type_label,
                    "threshold_cycles": int(threshold_cycles),
                    "ref_total_mp": int(total_mp),
                    "ref_P": float(total_dmg_per_mp_sum),
                    "ref_common_damage_buff_pct": common_damage_buff_pct,
                    "ref_stone_crit_buff_pct": stone_crit_buff_pct,
                    "ref_weakness_bonus_by_color": weakness_bonus_by_color,
                    "ref_energy_decrease_by_color": energy_decrease_by_color,
                })

                save_limits(store)

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

            st.markdown("### 🗑 프로필 1개 삭제(관리자)")
            sel_idx = st.selectbox(
                "삭제할 프로필 선택",
                options=list(range(len(profs))),
                format_func=lambda i: f"{i+1}. [{profs[i].get('label','-')}] ENERGY_LIMIT={float(profs[i].get('energy_limit',0)):,.0f} | {profs[i].get('ref_party','')}",
                key=f"del_profile_idx_{boss}"
            )

            col_del1, col_del2 = st.columns([1, 2])
            with col_del1:
                confirm = st.checkbox("삭제 확인", key=f"del_confirm_{boss}")
            with col_del2:
                if st.button("선택 프로필 삭제", key=f"del_btn_{boss}", disabled=not confirm):
                    try:
                        profs.pop(sel_idx)
                        store[boss]["profiles"] = profs
                        save_limits(store)
                        st.success("선택한 프로필을 삭제했어. (모든 유저에게 즉시 반영)")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

            st.markdown("---")
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
