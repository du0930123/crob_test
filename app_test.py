import streamlit as st

from src.boss_limits_store import load_limits
from src.ui.common import init_session_state, render_header, render_footer, render_admin_login
from src.ui.tab_single import render_single_party_tab
from src.ui.tab_compare import render_party_compare_tab
from src.ui.tab_threshold_page import render_threshold_page


st.set_page_config(
    page_title="CROB 파티 딜 계산",
    page_icon="🧮",
    layout="wide",
)


def main():
    load_limits()
    init_session_state()

    admin_mode = render_admin_login()

    render_header()

    tab1, tab2, tab3 = st.tabs(
        [
            "단일 파티 계산",
            "파티 여러 개 비교",
            "파티사이클 클리어 경계값",
        ]
    )

    with tab1:
        render_single_party_tab()

    with tab2:
        render_party_compare_tab()

    with tab3:
        render_threshold_page(admin_mode)

    render_footer()


if __name__ == "__main__":
    main()
