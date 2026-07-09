# utils/core.py
# 이름+출생연도를 키로 하는 단순 지속성 버전 (비밀번호 없음, DB에 저장)
import time
import random
import streamlit as st
from utils.config import (
    ASSET_CONFIG, ASSET_BASE_PRICE, STARTING_CASH, NEWS_TEMPLATES, BADGES, LEVEL_XP_TABLE,
)
from utils.database import load_doc, save_doc, db_available


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


# ── 유저 (이름+출생연도 키, DB 연결 시 지속됨 / 미연결 시 세션에만 유지) ─────────
def default_user():
    return {
        "cash": STARTING_CASH,
        "portfolio": {},        # {asset_id: {"qty": int, "avg_price": float}}
        "savings": [],
        "tx_log": [],           # [{kind, ...}, ...]
        "xp": 0,
        "badges": [],           # [badge_id, ...]
        "goal": None,           # {"name":..., "target":..., "created":...}
        "risk_profile": None,   # AI 온보딩 진단 결과
        "nw_history": [],       # [{"ts":..., "value":...}] 순자산 추이
    }


def get_user(uid: str):
    if "user" not in st.session_state:
        loaded = load_doc("users", uid, None)
        st.session_state.user = loaded if loaded else default_user()
    return st.session_state.user


def save_user(uid: str, user: dict):
    if db_available():
        save_doc("users", uid, user)


def log_tx(user: dict, tx: dict):
    tx = {**tx, "ts": time.time()}
    user["tx_log"].insert(0, tx)
    user["tx_log"] = user["tx_log"][:200]


# ── XP / 레벨 / 뱃지 (확률 없는 100% 확정 지급형 성취 시스템) ─────────────────
BADGE_BY_ID = {b["id"]: b for b in BADGES}


def award_badge(user, badge_id):
    """이미 획득한 뱃지면 무시, 처음이면 지급하고 새로 획득했는지 여부 반환."""
    if badge_id in user["badges"]:
        return False
    user["badges"].append(badge_id)
    user["xp"] += BADGE_BY_ID[badge_id]["xp"]
    return True


def get_level(xp):
    level = 1
    for i, threshold in enumerate(LEVEL_XP_TABLE):
        if xp >= threshold:
            level = i + 1
    return level


def xp_progress(xp):
    level = get_level(xp)
    idx = level - 1
    cur_floor = LEVEL_XP_TABLE[idx] if idx < len(LEVEL_XP_TABLE) else LEVEL_XP_TABLE[-1]
    next_ceil = LEVEL_XP_TABLE[idx + 1] if idx + 1 < len(LEVEL_XP_TABLE) else cur_floor + 500
    pct = min(1.0, (xp - cur_floor) / max(1, next_ceil - cur_floor))
    return level, pct, next_ceil


def check_habit_badges(user):
    """지출 기록 수, 보유 자산군 다양성 등 조건을 매번 점검해 새 뱃지가 있으면 지급."""
    newly = []
    n_expense = len([t for t in user["tx_log"] if t.get("kind") == "expense"])
    if n_expense >= 1 and award_badge(user, "first_record"):
        newly.append("first_record")
    if n_expense >= 10 and award_badge(user, "record_10"):
        newly.append("record_10")

    n_invest = len([t for t in user["tx_log"] if t.get("kind") == "invest_buy"])
    if n_invest >= 1 and award_badge(user, "first_invest"):
        newly.append("first_invest")

    types_held = {ASSET_BY_ID_CACHE()[aid]["type"] for aid in user.get("portfolio", {}) if user["portfolio"][aid]["qty"] > 0}
    if len(types_held) >= 3 and award_badge(user, "diversified"):
        newly.append("diversified")

    if user.get("savings") and award_badge(user, "first_saving"):
        newly.append("first_saving")

    if user.get("goal") and award_badge(user, "goal_set"):
        newly.append("goal_set")

    return newly


def ASSET_BY_ID_CACHE():
    return {a["id"]: a for a in ASSET_CONFIG}


# ── 목표 저축 ────────────────────────────────────────────────────────────
def set_goal(user, name, target):
    user["goal"] = {"name": name, "target": target, "created": time.time()}


def goal_progress(user):
    g = user.get("goal")
    if not g:
        return None
    save_val = sum(s["amount"] for s in user.get("savings", []))
    pct = min(1.0, save_val / g["target"]) if g["target"] > 0 else 0
    return {"name": g["name"], "target": g["target"], "current": save_val, "pct": pct}


# ── 시세 (세션 안에서 랜덤워크+뉴스 이벤트 시뮬레이션) ────────────────────────
def get_market():
    if "market" not in st.session_state:
        st.session_state.market = {
            "prices": {a["id"]: ASSET_BASE_PRICE[a["id"]] for a in ASSET_CONFIG},
            "history": {a["id"]: [ASSET_BASE_PRICE[a["id"]]] for a in ASSET_CONFIG},
            "history_t": {a["id"]: [time.time()] for a in ASSET_CONFIG},
            "last_tick": time.time(),
            "news": [],
        }
    return st.session_state.market


def tick_market(min_interval_sec=15):
    m = get_market()
    if time.time() - m.get("last_tick", 0) < min_interval_sec:
        return m

    news_event = None
    if random.random() < 0.22:
        news_event = random.choice(NEWS_TEMPLATES)
        m["news"].insert(0, {"ts": time.time(), "text": news_event["text"],
                              "asset": news_event["asset"], "impact": news_event["impact"]})
        m["news"] = m["news"][:20]

    now = time.time()
    for a in ASSET_CONFIG:
        aid, vol = a["id"], a["vol"]
        p = m["prices"][aid]
        change = random.gauss(0, vol)
        if news_event and news_event["asset"] == aid:
            change += news_event["impact"]
        new_p = max(100, p * (1 + change))
        m["prices"][aid] = round(new_p, 1)
        m["history"].setdefault(aid, []).append(round(new_p, 1))
        m["history"][aid] = m["history"][aid][-100:]
        m.setdefault("history_t", {}).setdefault(aid, []).append(now)
        m["history_t"][aid] = m["history_t"][aid][-100:]
    m["last_tick"] = now
    return m


def get_net_worth(user, market):
    w = user.get("cash", 0)
    for aid, pos in user.get("portfolio", {}).items():
        w += pos.get("qty", 0) * market["prices"].get(aid, 0)
    for s in user.get("savings", []):
        w += s.get("amount", 0)
    return w


def record_net_worth_point(user, market):
    """탭을 열 때마다(과도하지 않게, 최소 간격 유지) 순자산 스냅샷을 기록해 추이 차트를 만든다."""
    hist = user["nw_history"]
    now = time.time()
    if hist and now - hist[-1]["ts"] < 10:
        return
    hist.append({"ts": now, "value": get_net_worth(user, market)})
    user["nw_history"] = hist[-200:]
