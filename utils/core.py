# utils/core.py
# 로그인/DB 없이, 브라우저 세션 안에서만 동작하는 버전.
# (제출/데모용 — 새로고침하거나 다른 사람이 열면 데이터는 초기화됩니다)
import time
import random
import streamlit as st
from utils.config import ASSET_CONFIG, ASSET_BASE_PRICE, STARTING_CASH


def format_korean_money(num):
    try:
        if num is None or num != num or num == 0:
            return "0원"
    except TypeError:
        return "0원"
    is_neg = num < 0
    num = abs(int(num))
    jo, eok, man, won = num // 10**12, (num % 10**12) // 10**8, (num % 10**8) // 10**4, num % 10**4
    parts = []
    if jo > 0: parts.append(f"{jo:,}조")
    if eok > 0: parts.append(f"{eok:,}억")
    if man > 0: parts.append(f"{man:,}만")
    if won > 0 or not parts: parts.append(f"{won:,}")
    res = " ".join(parts) + "원"
    return f"-{res}" if is_neg else res


# ── 세션 유저 (로그인 없음, 세션당 1명) ──────────────────────────────────────
def get_user():
    if "user" not in st.session_state:
        st.session_state.user = {
            "cash": STARTING_CASH,
            "portfolio": {},   # {asset_id: {"qty": int, "avg_price": float}}
            "savings": [],
            "tx_log": [],      # [{kind, ...}, ...]
        }
    return st.session_state.user


def log_tx(tx: dict):
    user = get_user()
    tx = {**tx, "ts": time.time()}
    user["tx_log"].insert(0, tx)
    user["tx_log"] = user["tx_log"][:200]


# ── 시세 (세션 안에서 랜덤워크 시뮬레이션) ───────────────────────────────────
def get_market():
    if "market" not in st.session_state:
        st.session_state.market = {
            "prices": {a["id"]: ASSET_BASE_PRICE[a["id"]] for a in ASSET_CONFIG},
            "history": {a["id"]: [ASSET_BASE_PRICE[a["id"]]] for a in ASSET_CONFIG},
            "last_tick": time.time(),
        }
    return st.session_state.market


def tick_market(min_interval_sec=15):
    m = get_market()
    if time.time() - m.get("last_tick", 0) < min_interval_sec:
        return m
    for a in ASSET_CONFIG:
        aid, vol = a["id"], a["vol"]
        p = m["prices"][aid]
        change = random.gauss(0, vol)
        new_p = max(100, p * (1 + change))
        m["prices"][aid] = round(new_p, 1)
        m["history"].setdefault(aid, []).append(round(new_p, 1))
        m["history"][aid] = m["history"][aid][-60:]
    m["last_tick"] = time.time()
    return m


def get_net_worth(user, market):
    w = user.get("cash", 0)
    for aid, pos in user.get("portfolio", {}).items():
        w += pos.get("qty", 0) * market["prices"].get(aid, 0)
    for s in user.get("savings", []):
        w += s.get("amount", 0)
    return w
