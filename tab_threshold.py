import math
import streamlit as st
from typing import Dict


def get_limits_store():
    if "BOSS_LIMITS" not in st.session_state:
        st.session_state["BOSS_LIMITS"] = {}
    return st.session_state["BOSS_LIMITS"]


def render_threshold_tab(COLOR_OPTIONS, build_party_from_text, calculate_party, admin_mode: bool = False):
    st.subheader("📌 파티사이클 클리어 여부 경계값 (정규화 적용)")

    # 보스 목록
    BOSS_LIST = ["사마귀", "두억시니"]

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

    party_type = st.radio(
        "파티 유형 선택",
        ["빨강(주로 비트 구성)", "빨강(주로 인삼 구성)",
         "파랑(눈설탕, 캡아 구성)", "노랑(주로 스네 구성)"],
        index=0
    )

    st.markdown("### 경험적 파티사이클 경계")
    guide = BOSS_GUIDE.get(boss, {})
    cycle_text = guide.get(party_type, "데이터 없음")
    st.write(f"- 기준: **{cycle_text}**")
    st.markdown("---")

    # 🔒 관리자 영역
    if admin_mode:
        st.markdown("### ✅ 정규화 기준 저장(캘리브레이션)")
        st.write("관리자 모드에서만 보이는 영역입니다.")
    else:
        st.info("기준값 설정은 관리자만 가능해요.")
