import json
import os
import streamlit as st
from typing import Dict, Any

DEFAULT_PATH = "boss_limits.json"


def _ensure_session():
    if "BOSS_LIMITS" not in st.session_state:
        st.session_state["BOSS_LIMITS"] = {}


def load_limits(path: str = DEFAULT_PATH) -> Dict[str, Any]:
    _ensure_session()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                st.session_state["BOSS_LIMITS"] = json.load(f) or {}
        except Exception:
            st.session_state["BOSS_LIMITS"] = {}
    else:
        st.session_state["BOSS_LIMITS"] = {}
        # 파일도 하나 만들어둠(선택)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return st.session_state["BOSS_LIMITS"]


def save_limits(store: Dict[str, Any], path: str = DEFAULT_PATH) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, path)


def get_limits_store(path: str = DEFAULT_PATH) -> Dict[str, Any]:
    if "BOSS_LIMITS" not in st.session_state:
        load_limits(path)
    return st.session_state["BOSS_LIMITS"]
