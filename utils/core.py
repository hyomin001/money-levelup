# utils/core.py
# 이름+출생연도를 키로 하는 단순 지속성 버전 (비밀번호 없음, DB 연결 시 저장, 미연결 시 세션에만 유지)
import time
import random
import uuid
import hashlib
from datetime import date, timedelta

import streamlit as st

from utils.config import (
    ASSET_CONFIG, ASSET_BASE_PRICE, STARTING_MOCK_CASH, STARTING_REAL_CASH,
    NEWS_TEMPLATES, BADGES, LEVEL_XP_TABLE, EXPENSE_CATEGORIES, ORDERBOOK_LEVELS, ORDERBOOK_TICK_RATIO,
    SCAM_SCENARIOS, LEVERAGE_SEED, LEVERAGE_SIM_DAYS, LEVERAGE_MAINTENANCE_RATIO,
    CRISIS_SCENARIOS, CRISIS_DECISION_CHOICES,
    IMPULSE_THRESHOLD, IMPULSE_COOLDOWN_HOURS, MONEY_SHADOW_ITEMS,
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
def default_user(initial_real_cash: int = None, initial_savings: int = 0):
    """initial_real_cash: 온보딩(시작하기)에서 사용자가 직접 입력한 '현재 이미 가진 돈'.
    None이면 기존 기본값(STARTING_REAL_CASH)을 사용한다."""
    real_cash = STARTING_REAL_CASH if initial_real_cash is None else int(initial_real_cash)
    user = {
        "real_cash": real_cash,            # 실제 자금 (가계부/예적금 전용)
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
        "chat_history": [],     # [{"role": "user"|"coach", "text": ...}, ...]  ※ AI 상담 챗봇 전용
        "risk_lab": {           # 🚨 리스크 체험관 (실제/모의 자금과 완전히 분리된 학습 전용 기록)
            "scam_scores": {},           # {scenario_id: 획득 점수(0/5/10 등)}
            "leverage_trials": 0,        # 레버리지 시뮬레이터 실행 횟수
            "leverage_liquidations": 0,  # 청산(강제 로스컷) 경험 횟수
            "leverage_survive_5x": 0,    # 5배 이상에서 청산 없이 생존한 연속 횟수
            "crisis_completed": {},      # {scenario_id: {"final_value":..., "baseline_value":..., "decisions":[...]}}
        },
        "guide_seen": False,    # 📖 첫 방문 이용 가이드를 이미 봤는지 여부
        "pin_hash": None,       # 🔐 4자리 PIN 해시 (동명이인+동일 출생연도 계정 충돌 방지용)
        "created_at": time.time(),   # 🔥 무지출 스트릭 캘린더 시작 기준일
        "pending_impulses": [], # ⏸️ 충동구매 쿨다운 대기 목록 [{id, category, amount, memo, created_ts, unlock_ts}]
        "impulse_cancel_count": 0,   # ⏸️ 쿨다운 중 '포기하기'를 선택한 누적 횟수
    }
    if initial_real_cash:
        log_tx(user, {"kind": "income", "category": "etc_in", "amount": int(initial_real_cash),
                       "memo": "초기 보유 자금 설정", "is_setup": True})
    if initial_savings:
        s = create_saving("초기 보유 저축", date.today().isoformat(), 0, 0, 0.0, initial_savings, icon="💼")
        user["savings"].append(s)
        log_tx(user, {"kind": "savings_open", "name": s["name"], "amount": initial_savings,
                       "memo": "초기 보유 저축/예적금 설정"})
    return user


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(f"ml-pin::{pin}".encode()).hexdigest()


def verify_pin(uid: str, pin: str):
    """로그인 시 PIN 검증. 이름+출생연도만으로는 동명이인이 서로의 데이터를 볼 수 있어서
    4자리 PIN으로 한 겹 더 확인한다.
    반환: (통과 여부, 에러 메시지 또는 None)
    - 해당 uid로 저장된 기록이 아직 없으면(신규 유저) 통과 — 이번에 입력한 PIN이 앞으로의 PIN이 됨.
    - 기록은 있는데 PIN이 설정된 적 없으면(이 기능 추가 이전 데이터) 통과 — 이번 PIN으로 새로 설정됨.
    - 기록에 PIN이 있으면 반드시 일치해야 통과.
    """
    existing = load_doc("users", uid, None)
    if not existing:
        return True, None
    stored = existing.get("pin_hash")
    if not stored:
        return True, None
    if stored == _hash_pin(pin):
        return True, None
    return False, "PIN이 일치하지 않아요. 이름·출생연도·PIN을 다시 확인해주세요."


def get_user(uid: str, initial_real_cash: int = None, initial_savings: int = 0, pin: str = None):
    if "user" not in st.session_state:
        loaded = load_doc("users", uid, None)
        is_new = loaded is None
        user = loaded if loaded else default_user(initial_real_cash, initial_savings)
        # ── 이전 버전 데이터 마이그레이션 ──
        # 구버전은 "cash" 하나로 실제자금/모의투자를 같이 썼음. 있으면 1회 분리한다.
        if "cash" in user:
            old_cash = user.pop("cash")
            user.setdefault("mock_cash", old_cash)   # 기존 잔액은 모의투자 쪽에 보존
            user.setdefault("real_cash", STARTING_REAL_CASH)
        # 새로 추가된 필드가 없으면 채워준다.
        for k, v in default_user().items():
            user.setdefault(k, v)
        # PIN이 아직 설정 안 되어 있으면(신규 유저 또는 이 기능 추가 이전 데이터) 이번 PIN으로 설정
        if pin and not user.get("pin_hash"):
            user["pin_hash"] = _hash_pin(pin)
        st.session_state.user = user
        st.session_state["_is_new_user"] = is_new
    return st.session_state.user


def adjust_balance(user: dict, new_amount: int, memo: str = "잔액 직접 수정"):
    """지갑 잔액을 사용자가 원하는 값으로 직접 맞춘다 (차액만큼 조정 내역을 기록)."""
    diff = int(new_amount) - user.get("real_cash", 0)
    if diff == 0:
        return 0
    user["real_cash"] = int(new_amount)
    log_tx(user, {"kind": "income" if diff > 0 else "expense",
                   "category": "etc_in" if diff > 0 else "etc",
                   "amount": abs(diff), "memo": memo, "is_adjustment": True})
    return diff


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
        _seed_initial_news(st.session_state.market)
    return st.session_state.market


def _seed_initial_news(m, count=4):
    """market은 세션마다 새로 만들어지고, 뉴스는 원래 tick_market()에서 10초마다 22% 확률로만
    생성됐다. 그래서 접속 직후에는 몇 분씩 '뉴스 수신 대기 중' 상태로 비어 보이는 문제가 있었다.
    첫 화면부터 자연스럽게 뉴스가 보이도록 시작 시점에 몇 건을 미리 채워둔다."""
    sample = random.sample(NEWS_TEMPLATES, k=min(count, len(NEWS_TEMPLATES)))
    now = time.time()
    for i, news_event in enumerate(sample):
        # 최근 것부터 최대 몇 분 전 발생한 것처럼 타임스탬프를 살짝 과거로 흩어준다.
        m["news"].append({"ts": now - i * 47, "text": news_event["text"],
                           "asset": news_event["asset"], "impact": news_event["impact"]})


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


def tick_market(min_interval_sec=10):
    """10초마다 한 번씩 시세를 갱신한다.
    뉴스와 가격 반영을 한 틱에 동시에 처리하면 '뉴스가 뜨자마자 이미 가격에 반영되어 있는'
    부자연스러운 상태가 되어, 평가자 입장에서 뉴스와 시세가 서로 무관하게 보일 수 있다.
    그래서 이번 틱에서 새로 뜬 뉴스는 화면에만 먼저 노출하고, 그 뉴스의 가격 영향(impact)은
    다음 틱(pending_impact)으로 예약해두었다가 그 다음 시세 갱신에 반영한다.
    즉: [뉴스 발생 → 그 다음 시세 갱신에 뉴스가 영향] 순서가 명확히 드러난다."""
    m = get_market()
    if time.time() - m.get("last_tick", 0) < min_interval_sec:
        return m

    now = time.time()

    # 1) 이전 틱에서 예약해둔 뉴스 효과를 이번 가격 변동에 반영
    pending = m.pop("pending_impact", None)

    # 2) 새 뉴스 이벤트 발생 여부 판단 → 화면에는 바로 노출하되, 가격 반영은 다음 틱으로 예약
    news_event = None
    if random.random() < 0.22:
        news_event = random.choice(NEWS_TEMPLATES)
        m["news"].insert(0, {"ts": now, "text": news_event["text"],
                              "asset": news_event["asset"], "impact": news_event["impact"]})
        m["news"] = m["news"][:30]
        m["pending_impact"] = {"asset": news_event["asset"], "impact": news_event["impact"]}

    for a in ASSET_CONFIG:
        aid, vol = a["id"], a["vol"]
        p = m["prices"][aid]
        change = random.gauss(0, vol)
        if pending and pending["asset"] == aid:
            change += pending["impact"]
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


# ── 재무 건강 점수 (규칙 기반 · 설명 가능한 100점 만점 점수) ──────────────────
# 판정 근거를 그대로 노출하는 투명한 알고리즘으로, AI 코치의 정성적 진단을 정량 지표로 보완한다.
def financial_health_score(user, market):
    tx = user.get("tx_log", [])
    now = time.time()
    month_ago = now - 30 * 24 * 3600
    three_months_ago = now - 90 * 24 * 3600

    income_recent = sum(t["amount"] for t in tx if t.get("kind") == "income" and t.get("ts", 0) >= three_months_ago
                         and not t.get("is_setup") and not t.get("is_adjustment"))
    expense_recent = sum(t["amount"] for t in tx if t.get("kind") == "expense" and t.get("ts", 0) >= three_months_ago)
    month_expense = sum(t["amount"] for t in tx if t.get("kind") == "expense" and t.get("ts", 0) >= month_ago)

    savings_total = total_saving_amount(user)
    real_cash = user.get("real_cash", 0)
    breakdown = []

    # 1) 저축률 (최근 3개월 수입 대비 저축 비중, 최대 30점)
    if income_recent > 0:
        save_rate = min(1.5, savings_total / income_recent)
        pts = round(min(30, save_rate / 0.3 * 30))
    else:
        pts = 10 if savings_total > 0 else 0
    breakdown.append({"key": "저축 습관", "points": pts, "max": 30,
                       "detail": f"최근 3개월 수입 대비 저축 비중 기준 (누적 저축 {format_korean_money(savings_total)})"})

    # 2) 비상금 커버리지 (월 지출 대비 실제 현금 보유, 최대 25점)
    if month_expense > 0:
        months_covered = real_cash / month_expense
        pts = round(min(25, months_covered / 3 * 25))
    else:
        pts = 15 if real_cash > 0 else 5
    breakdown.append({"key": "비상금 여력", "points": pts, "max": 25,
                       "detail": "생활비 3개월치 이상의 현금 보유를 만점 기준으로 계산"})

    # 3) 투자 분산도 (보유 자산군 종류 수, 최대 20점)
    assets_by_id = ASSET_BY_ID_CACHE()
    held_ids = [aid for aid, pos in user.get("portfolio", {}).items() if pos.get("qty", 0) > 0]
    types_held = {assets_by_id[aid]["type"] for aid in held_ids if aid in assets_by_id}
    pts = round(min(20, len(types_held) / 4 * 20))
    breakdown.append({"key": "분산 투자", "points": pts, "max": 20,
                       "detail": f"서로 다른 자산군 {len(types_held)}개 보유 (4개 이상이면 만점)"})

    # 4) 소비 통제력 (최근 3개월 지출이 수입을 넘지 않았는지, 최대 15점)
    if income_recent > 0:
        ratio = expense_recent / income_recent
        pts = 15 if ratio <= 0.7 else round(max(0, 15 * (1.3 - ratio) / 0.6))
    else:
        pts = 8
    breakdown.append({"key": "소비 통제", "points": pts, "max": 15,
                       "detail": "최근 3개월 지출/수입 비율 기준"})

    # 5) 목표 설정 및 진행 (최대 10점)
    g = goal_progress(user)
    if g:
        pts = round(5 + 5 * g["pct"])
    else:
        pts = 0
    breakdown.append({"key": "목표 관리", "points": pts, "max": 10,
                       "detail": "목표저축 설정 여부와 달성률 기준"})

    score = sum(b["points"] for b in breakdown)
    if score >= 85:
        grade, comment = "S", "탄탄한 재무 체력을 갖추고 있어요."
    elif score >= 70:
        grade, comment = "A", "좋은 습관이 자리 잡고 있어요."
    elif score >= 50:
        grade, comment = "B", "기본기는 있지만 보완할 부분이 있어요."
    elif score >= 30:
        grade, comment = "C", "몇 가지 습관만 바꾸면 크게 좋아질 수 있어요."
    else:
        grade, comment = "D", "지금부터 하나씩 만들어가면 돼요."

    return {"score": score, "grade": grade, "comment": comment, "breakdown": breakdown}


# ── 다음 달 지출 예측 (최근 3개월 가계부 기록 기반 추세 예측, 회귀 없이도 안정적으로 동작) ──
def predict_next_month_expense(user):
    tx = [t for t in user.get("tx_log", []) if t.get("kind") == "expense"]
    if not tx:
        return None

    now = time.localtime()
    monthly = {}
    for t in tx:
        lt = time.localtime(t.get("ts", time.time()))
        key = (lt.tm_year, lt.tm_mon)
        monthly[key] = monthly.get(key, 0) + t["amount"]

    ordered_keys = sorted(monthly.keys())
    recent_keys = ordered_keys[-3:]
    recent_vals = [monthly[k] for k in recent_keys]
    if not recent_vals:
        return None

    if len(recent_vals) == 1:
        forecast = recent_vals[0]
        trend = 0.0
    else:
        # 최근 값에 가중치를 더 주는 단순 가중이동평균 + 최근 추세 반영
        weights = list(range(1, len(recent_vals) + 1))
        weighted_avg = sum(v * w for v, w in zip(recent_vals, weights)) / sum(weights)
        trend = (recent_vals[-1] - recent_vals[0]) / max(1, len(recent_vals) - 1)
        forecast = max(0, weighted_avg + trend * 0.5)

    # 카테고리별 최근 1개월 비중을 그대로 다음 달 예측에 적용
    month_ago = time.time() - 30 * 24 * 3600
    by_cat = {}
    for t in tx:
        if t.get("ts", 0) >= month_ago:
            by_cat[t["category"]] = by_cat.get(t["category"], 0) + t["amount"]
    cat_total = sum(by_cat.values()) or 1
    forecast_by_cat = {cat: forecast * (amt / cat_total) for cat, amt in by_cat.items()}

    is_anomaly_month = False
    if len(recent_vals) >= 2:
        avg_prev = sum(recent_vals[:-1]) / len(recent_vals[:-1])
        is_anomaly_month = avg_prev > 0 and recent_vals[-1] >= avg_prev * 1.3

    return {
        "forecast": round(forecast),
        "trend": trend,
        "history": list(zip([f"{y}-{m:02d}" for y, m in recent_keys], recent_vals)),
        "forecast_by_category": forecast_by_cat,
        "anomaly": is_anomaly_month,
    }


# ── 사회초년생용 50/30/20 예산 자동분석 ──────────────────────────────────────
# 고정비(니즈): 주거/공과금·교통·의료/건강·구독멤버십 / 변동비(원츠): 식비·카페·쇼핑·여가·기타
NEEDS_CATEGORIES = {"living", "transport", "health", "sub"}
BUDGET_TARGET = {"needs": 0.50, "wants": 0.30, "savings": 0.20}


def analyze_budget_50_30_20(user: dict):
    """이번 달(최근 30일) 지출을 고정비/변동비로 나누고, 이번 달 수입 대비 저축률을 계산한다."""
    tx = user.get("tx_log", [])
    month_ago = time.time() - 30 * 24 * 3600
    recent = [t for t in tx if t.get("ts", 0) >= month_ago]

    income = sum(t["amount"] for t in recent if t.get("kind") == "income")
    expenses = [t for t in recent if t.get("kind") == "expense"]
    needs_amt = sum(t["amount"] for t in expenses if t.get("category") in NEEDS_CATEGORIES)
    wants_amt = sum(t["amount"] for t in expenses if t.get("category") not in NEEDS_CATEGORIES)
    total_exp = needs_amt + wants_amt

    if income > 0:
        base = income
        savings_amt = max(0, income - total_exp)
    else:
        # 이번 달 수입 기록이 없으면 지출 총액을 기준(100%)으로 needs/wants 비중만 보여준다
        base = total_exp
        savings_amt = 0

    def pct(x):
        return (x / base) if base > 0 else 0.0

    return {
        "has_income": income > 0,
        "income": income,
        "needs_amt": needs_amt, "wants_amt": wants_amt, "savings_amt": savings_amt,
        "needs_ratio": pct(needs_amt), "wants_ratio": pct(wants_amt), "savings_ratio": pct(savings_amt),
        "target": BUDGET_TARGET,
    }


# ── 구독료(반복 결제) 자동 감지 ───────────────────────────────────────────────
def detect_recurring_subscriptions(user: dict):
    """'구독/멤버십' 카테고리 지출을 메모 기준으로 묶어, 두 달 이상 반복되면 '확정 구독'으로 표시한다."""
    tx = [t for t in user.get("tx_log", []) if t.get("kind") == "expense" and t.get("category") == "sub"]
    groups = {}
    for t in tx:
        key = (t.get("memo") or "").strip().lower() or "미분류 구독"
        g = groups.setdefault(key, {"label": (t.get("memo") or "미분류 구독").strip() or "미분류 구독",
                                     "months": set(), "amounts": [], "last_ts": 0, "last_amount": 0})
        lt = time.localtime(t.get("ts", time.time()))
        g["months"].add((lt.tm_year, lt.tm_mon))
        g["amounts"].append(t["amount"])
        if t.get("ts", 0) >= g["last_ts"]:
            g["last_ts"] = t.get("ts", 0)
            g["last_amount"] = t["amount"]

    confirmed, candidates = [], []
    for g in groups.values():
        item = {"label": g["label"], "monthly_cost": g["last_amount"],
                 "months_seen": len(g["months"]), "total_seen": sum(g["amounts"])}
        (confirmed if len(g["months"]) >= 2 else candidates).append(item)

    confirmed.sort(key=lambda x: -x["monthly_cost"])
    candidates.sort(key=lambda x: -x["monthly_cost"])
    monthly_total = sum(c["monthly_cost"] for c in confirmed)
    return {"confirmed": confirmed, "candidates": candidates, "monthly_total": monthly_total}


# ══════════════════════════════════════════════════════════════════════════
# 🔥 무지출 스트릭 캘린더 — 지출 없이 지나간 날을 GitHub 잔디밭처럼 시각화
# ══════════════════════════════════════════════════════════════════════════
def no_spend_streak_calendar(user: dict, weeks: int = 12):
    """최근 weeks*7일 구간의 일별 '무지출 여부'를 계산해 스트릭 통계와 함께 반환한다."""
    today = date.fromtimestamp(time.time())
    window_days = weeks * 7
    account_start = date.fromtimestamp(user.get("created_at", time.time()))
    range_start = max(account_start, today - timedelta(days=window_days - 1))

    # 실제 소비 행위로 인정하는 지출만 집계 (초기 설정/잔액 보정은 제외)
    spend_dates = set()
    for t in user.get("tx_log", []):
        if t.get("kind") == "expense" and not t.get("is_adjustment") and not t.get("is_setup"):
            spend_dates.add(date.fromtimestamp(t.get("ts", time.time())).isoformat())

    days = []
    d = range_start
    while d <= today:
        days.append({"date": d.isoformat(), "weekday": d.weekday(), "no_spend": d.isoformat() not in spend_dates})
        d += timedelta(days=1)

    # 오늘부터 거꾸로 연속 무지출 일수 (계정 시작일 이전은 카운트하지 않음)
    current_streak = 0
    d = today
    while d >= range_start and d.isoformat() not in spend_dates:
        current_streak += 1
        d -= timedelta(days=1)

    longest_streak, run = 0, 0
    for day in days:
        run = run + 1 if day["no_spend"] else 0
        longest_streak = max(longest_streak, run)

    this_month = today.month
    no_spend_this_month = sum(1 for day in days
                               if day["no_spend"] and date.fromisoformat(day["date"]).month == this_month)

    return {
        "days": days, "range_start": range_start.isoformat(), "today": today.isoformat(),
        "current_streak": current_streak, "longest_streak": longest_streak,
        "no_spend_this_month": no_spend_this_month,
    }


def check_streak_badges(user: dict):
    """무지출 스트릭 길이에 따라 뱃지를 지급하고, 새로 획득한 뱃지 id 목록을 반환한다."""
    streak = no_spend_streak_calendar(user)["current_streak"]
    newly = []
    if streak >= 7 and award_badge(user, "no_spend_streak_7"):
        newly.append("no_spend_streak_7")
    if streak >= 14 and award_badge(user, "no_spend_streak_14"):
        newly.append("no_spend_streak_14")
    if streak >= 30 and award_badge(user, "no_spend_streak_30"):
        newly.append("no_spend_streak_30")
    return newly


# ══════════════════════════════════════════════════════════════════════════
# ⏸️ 충동구매 쿨다운 — 일정 금액 이상 지출은 즉시 기록하지 않고 대기시켜 재고할 시간을 준다
# (사용자는 언제든 '지금 바로 기록하기'로 대기를 건너뛸 수 있다 — 강제 차단이 아닌 넛지)
# ══════════════════════════════════════════════════════════════════════════
def create_pending_impulse(user: dict, category: str, amount: int, memo: str = ""):
    now = time.time()
    item = {
        "id": uuid.uuid4().hex[:10], "category": category, "amount": amount, "memo": memo,
        "created_ts": now, "unlock_ts": now + IMPULSE_COOLDOWN_HOURS * 3600,
    }
    user.setdefault("pending_impulses", []).append(item)
    return item["id"]


def pending_impulses_view(user: dict):
    """대기 목록을 최근 등록 순으로 반환하며, 각 항목에 남은 시간(초)과 준비 여부를 붙인다."""
    now = time.time()
    out = []
    for it in user.get("pending_impulses", []):
        remain = max(0, int(it["unlock_ts"] - now))
        out.append({**it, "remaining_seconds": remain, "ready": remain <= 0})
    return sorted(out, key=lambda x: -x["created_ts"])


def resolve_pending_impulse(user: dict, impulse_id: str, action: str):
    """action='confirm' → 실제로 지출 기록(잔액 차감), action='cancel' → 지출 포기(자제 카운트 증가).
    반환: 처리된 항목 dict 또는 None."""
    items = user.get("pending_impulses", [])
    it = next((x for x in items if x["id"] == impulse_id), None)
    if it is None:
        return None
    user["pending_impulses"] = [x for x in items if x["id"] != impulse_id]

    if action == "confirm":
        user["real_cash"] = user.get("real_cash", 0) - it["amount"]
        log_tx(user, {"kind": "expense", "category": it["category"], "amount": it["amount"],
                       "memo": it.get("memo", "")})
    elif action == "cancel":
        user["impulse_cancel_count"] = user.get("impulse_cancel_count", 0) + 1
    return it


def check_impulse_badges(user: dict):
    newly = []
    n = user.get("impulse_cancel_count", 0)
    if n >= 3 and award_badge(user, "impulse_resist_3"):
        newly.append("impulse_resist_3")
    if n >= 10 and award_badge(user, "impulse_resist_10"):
        newly.append("impulse_resist_10")
    return newly


# ══════════════════════════════════════════════════════════════════════════
# ☕ 돈 그림자 — 지출 금액을 익숙한 물가·목표저축 진행률로 환산해 체감시킨다
# ══════════════════════════════════════════════════════════════════════════
def money_shadow_comparisons(amount: int, user: dict = None, n: int = 2):
    if amount <= 0:
        return []
    picks = random.sample(MONEY_SHADOW_ITEMS, k=min(n, len(MONEY_SHADOW_ITEMS)))
    comparisons = []
    for item in picks:
        multiple = amount / item["price"]
        qty = f"{multiple:.1f}개" if multiple < 10 else f"{multiple:.0f}개"
        comparisons.append(f"{item['icon']} {item['name']} {qty}")

    if user is not None:
        g = user.get("goal")
        if g and not g.get("completed") and g.get("target", 0) > 0:
            pct = amount / g["target"] * 100
            comparisons.append(f"🎯 목표 '{g['name']}'의 {pct:.1f}%에 해당하는 금액이에요")

    return comparisons


# ══════════════════════════════════════════════════════════════════════════
# 🚨 리스크 체험관 로직 — 실제/모의 자금과 완전히 분리된 학습 전용 시뮬레이션
# ══════════════════════════════════════════════════════════════════════════
SCAM_BY_ID = {s["id"]: s for s in SCAM_SCENARIOS}
CRISIS_BY_ID = {c["id"]: c for c in CRISIS_SCENARIOS}
SCAM_MAX_SCORE = len(SCAM_SCENARIOS) * 10


def record_scam_answer(user, scenario_id: str, choice_index: int):
    """사용자의 선택을 기록하고, 이번 선택에 대한 피드백 dict를 반환한다 (최고 점수만 누적 반영)."""
    scenario = SCAM_BY_ID[scenario_id]
    choice = scenario["choices"][choice_index]
    rl = user["risk_lab"]
    prev = rl["scam_scores"].get(scenario_id, -1)
    if choice["score"] > prev:
        rl["scam_scores"][scenario_id] = choice["score"]
    return choice


def scam_lab_summary(user):
    rl = user["risk_lab"]
    total = sum(rl["scam_scores"].values())
    completed = len(rl["scam_scores"])
    if total >= SCAM_MAX_SCORE * 0.9:
        grade, comment = "사기 방어 마스터", "패턴을 정확히 꿰뚫고 있어요. 주변 사람에게도 알려주면 더 좋아요."
    elif total >= SCAM_MAX_SCORE * 0.65:
        grade, comment = "양호", "핵심은 잘 짚고 있지만, 몇 가지 유형은 한 번 더 복습해두면 좋아요."
    elif total >= SCAM_MAX_SCORE * 0.35:
        grade, comment = "주의 필요", "그럴듯한 말에 판단이 흔들릴 수 있어요. 원칙 위주로 다시 점검해봐요."
    else:
        grade, comment = "위험", "지금 패턴이라면 실제 상황에서 위험할 수 있어요. 시나리오를 다시 복습해보세요."
    return {"total": total, "max": SCAM_MAX_SCORE, "completed": completed,
            "n_scenarios": len(SCAM_SCENARIOS), "grade": grade, "comment": comment}


def run_leverage_simulation(asset_id: str, leverage: int):
    """자산의 변동성(vol)을 바탕으로 LEVERAGE_SIM_DAYS일간의 랜덤워크를 생성하고,
    레버리지 적용 시 계좌(가상 시드머니 LEVERAGE_SEED 기준)와 무레버리지(1배) 계좌를 나란히 비교한다.
    실제/모의 자금과 완전히 분리된 결과만 반환하며 user 데이터는 건드리지 않는다."""
    asset = ASSET_BY_ID_CACHE()[asset_id]
    vol = asset["vol"]
    daily_returns = [random.gauss(-0.0006, vol) for _ in range(LEVERAGE_SIM_DAYS)]

    equity_lev = [float(LEVERAGE_SEED)]
    equity_base = [float(LEVERAGE_SEED)]
    liquidated_day = None
    floor = LEVERAGE_SEED * LEVERAGE_MAINTENANCE_RATIO

    for day, r in enumerate(daily_returns, start=1):
        base_val = equity_base[-1] * (1 + r)
        equity_base.append(max(0.0, base_val))

        if liquidated_day is not None:
            equity_lev.append(0.0)
            continue
        lev_val = equity_lev[-1] * (1 + r * leverage)
        if lev_val <= floor:
            equity_lev.append(0.0)
            liquidated_day = day
        else:
            equity_lev.append(lev_val)

    return {
        "asset_name": asset["name"], "leverage": leverage,
        "equity_lev": equity_lev, "equity_base": equity_base,
        "liquidated": liquidated_day is not None, "liquidated_day": liquidated_day,
        "final_lev": equity_lev[-1], "final_base": equity_base[-1],
        "seed": LEVERAGE_SEED,
    }


def record_leverage_trial(user, result: dict):
    """레버리지 시뮬레이션 1회 실행 결과를 유저 기록에 반영한다 (뱃지/통계 목적)."""
    rl = user["risk_lab"]
    rl["leverage_trials"] = rl.get("leverage_trials", 0) + 1
    if result["liquidated"]:
        rl["leverage_liquidations"] = rl.get("leverage_liquidations", 0) + 1
        rl["leverage_survive_5x"] = 0
    elif result["leverage"] >= 5:
        rl["leverage_survive_5x"] = rl.get("leverage_survive_5x", 0) + 1


def _crisis_path(control_points):
    """제어점(day, index값) 목록을 선형보간해 하루 단위 지수 배열로 만들고,
    약간의 노이즈를 더해 자연스러운 일별 흐름을 만든다."""
    days = control_points[-1][0]
    path = []
    cp = control_points
    for d in range(days + 1):
        seg = next(i for i in range(len(cp) - 1) if cp[i][0] <= d <= cp[i + 1][0])
        d0, v0 = cp[seg]
        d1, v1 = cp[seg + 1]
        t = 0 if d1 == d0 else (d - d0) / (d1 - d0)
        base = v0 + (v1 - v0) * t
        noise = random.gauss(0, base * 0.006)
        path.append(max(1.0, base + noise))
    path[0] = float(control_points[0][1])
    return path


def get_crisis_path(scenario_id: str):
    """세션 동안 동일한 시나리오는 같은 경로를 유지 (재실행 버튼으로만 재생성)."""
    key = f"_crisis_path_{scenario_id}"
    if key not in st.session_state:
        st.session_state[key] = _crisis_path(CRISIS_BY_ID[scenario_id]["control_points"])
    return st.session_state[key]


def reset_crisis_path(scenario_id: str):
    st.session_state.pop(f"_crisis_path_{scenario_id}", None)


def simulate_crisis_decisions(scenario_id: str, decisions: dict):
    """decisions: {decision_day: choice_id} (choice_id는 CRISIS_DECISION_CHOICES의 id)
    가상 투자금 1,000,000원을 시작 시점에 전액 투입했다고 가정하고, 각 결정 시점의 선택에 따라
    최종 결과값과 '아무 결정도 안 하고 계속 보유(buy&hold)'했을 때를 비교한다."""
    path = get_crisis_path(scenario_id)
    scenario = CRISIS_BY_ID[scenario_id]
    seed = 1_000_000
    units = seed / path[0]     # 보유 좌수
    banked_cash = 0.0          # 매도해서 현금화한 금액 (재투자하지 않음)
    extra_invested = 0.0       # 물타기로 추가 투입한 원금 (원금 대비 비교용)
    user_curve = []

    for day, val in enumerate(path):
        if day in decisions:
            choice = decisions[day]
            if choice == "sell_all":
                banked_cash += units * val
                units = 0.0
            elif choice == "sell_half":
                banked_cash += (units * 0.5) * val
                units *= 0.5
            elif choice == "buy_more":
                units += seed / val
                extra_invested += seed
            # "hold"는 변화 없음
        user_curve.append(banked_cash + units * val)

    final_value = user_curve[-1]
    baseline_value = (seed / path[0]) * path[-1]  # 아무 결정 없이 처음부터 끝까지 보유
    total_principal = seed + extra_invested

    return {
        "scenario": scenario, "path": path, "user_curve": user_curve,
        "final_value": final_value, "baseline_value": baseline_value,
        "principal": total_principal, "decisions": decisions,
    }


def record_crisis_result(user, scenario_id: str, result: dict):
    rl = user["risk_lab"]
    rl["crisis_completed"][scenario_id] = {
        "final_value": result["final_value"],
        "baseline_value": result["baseline_value"],
        "principal": result["principal"],
    }


def check_risk_lab_badges(user):
    """리스크 체험관 전용 뱃지를 점검해 지급하고, 새로 획득한 뱃지 id 목록을 반환한다."""
    newly = []
    rl = user["risk_lab"]

    if len(rl.get("scam_scores", {})) >= 1 and award_badge(user, "scam_shield_first"):
        newly.append("scam_shield_first")
    if sum(rl.get("scam_scores", {}).values()) >= SCAM_MAX_SCORE and award_badge(user, "scam_shield_master"):
        newly.append("scam_shield_master")

    if rl.get("leverage_trials", 0) >= 1 and award_badge(user, "leverage_tried"):
        newly.append("leverage_tried")
    if rl.get("leverage_liquidations", 0) >= 1 and award_badge(user, "leverage_liquidated"):
        newly.append("leverage_liquidated")
    if rl.get("leverage_survive_5x", 0) >= 3 and award_badge(user, "leverage_survivor"):
        newly.append("leverage_survivor")

    if len(rl.get("crisis_completed", {})) >= 1 and award_badge(user, "crisis_navigator"):
        newly.append("crisis_navigator")
    if len(rl.get("crisis_completed", {})) >= len(CRISIS_SCENARIOS) and award_badge(user, "crisis_all_clear"):
        newly.append("crisis_all_clear")

    return newly


# ══════════════════════════════════════════════════════════════════════════
# 🎭 소비 페르소나 — 최근 3개월 지출 카테고리 비중을 규칙 기반으로 분석해 태그를 붙인다.
# ══════════════════════════════════════════════════════════════════════════
SPENDING_PERSONAS = [
    {"id": "sub_addict",  "icon": "📺", "name": "구독 중독형",
     "desc": "매달 빠져나가는 구독료가 쌓여 지출의 큰 축을 차지하고 있어요. 안 쓰는 구독은 없는지 한 번 점검해보세요."},
    {"id": "caffeine",    "icon": "☕", "name": "카페인 러버형",
     "desc": "카페/간식 지출 비중이 눈에 띄게 높아요. 하루 한 잔의 습관이 한 달이면 꽤 큰 돈이 됩니다."},
    {"id": "flex",        "icon": "🛍️", "name": "플렉스형",
     "desc": "쇼핑 지출 비중이 커요. 큰 소비 전에 '이게 정말 필요한가'를 한 번 더 물어보는 습관을 들여보세요."},
    {"id": "leisure",     "icon": "🎮", "name": "여가 러버형",
     "desc": "여가/문화 지출 비중이 높아요. 삶의 만족도엔 좋지만, 예산 안에서 즐기고 있는지 가끔 점검해봐요."},
    {"id": "homebody",    "icon": "🏠", "name": "안정 지향형",
     "desc": "주거/공과금 등 고정비 비중이 크고 전체 지출은 안정적이에요. 여유 자금을 저축/투자로 옮겨볼 타이밍입니다."},
    {"id": "balanced",    "icon": "⚖️", "name": "균형 잡힌 소비형",
     "desc": "특정 카테고리에 치우치지 않고 고르게 소비하고 있어요. 지금의 균형 감각을 잘 유지해보세요."},
    {"id": "no_data",     "icon": "🌱", "name": "아직 데이터가 부족해요",
     "desc": "가계부 기록이 조금 더 쌓이면 당신만의 소비 페르소나를 분석해드릴게요."},
]
PERSONA_BY_ID = {p["id"]: p for p in SPENDING_PERSONAS}
_PERSONA_CATEGORY_MAP = {"sub": "sub_addict", "cafe": "caffeine", "shopping": "flex", "leisure": "leisure"}


def spending_persona(user):
    tx = user.get("tx_log", [])
    now = time.time()
    three_months_ago = now - 90 * 24 * 3600
    expenses = [t for t in tx if t.get("kind") == "expense" and t.get("ts", 0) >= three_months_ago]
    total = sum(t.get("amount", 0) for t in expenses)
    if total <= 0 or len(expenses) < 3:
        return PERSONA_BY_ID["no_data"]

    by_cat = {}
    for t in expenses:
        by_cat[t.get("category", "etc")] = by_cat.get(t.get("category", "etc"), 0) + t.get("amount", 0)
    ratios = {cat: amt / total for cat, amt in by_cat.items()}

    living_ratio = ratios.get("living", 0)
    if living_ratio >= 0.4 and max([r for c, r in ratios.items() if c != "living"], default=0) < 0.2:
        return PERSONA_BY_ID["homebody"]

    best_cat, best_ratio = max(
        ((c, r) for c, r in ratios.items() if c in _PERSONA_CATEGORY_MAP), key=lambda x: x[1], default=(None, 0))
    if best_cat and best_ratio >= 0.22:
        return PERSONA_BY_ID[_PERSONA_CATEGORY_MAP[best_cat]]

    return PERSONA_BY_ID["balanced"]


# ══════════════════════════════════════════════════════════════════════════
# 🧓 노후 준비 설계 — 단리/복리 누적 + '연간 지출의 25배' 목표자금 휴리스틱(4% 룰 근사) 기반 계산기.
# 실제 연금 상품과 무관한 교육용 근사 계산입니다.
# ══════════════════════════════════════════════════════════════════════════
def estimate_retirement(current_age: int, retire_age: int, current_assets: float,
                         monthly_saving: float, annual_return_pct: float,
                         monthly_expense_today: float, inflation_pct: float,
                         withdrawal_multiple: float = 25.0):
    years = max(0, retire_age - current_age)
    months = years * 12
    monthly_return = (1 + annual_return_pct / 100) ** (1 / 12) - 1

    curve = [current_assets]
    balance = float(current_assets)
    for _m in range(months):
        balance = balance * (1 + monthly_return) + monthly_saving
        curve.append(balance)

    projected_corpus = curve[-1]
    future_monthly_expense = monthly_expense_today * ((1 + inflation_pct / 100) ** years)
    needed_corpus = future_monthly_expense * 12 * withdrawal_multiple

    gap = projected_corpus - needed_corpus
    achieved_pct = min(2.0, projected_corpus / needed_corpus) if needed_corpus > 0 else 1.0

    # 목표 달성에 필요한 월 저축액 역산 (연금 미래가치 공식, monthly_return≈0인 경우도 처리)
    if months > 0:
        if abs(monthly_return) < 1e-9:
            required_monthly = (needed_corpus - current_assets) / months
        else:
            fv_factor = ((1 + monthly_return) ** months - 1) / monthly_return
            required_monthly = (needed_corpus - current_assets * (1 + monthly_return) ** months) / fv_factor
        required_monthly = max(0.0, required_monthly)
    else:
        required_monthly = 0.0

    return {
        "years": years, "curve": curve, "projected_corpus": projected_corpus,
        "needed_corpus": needed_corpus, "future_monthly_expense": future_monthly_expense,
        "gap": gap, "achieved_pct": achieved_pct, "required_monthly": required_monthly,
    }
