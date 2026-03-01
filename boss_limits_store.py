import json
import os
import streamlit as st
from typing import Dict, Any

DEFAULT_PATH = "boss_limits.json"


def _ensure_session():
    if "BOSS_LIMITS" not in st.session_state:
        st.session_state["BOSS_LIMITS"] = {}


def _migrate_limits_store(store: Dict[str, Any]) -> Dict[str, Any]:
    """
    boss_limits.json의 구 구조/구 키를 신 구조로 자동 변환.
    목표:
      - store[boss]["profiles"] 리스트 안의 각 profile이 최소한
        ref_vec(dict) + ref_required_norm(float) 를 갖도록 보정
      - 과거 키: limit_norm -> ref_required_norm 로 매핑
      - 과거 구조: store[boss][party_type]["energy_limit"] 형태를 profiles로 승격(가능하면)
    """
    if not isinstance(store, dict):
        return {}

    for boss, boss_pack in list(store.items()):
        if not isinstance(boss_pack, dict):
            continue

        # 1) 이미 profiles 구조면: profile 키 보정
        if isinstance(boss_pack.get("profiles", None), list):
            profs = boss_pack.get("profiles", [])
            new_profs = []
            for p in profs:
                if not isinstance(p, dict):
                    continue

                # (a) ref_vec 보정
                ref_vec = p.get("ref_vec", None)
                if not isinstance(ref_vec, dict):
                    # 구버전에서 없었을 수 있으니 빈 dict로 둠(이 경우 clear_judge에서 무효 처리됨)
                    p["ref_vec"] = {}  

                # (b) limit_norm -> ref_required_norm
                if p.get("ref_required_norm", None) is None:
                    if p.get("limit_norm", None) is not None:
                        try:
                            p["ref_required_norm"] = float(p["limit_norm"])
                        except Exception:
                            pass

                # (c) 혹시 energy_limit만 있는 구버전 profiles가 남아있다면:
                #     지금 너의 로직은 ref_required_norm을 요구하므로, energy_limit은 참고용으로만 남김
                #     (여기서 변환은 불가능: boss_hp 정보가 없으면 boss_hp/P 한계로 못 바꿈)
                #     -> 그대로 두되 ref_required_norm이 없으면 무효로 남는다.

                new_profs.append(p)

            boss_pack["profiles"] = new_profs
            store[boss] = boss_pack
            continue

        # 2) profiles가 없는 "아주 구 구조" (예: store[boss][party_type] = {...}) 를 profiles로 승격
        #    단, 여기서도 ref_required_norm을 만들려면 limit_norm이 있어야 함.
        #    energy_limit만 있으면 변환 불가(위와 동일 이유).
        new_profiles = []
        for k, v in list(boss_pack.items()):
            if k == "profiles":
                continue
            if not isinstance(v, dict):
                continue

            # party_type별 dict에서 limit_norm이 있으면 ref_required_norm으로 승격
            if v.get("limit_norm", None) is not None:
                try:
                    new_profiles.append({
                        "label": str(k),
                        "ref_party": v.get("ref_party", ""),
                        "ref_vec": v.get("ref_vec", {}) if isinstance(v.get("ref_vec", {}), dict) else {},
                        "ref_required_norm": float(v["limit_norm"]),
                        "threshold_cycles": v.get("threshold_cycles", None),
                    })
                except Exception:
                    pass
            # energy_limit만 있는 케이스는 그대로 두거나 버릴지 선택인데,
            # 여기서는 "그대로 두면 혼선"이라 profiles로는 올리지 않음.

        if new_profiles:
            store[boss] = {"profiles": new_profiles}

    return store


def load_limits(path: str = DEFAULT_PATH) -> Dict[str, Any]:
    _ensure_session()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f) or {}
                raw = _migrate_limits_store(raw)  # ✅ 마이그레이션
                st.session_state["BOSS_LIMITS"] = raw
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
    # 저장 직전에도 한 번 정리(선택이지만 안전)
    store = _migrate_limits_store(store)

    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, path)


def get_limits_store(path: str = DEFAULT_PATH) -> Dict[str, Any]:
    if "BOSS_LIMITS" not in st.session_state:
        load_limits(path)
    return st.session_state["BOSS_LIMITS"]
