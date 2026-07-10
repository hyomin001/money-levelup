# utils/core.py
# 이름+출생연도를 키로 하는 단순 지속성 버전 (비밀번호 없음, DB 연결 시 저장, 미연결 시 세션에만 유지)
import time
import random
import uuid
from datetime import date, timedelta

import streamlit as st

from utils.config import (
    ASSET_CONFIG, ASSET_BASE_PRICE, STARTING_MOCK_CASH, STARTING_REAL_CASH,
    NEWS_TEMPLATES, BADGES, LEVEL_XP_TABLE, EXPENSE_CATEGORIES, ORDERBOOK_LEVELS, ORDERBOOK_TICK_RATIO,
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
        "real_cash": STARTING_REAL_CASH,   # 실제 자금 (가계부/예적금 전용)
        "mock_cash": STARTING_MOCK_CASH,   # 모의투자 전용 가상 시드머니
        "portfolio": {},        # {asset_id: {"qty": int, "avg_price": float}}  ※ 모의투자 전용
        "savings": [],          # [{id,name,icon,start,end,months,target_amount,rate,amount,created}, ...]  ※ 실제 자금
        "tx_log": [],           # [{id, kind, ...}, ...]
        "xp": 0,
        "badges": [],           # [badge_id, ...]
        "goal": None,           # {"name":..., "target":..., "created":..., "completed": bool}
        "completed_goals_count": 0,
        "risk_profile": None,   # AI 온보딩 진단 결과
        "ai_coach_count": 0,
        "nw_history": [],       # [{"ts":..., "value":...}] 순자산 추이 (실제+모의 합산, 게임 지표용)
    }


def get_user(uid: str):
    if "user" not in st.session_state:
        loaded = load_doc("users", uid, None)
        user = loaded if loaded else default_user()
        # ── 이전 버전 데이터 마이그레이션 ──
        # 구버전은 "cash" 하나로 실제자금/모의투자를 같이 썼음. 있으면 1회 분리한다.
        if "cash" in user:
            old_cash = user.pop("cash")
            user.setdefault("mock_cash", old_cash)   # 기존 잔액은 모의투자 쪽에 보존
            user.setdefault("real_cash", STARTING_REAL_CASH)
        # 새로 추가된 필드가 없으면 채워준다.
        for k, v in default_user().items():
            user.setdefault(k, v)
        st.session_state.user = user
    return st.session_state.user


def save_user(uid: str, user: dict) -> bool:
    if not db_available():
        return False
    return save_doc("users", uid, user)


def log_tx(user: dict, tx: dict):
    tx = {"id": uuid.uuid4().hex[:10], "ts": time.time(), **tx}
    user["tx_log"].insert(0, tx)
    user["tx_log"] = user["tx_log"][:300]
    return tx["id"]


def delete_tx(user: dict, tx_id: str):
    """가계부 기록 삭제. 지출/수입 기록이었다면 real_cash를 원래대로 되돌려준다."""
    tx = next((t for t in user["tx_log"] if t.get("id") == tx_id), None)
    if tx is None:
        return False
    if tx.get("kind") == "expense":
        user["real_cash"] = user.get("real_cash", 0) + tx.get("amount", 0)
    elif tx.get("kind") == "income":
        user["real_cash"] = user.get("real_cash", 0) - tx.get("amount", 0)
    user["tx_log"] = [t for t in user["tx_log"] if t.get("id") != tx_id]
    return True


def add_income(user: dict, category: str, amount: int, memo: str = ""):
    """실제 수입을 기록하고 real_cash를 늘린다."""
    user["real_cash"] = user.get("real_cash", 0) + amount
    return log_tx(user, {"kind": "income", "category": category, "amount": amount, "memo": memo})


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
    next_ceil = LEVEL_XP_TABLE[idx + 1] if idx + 1 < len(LEVEL_XP_TABLE) else cur_floor + 1200
    pct = min(1.0, (xp - cur_floor) / max(1, next_ceil - cur_floor))
    return level, pct, next_ceil


def ASSET_BY_ID_CACHE():
    return {a["id"]: a for a in ASSET_CONFIG}


def total_saving_amount(user):
    return sum(s.get("amount", 0) for s in user.get("savings", []))


def check_habit_badges(user, market):
    """모든 습관/성취 조건을 매번 점검해 새로 달성한 뱃지가 있으면 지급하고 id 목록을 반환."""
    newly = []

    tx = user["tx_log"]
    n_expense = len([t for t in tx if t.get("kind") == "expense"])
    if n_expense >= 1 and award_badge(user, "first_record"):
        newly.append("first_record")
    if n_expense >= 10 and award_badge(user, "record_10"):
        newly.append("record_10")
    if n_expense >= 30 and award_badge(user, "record_30"):
        newly.append("record_30")

    cats_used = {t["category"] for t in tx if t.get("kind") == "expense"}
    if len(cats_used) >= len(EXPENSE_CATEGORIES) and award_badge(user, "category_master"):
        newly.append("category_master")

    n_invest = len([t for t in tx if t.get("kind") == "invest_buy"])
    if n_invest >= 1 and award_badge(user, "first_invest"):
        newly.append("first_invest")

    n_trades = len([t for t in tx if t.get("kind") in ("invest_buy", "invest_sell")])
    if n_trades >= 10 and award_badge(user, "trade_10"):
        newly.append("trade_10")

    assets_by_id = ASSET_BY_ID_CACHE()
    held_ids = [aid for aid, pos in user.get("portfolio", {}).items() if pos.get("qty", 0) > 0]
    types_held = {assets_by_id[aid]["type"] for aid in held_ids if aid in assets_by_id}
    if len(types_held) >= 3 and award_badge(user, "diversified"):
        newly.append("diversified")
    if len(types_held) >= 5 and award_badge(user, "diversified_plus"):
        newly.append("diversified_plus")
    if len(held_ids) >= len(ASSET_CONFIG) and award_badge(user, "all_assets"):
        newly.append("all_assets")

    sell_txs = [t for t in tx if t.get("kind") == "invest_sell"]
    if any(t.get("pnl", 0) > 0 for t in sell_txs) and award_badge(user, "profit_take"):
        newly.append("profit_take")
    if any(t.get("pnl_pct", 0) >= 15 for t in sell_txs) and award_badge(user, "big_win"):
        newly.append("big_win")

    if user.get("savings") and award_badge(user, "first_saving"):
        newly.append("first_saving")
    if len(user.get("savings", [])) >= 3 and award_badge(user, "multi_saving"):
        newly.append("multi_saving")

    save_total = total_saving_amount(user)
    if save_total >= 1_000_000 and award_badge(user, "saving_1000"):
        newly.append("saving_1000")
    if save_total >= 5_000_000 and award_badge(user, "saving_5000"):
        newly.append("saving_5000")

    if user.get("goal") and award_badge(user, "goal_set"):
        newly.append("goal_set")
    if (user.get("goal") or {}).get("completed") and award_badge(user, "goal_reached"):
        newly.append("goal_reached")
    if user.get("completed_goals_count", 0) >= 3 and award_badge(user, "goal_reached_x3"):
        newly.append("goal_reached_x3")

    if user.get("ai_coach_count", 0) >= 1 and award_badge(user, "ai_first"):
        newly.append("ai_first")
    if user.get("ai_coach_count", 0) >= 5 and award_badge(user, "ai_veteran"):
        newly.append("ai_veteran")

    if user.get("risk_profile") and award_badge(user, "risk_profile_done"):
        newly.append("risk_profile_done")

    level = get_level(user["xp"])
    if level >= 5 and award_badge(user, "level_5"):
        newly.append("level_5")
    if level >= 10 and award_badge(user, "level_10"):
        newly.append("level_10")

    nw = get_net_worth(user, market)
    if nw >= 5_000_000 and award_badge(user, "net_worth_500"):
        newly.append("net_worth_500")
    if nw >= 10_000_000 and award_badge(user, "net_worth_1000"):
        newly.append("net_worth_1000")
    if nw >= 30_000_000 and award_badge(user, "net_worth_3000"):
        newly.append("net_worth_3000")

    return newly


# ── 목표 저축 (하나의 대표 목표를 저축 총액 기준으로 추적) ─────────────────────
def set_goal(user, name, target):
    user["goal"] = {"name": name, "target": target, "created": time.time(), "completed": False}


def goal_progress(user):
    g = user.get("goal")
    if not g:
        return None
    save_val = total_saving_amount(user)
    pct = min(1.0, save_val / g["target"]) if g["target"] > 0 else 0
    if pct >= 1.0 and not g.get("completed"):
        g["completed"] = True
        user["completed_goals_count"] = user.get("completed_goals_count", 0) + 1
    return {"name": g["name"], "target": g["target"], "current": save_val,
            "pct": pct, "completed": g.get("completed", False)}


# ── 예/적금 (이름·기간·목표금액을 자유롭게 입력해 나만의 상품을 생성) ────────────
def create_saving(name, start_date_str, months, target_amount, rate, initial_amount, icon="🏦"):
    start = date.fromisoformat(start_date_str)
    end = (start + timedelta(days=months * 30)).isoformat() if months and months > 0 else None
    return {
        "id": uuid.uuid4().hex[:10],
        "name": name,
        "icon": icon,
        "start": start_date_str,
        "end": end,
        "months": months or 0,
        "target_amount": int(target_amount or 0),
        "rate": float(rate or 0),
        "amount": int(initial_amount or 0),
        "created": time.time(),
    }


def saving_progress(s):
    """기간 진행률(time_pct)과 금액 진행률(amount_pct)을 각각 계산 — 없으면 None."""
    today = date.today()
    try:
        start = date.fromisoformat(s["start"])
    except Exception:
        start = today

    time_pct, days_left, matured = None, None, False
    if s.get("end"):
        try:
            end = date.fromisoformat(s["end"])
            total_days = max(1, (end - start).days)
            elapsed = (today - start).days
            time_pct = min(1.0, max(0.0, elapsed / total_days))
            days_left = max(0, (end - today).days)
            matured = today >= end
        except Exception:
            pass

    amount_pct = None
    if s.get("target_amount"):
        amount_pct = min(1.0, s.get("amount", 0) / s["target_amount"]) if s["target_amount"] > 0 else 0.0

    return {"time_pct": time_pct, "amount_pct": amount_pct, "days_left": days_left, "matured": matured}


# ── 시세 (세션 안에서 랜덤워크+뉴스 이벤트 시뮬레이션) + 모의 호가창 ────────────
def get_market():
    if "market" not in st.session_state:
        st.session_state.market = {
            "prices": {a["id"]: ASSET_BASE_PRICE[a["id"]] for a in ASSET_CONFIG},
            "history": {a["id"]: [ASSET_BASE_PRICE[a["id"]]] for a in ASSET_CONFIG},
            "history_t": {a["id"]: [time.time()] for a in ASSET_CONFIG},
            "orderbook": {},
            "last_tick": 0,
            "news": [],
        }
        _refresh_orderbooks(st.session_state.market)
    return st.session_state.market


def _refresh_orderbooks(m):
    for a in ASSET_CONFIG:
        m["orderbook"][a["id"]] = generate_orderbook(m["prices"][a["id"]])


def generate_orderbook(price):
    """현재가 주변에 매수(bid)/매도(ask) 각 N호가를 랜덤 잔량으로 생성 (실시세 연동 아님)."""
    tick = max(1, round(price * ORDERBOOK_TICK_RATIO / 10) * 10)
    asks = [{"price": round(price + tick * i), "qty": random.randint(5, 320)}
            for i in range(ORDERBOOK_LEVELS, 0, -1)]
    bids = [{"price": max(1, round(price - tick * i)), "qty": random.randint(5, 320)}
            for i in range(1, ORDERBOOK_LEVELS + 1)]
    max_qty = max([o["qty"] for o in asks + bids] + [1])
    return {"asks": asks, "bids": bids, "max_qty": max_qty, "ts": time.time()}


def tick_market(min_interval_sec=15):
    m = get_market()
    if time.time() - m.get("last_tick", 0) < min_interval_sec:
        return m

    news_event = None
    if random.random() < 0.22:
        news_event = random.choice(NEWS_TEMPLATES)
        m["news"].insert(0, {"ts": time.time(), "text": news_event["text"],
                              "asset": news_event["asset"], "impact": news_event["impact"]})
        m["news"] = m["news"][:30]

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
    _refresh_orderbooks(m)
    m["last_tick"] = now
    return m


def real_net_worth(user):
    """실제로 관리하는 돈 (실제 지갑 + 저축 총액). 모의투자는 포함하지 않는다."""
    return user.get("real_cash", 0) + total_saving_amount(user)


def mock_portfolio_value(user, market):
    """모의투자 보유 종목의 현재 평가액 합계 (현금 제외)."""
    return sum(pos.get("qty", 0) * market["prices"].get(aid, 0) for aid, pos in user.get("portfolio", {}).items())


def mock_total_value(user, market):
    """모의투자 계좌 총액 (모의 현금 + 평가액). 연습용이며 실제 자산이 아니다."""
    return user.get("mock_cash", 0) + mock_portfolio_value(user, market)


def get_net_worth(user, market):
    """게임 지표(뱃지/레벨)용 종합 점수 — 실제 자금 + 모의투자를 합산. 대시보드 표시는 반드시 분리해서 보여줄 것."""
    return real_net_worth(user) + mock_total_value(user, market)


def record_net_worth_point(user, market):
    """탭을 열 때마다(과도하지 않게, 최소 간격 유지) 순자산 스냅샷을 기록해 추이 차트를 만든다."""
    hist = user["nw_history"]
    now = time.time()
    if hist and now - hist[-1]["ts"] < 10:
        return
    hist.append({"ts": now, "value": get_net_worth(user, market),
                 "real": real_net_worth(user), "mock": mock_total_value(user, market)})
    user["nw_history"] = hist[-200:]
