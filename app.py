# app.py — 머니레벨업: 사회초년생을 위한 AI 금융 코칭 모의투자 앱
import time
import streamlit as st
import pandas as pd

from utils.config import ASSET_CONFIG, EXPENSE_CATEGORIES, SAVINGS_PRODUCTS
from utils.core import (
    signup, login, get_user, save_user, get_net_worth,
    get_market, tick_market, format_korean_money,
)
from utils.database import log_tx, load_tx
from utils.ai_coach import get_financial_diagnosis

st.set_page_config(page_title="머니레벨업 | AI 금융 코치", page_icon="💡", layout="wide")

ASSET_BY_ID = {a["id"]: a for a in ASSET_CONFIG}
CAT_BY_ID = {c["id"]: c for c in EXPENSE_CATEGORIES}
SAVE_BY_ID = {s["id"]: s for s in SAVINGS_PRODUCTS}


# ── 로그인 화면 ───────────────────────────────────────────────────────────
def login_screen():
    st.title("💡 머니레벨업")
    st.caption("사회초년생을 위한 AI 소비·투자 코칭 모의 서비스 — 실제 돈이 오가지 않는 시뮬레이션입니다.")
    tab1, tab2 = st.tabs(["로그인", "회원가입"])
    with tab1:
        uid = st.text_input("아이디", key="li_uid")
        pw = st.text_input("비밀번호", type="password", key="li_pw")
        if st.button("로그인", type="primary", use_container_width=True):
            ok, msg = login(uid, pw)
            if ok:
                st.session_state.logged_in_user = uid
                st.rerun()
            else:
                st.error(msg)
    with tab2:
        uid = st.text_input("아이디", key="su_uid")
        pw = st.text_input("비밀번호", type="password", key="su_pw")
        if st.button("가입하기", use_container_width=True):
            if len(uid) < 3 or len(pw) < 4:
                st.error("아이디 3자 이상, 비밀번호 4자 이상으로 입력해주세요.")
            else:
                ok, msg = signup(uid, pw)
                if ok:
                    st.success("가입 완료! 로그인 탭에서 로그인해주세요. (시작 자금 300만원 지급)")
                else:
                    st.error(msg)


# ── 대시보드 ──────────────────────────────────────────────────────────────
def render_dashboard(user, market):
    nw = get_net_worth(user, market)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("순자산", format_korean_money(nw))
    c2.metric("현금", format_korean_money(user.get("cash", 0)))
    invest_val = sum(pos["qty"] * market["prices"].get(aid, 0) for aid, pos in user.get("portfolio", {}).items())
    c3.metric("투자 평가액", format_korean_money(invest_val))
    save_val = sum(s["amount"] for s in user.get("savings", []))
    c4.metric("저축액", format_korean_money(save_val))

    if user.get("portfolio"):
        st.subheader("보유 포트폴리오")
        rows = []
        for aid, pos in user["portfolio"].items():
            a = ASSET_BY_ID[aid]
            cur = market["prices"].get(aid, 0)
            val = pos["qty"] * cur
            pnl = (cur - pos["avg_price"]) * pos["qty"]
            rows.append({"자산": f"{a['icon']} {a['name']}", "수량": pos["qty"],
                         "평단가": format_korean_money(pos["avg_price"]),
                         "현재가": format_korean_money(cur),
                         "평가액": format_korean_money(val),
                         "손익": format_korean_money(pnl)})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("아직 투자한 자산이 없어요. '모의투자' 탭에서 시작해보세요.")


# ── 모의투자 ──────────────────────────────────────────────────────────────
def render_invest(user, market):
    st.caption("⚠️ 실제 시세가 아닌 랜덤워크 기반 가상 시뮬레이션입니다. (약 30초마다 가격 변동)")
    cols = st.columns(4)
    for i, a in enumerate(ASSET_CONFIG):
        with cols[i % 4]:
            price = market["prices"][a["id"]]
            hist = market["history"].get(a["id"], [price])
            chg = (price - hist[0]) / hist[0] * 100 if hist[0] else 0
            st.metric(f"{a['icon']} {a['name']}", format_korean_money(price), f"{chg:+.2f}%")

    st.divider()
    asset_id = st.selectbox("종목 선택", [a["id"] for a in ASSET_CONFIG],
                             format_func=lambda x: f"{ASSET_BY_ID[x]['icon']} {ASSET_BY_ID[x]['name']} ({ASSET_BY_ID[x]['type']})")
    price = market["prices"][asset_id]
    st.write(f"현재가: **{format_korean_money(price)}**")

    b1, b2 = st.columns(2)
    with b1:
        buy_qty = st.number_input("매수 수량", min_value=1, value=1, key="buy_qty")
        if st.button("매수", type="primary", use_container_width=True):
            cost = buy_qty * price
            if user["cash"] < cost:
                st.error("현금이 부족합니다.")
            else:
                user["cash"] -= cost
                pos = user["portfolio"].get(asset_id, {"qty": 0, "avg_price": price})
                total_qty = pos["qty"] + buy_qty
                pos["avg_price"] = (pos["avg_price"] * pos["qty"] + cost) / total_qty
                pos["qty"] = total_qty
                user["portfolio"][asset_id] = pos
                save_user(user["uid"], user)
                log_tx(user["uid"], {"kind": "invest_buy", "asset": asset_id, "qty": buy_qty, "price": price})
                st.success(f"{buy_qty}주 매수 완료")
                st.rerun()
    with b2:
        own_qty = user["portfolio"].get(asset_id, {}).get("qty", 0)
        sell_qty = st.number_input(f"매도 수량 (보유 {own_qty})", min_value=1, value=1, key="sell_qty")
        if st.button("매도", use_container_width=True):
            if own_qty < sell_qty:
                st.error("보유 수량이 부족합니다.")
            else:
                user["cash"] += sell_qty * price
                user["portfolio"][asset_id]["qty"] -= sell_qty
                if user["portfolio"][asset_id]["qty"] == 0:
                    del user["portfolio"][asset_id]
                save_user(user["uid"], user)
                log_tx(user["uid"], {"kind": "invest_sell", "asset": asset_id, "qty": sell_qty, "price": price})
                st.success(f"{sell_qty}주 매도 완료")
                st.rerun()


# ── 가계부 ────────────────────────────────────────────────────────────────
def render_expense(user):
    st.subheader("지출 기록하기")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        cat = st.selectbox("카테고리", [c["id"] for c in EXPENSE_CATEGORIES],
                            format_func=lambda x: f"{CAT_BY_ID[x]['icon']} {CAT_BY_ID[x]['name']}")
    with c2:
        amount = st.number_input("금액(원)", min_value=0, step=1000, value=10000)
    with c3:
        memo = st.text_input("메모", placeholder="예: 점심")
    if st.button("기록 추가", type="primary"):
        if amount <= 0 or user["cash"] < amount:
            st.error("금액을 확인해주세요. (현금 부족 시 기록 불가)")
        else:
            user["cash"] -= amount
            user["expense_total"] = user.get("expense_total", 0) + amount
            save_user(user["uid"], user)
            log_tx(user["uid"], {"kind": "expense", "category": cat, "amount": amount, "memo": memo})
            st.success("기록 완료")
            st.rerun()

    st.divider()
    st.subheader("최근 지출 내역")
    tx = [t for t in load_tx(user["uid"], 100) if t.get("kind") == "expense"]
    if not tx:
        st.info("아직 기록된 지출이 없어요.")
        return
    rows = [{"날짜": time.strftime("%m/%d %H:%M", time.localtime(t["ts"])),
             "카테고리": f"{CAT_BY_ID[t['category']]['icon']} {CAT_BY_ID[t['category']]['name']}",
             "금액": format_korean_money(t["amount"]), "메모": t.get("memo", "")} for t in tx]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    cat_sum = {}
    for t in tx:
        name = CAT_BY_ID[t["category"]]["name"]
        cat_sum[name] = cat_sum.get(name, 0) + t["amount"]
    st.bar_chart(pd.Series(cat_sum))


# ── 예/적금 ───────────────────────────────────────────────────────────────
def render_savings(user):
    st.subheader("예/적금 가입")
    for p in SAVINGS_PRODUCTS:
        with st.container(border=True):
            st.write(f"**{p['name']}** — 연 {p['rate']*100:.1f}%")
            st.caption(p["desc"])
            amt = st.number_input(f"가입 금액 ({p['name']})", min_value=0, step=10000, key=f"sv_{p['id']}")
            if st.button(f"{p['name']} 가입", key=f"btn_{p['id']}"):
                if amt <= 0 or user["cash"] < amt:
                    st.error("금액을 확인해주세요.")
                else:
                    user["cash"] -= amt
                    user["savings"].append({"product_id": p["id"], "amount": amt, "start": time.time()})
                    save_user(user["uid"], user)
                    log_tx(user["uid"], {"kind": "savings_open", "product": p["id"], "amount": amt})
                    st.success("가입 완료")
                    st.rerun()

    if user.get("savings"):
        st.divider()
        st.subheader("가입 현황")
        rows = [{"상품": SAVE_BY_ID[s["product_id"]]["name"], "금액": format_korean_money(s["amount"]),
                 "가입일": time.strftime("%Y-%m-%d", time.localtime(s["start"]))} for s in user["savings"]]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── AI 코치 ───────────────────────────────────────────────────────────────
def render_ai_coach(user, market):
    st.subheader("🤖 AI 금융 코치")
    st.caption("최근 소비·투자·저축 데이터를 바탕으로 Claude가 개인화된 진단을 제공합니다.")
    if st.button("AI 진단 받기", type="primary"):
        tx = load_tx(user["uid"], 200)
        spending = {}
        for t in tx:
            if t.get("kind") == "expense":
                name = CAT_BY_ID[t["category"]]["name"]
                spending[name] = spending.get(name, 0) + t["amount"]

        portfolio_summary = []
        for aid, pos in user.get("portfolio", {}).items():
            a = ASSET_BY_ID[aid]
            val = pos["qty"] * market["prices"].get(aid, 0)
            portfolio_summary.append({"name": a["name"], "type": a["type"], "value": val})

        savings_total = sum(s["amount"] for s in user.get("savings", []))

        with st.spinner("AI가 데이터를 분석하는 중..."):
            result = get_financial_diagnosis(spending, portfolio_summary, savings_total, user.get("cash", 0))

        st.session_state["ai_result"] = result

    result = st.session_state.get("ai_result")
    if result:
        risk_color = {"낮음": "green", "보통": "orange", "높음": "red"}.get(result.get("risk_level"), "gray")
        st.markdown(f"### {result.get('summary','')}")
        st.markdown(f"**리스크 수준:** :{risk_color}[{result.get('risk_level','-')}]")
        st.write("**소비 분석**")
        st.write(result.get("spending_insight", ""))
        st.write("**투자 분석**")
        st.write(result.get("investing_insight", ""))
        if result.get("action_items"):
            st.write("**추천 행동**")
            for item in result["action_items"]:
                st.write(f"- {item}")


# ── 메인 ──────────────────────────────────────────────────────────────────
def main():
    if "logged_in_user" not in st.session_state:
        login_screen()
        return

    uid = st.session_state.logged_in_user
    user = get_user(uid)
    market = tick_market()

    with st.sidebar:
        st.write(f"👤 **{uid}**님")
        if st.button("로그아웃"):
            del st.session_state["logged_in_user"]
            st.rerun()
        st.divider()
        st.caption("머니레벨업은 실제 금전 거래가 없는 교육용 시뮬레이션입니다.")

    st.title("💡 머니레벨업")
    tabs = st.tabs(["📊 대시보드", "📈 모의투자", "🧾 가계부", "🏦 예/적금", "🤖 AI 코치"])
    with tabs[0]:
        render_dashboard(user, market)
    with tabs[1]:
        render_invest(user, market)
    with tabs[2]:
        render_expense(user)
    with tabs[3]:
        render_savings(user)
    with tabs[4]:
        render_ai_coach(user, market)


if __name__ == "__main__":
    main()
