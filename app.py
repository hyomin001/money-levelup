# app.py — 머니레벨업: 사회초년생을 위한 AI 금융 코칭 모의투자 앱
import time
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

from utils.config import ASSET_CONFIG, EXPENSE_CATEGORIES, SAVINGS_PRODUCTS, STARTING_CASH
from utils.core import (
    get_user, log_tx, get_net_worth,
    get_market, tick_market, format_korean_money,
)
from utils.ai_coach import get_financial_diagnosis

st.set_page_config(page_title="머니레벨업 | AI 금융 코치", page_icon="💡", layout="wide")

ASSET_BY_ID = {a["id"]: a for a in ASSET_CONFIG}
CAT_BY_ID = {c["id"]: c for c in EXPENSE_CATEGORIES}
SAVE_BY_ID = {s["id"]: s for s in SAVINGS_PRODUCTS}

PLOTLY_DARK = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E1", family="Noto Sans KR, sans-serif"),
    margin=dict(l=10, r=10, t=10, b=10),
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Noto+Sans+KR:wght@400;500;700&display=swap');

.stApp { background: #0A0A12; }
h1, h2, h3 { font-family: 'Noto Sans KR', sans-serif !important; }

/* 상단 타이틀 그라디언트 */
.ml-hero {
    background: linear-gradient(135deg,#161628,#0D0D18);
    border: 1px solid #23233B; border-radius: 18px;
    padding: 22px 26px; margin-bottom: 14px;
}
.ml-hero h1 { margin: 0; font-size: 1.7rem; color: #E2E8F0; }
.ml-hero p  { margin: 4px 0 0 0; color: #8891A8; font-size: 0.88rem; }

/* 뉴스 티커 */
.ticker-wrap {
    overflow: hidden; white-space: nowrap;
    background: #0D0D18; border: 1px solid #23233B;
    border-radius: 10px; padding: 9px 0; margin-bottom: 16px;
}
.ticker-inner { display: inline-block; animation: ticker-scroll 26s linear infinite; }
.ticker-inner:hover { animation-play-state: paused; }
@keyframes ticker-scroll { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
.ticker-item { display: inline-flex; align-items: center; gap: 8px; margin-right: 46px; font-size: 0.83rem; color: #9AA5C0; }
.ticker-item b { color: #E2E8F0; }

/* 카드형 metric */
div[data-testid="stMetric"] {
    background: #12121F; border: 1px solid #23233B; border-radius: 14px;
    padding: 14px 16px;
}
div[data-testid="stMetricLabel"] { color: #8891A8 !important; }

/* 자산 카드 */
.asset-card {
    background: #10101C; border: 1px solid #1E2035; border-radius: 14px;
    padding: 12px 14px; margin-bottom: 6px;
}
.asset-card .a-name { font-size: 0.8rem; color: #94A3B8; }
.asset-card .a-price { font-family: 'Orbitron', monospace; font-size: 1.05rem; color: #E2E8F0; font-weight: 700; }
.up   { color: #FF5C5C !important; }
.down { color: #4C8DFF !important; }

/* 뉴스 카드 */
.news-item { border-left: 3px solid #3D4270; padding: 6px 12px; margin-bottom: 6px; background: #10101C; border-radius: 0 8px 8px 0; }
.news-item .n-time { font-size: 0.72rem; color: #64748B; }
.news-item .n-text { font-size: 0.85rem; color: #CBD5E1; }
</style>
"""


def price_chart(asset_id, market):
    hist = market["history"].get(asset_id, [])
    if len(hist) < 2:
        hist = hist * 2
    up = hist[-1] >= hist[0]
    line_color = "#FF5C5C" if up else "#4C8DFF"
    fill_color = "rgba(255,92,92,0.10)" if up else "rgba(76,141,255,0.10)"
    fig = go.Figure(go.Scatter(
        x=list(range(len(hist))), y=hist, mode="lines",
        line=dict(color=line_color, width=2.2),
        fill="tozeroy", fillcolor=fill_color,
    ))
    fig.update_layout(**PLOTLY_DARK, height=220, showlegend=False)
    fig.update_yaxes(showgrid=False, range=[min(hist) * 0.985, max(hist) * 1.015])
    fig.update_xaxes(showgrid=False, showticklabels=False)
    return fig


def portfolio_donut(user, market):
    labels, values = [], []
    for aid, pos in user.get("portfolio", {}).items():
        val = pos["qty"] * market["prices"].get(aid, 0)
        if val > 0:
            labels.append(ASSET_BY_ID[aid]["name"])
            values.append(val)
    if user.get("cash", 0) > 0:
        labels.append("현금")
        values.append(user["cash"])
    if not values:
        return None
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.62,
        marker=dict(colors=["#5C6BC0", "#4C8DFF", "#FF5C5C", "#FFB74D", "#66BB6A", "#BA68C8", "#26C6DA", "#9AA5C0"]),
        textinfo="label+percent", textfont=dict(size=11, color="#E2E8F0"),
    ))
    fig.update_layout(**PLOTLY_DARK, height=280, showlegend=False)
    return fig


def render_news_ticker(market):
    items = market.get("news", [])
    if not items:
        html = "<div class='ticker-item'>📡 시장 뉴스를 수신 대기 중입니다...</div>"
    else:
        html = "".join(
            f"<span class='ticker-item'>📰 <b>{ASSET_BY_ID.get(n['asset'],{}).get('name', n['asset'])}</b> · {n['text']}</span>"
            for n in items[:8]
        )
    st.markdown(f"<div class='ticker-wrap'><div class='ticker-inner'>{html}{html}</div></div>", unsafe_allow_html=True)


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

    st.write("")
    col_l, col_r = st.columns([3, 2])
    with col_l:
        if user.get("portfolio"):
            st.subheader("보유 포트폴리오")
            rows = []
            for aid, pos in user["portfolio"].items():
                a = ASSET_BY_ID[aid]
                cur = market["prices"].get(aid, 0)
                val = pos["qty"] * cur
                pnl = (cur - pos["avg_price"]) * pos["qty"]
                pnl_pct = (cur / pos["avg_price"] - 1) * 100 if pos["avg_price"] else 0
                rows.append({"자산": f"{a['icon']} {a['name']}", "수량": pos["qty"],
                             "평단가": format_korean_money(pos["avg_price"]),
                             "현재가": format_korean_money(cur),
                             "평가액": format_korean_money(val),
                             "손익": f"{format_korean_money(pnl)} ({pnl_pct:+.1f}%)"})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("아직 투자한 자산이 없어요. '모의투자' 탭에서 시작해보세요.")
    with col_r:
        st.subheader("자산 배분")
        fig = portfolio_donut(user, market)
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("자산이 쌓이면 여기에 배분 차트가 표시돼요.")


# ── 모의투자 ──────────────────────────────────────────────────────────────
def render_invest(user, market):
    st.caption("⚠️ 실제 시세가 아닌 랜덤워크+뉴스 이벤트 기반 가상 시뮬레이션입니다. (약 15초마다 갱신)")

    cols = st.columns(4)
    for i, a in enumerate(ASSET_CONFIG):
        with cols[i % 4]:
            price = market["prices"][a["id"]]
            hist = market["history"].get(a["id"], [price])
            chg = (price - hist[0]) / hist[0] * 100 if hist[0] else 0
            cls = "up" if chg >= 0 else "down"
            arrow = "▲" if chg >= 0 else "▼"
            st.markdown(f"""<div class="asset-card">
                <div class="a-name">{a['icon']} {a['name']}</div>
                <div class="a-price">{format_korean_money(price)}</div>
                <div class="{cls}">{arrow} {chg:+.2f}%</div>
                </div>""", unsafe_allow_html=True)

    st.divider()
    c_chart, c_trade = st.columns([3, 2])

    with c_chart:
        asset_id = st.selectbox("종목 선택", [a["id"] for a in ASSET_CONFIG],
                                 format_func=lambda x: f"{ASSET_BY_ID[x]['icon']} {ASSET_BY_ID[x]['name']} ({ASSET_BY_ID[x]['type']})")
        price = market["prices"][asset_id]
        st.plotly_chart(price_chart(asset_id, market), use_container_width=True, config={"displayModeBar": False})
        st.write(f"현재가: **{format_korean_money(price)}**")

        st.markdown("**📰 관련 뉴스**")
        related = [n for n in market.get("news", []) if n["asset"] == asset_id][:5]
        if related:
            for n in related:
                st.markdown(f"""<div class="news-item">
                    <div class="n-time">{time.strftime('%H:%M', time.localtime(n['ts']))}</div>
                    <div class="n-text">{n['text']}</div></div>""", unsafe_allow_html=True)
        else:
            st.caption("최근 관련 뉴스가 없습니다.")

    with c_trade:
        st.markdown("**매수 / 매도**")
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
                log_tx({"kind": "invest_buy", "asset": asset_id, "qty": buy_qty, "price": price})
                st.success(f"{buy_qty}주 매수 완료")
                st.rerun()

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
                log_tx({"kind": "invest_sell", "asset": asset_id, "qty": sell_qty, "price": price})
                st.success(f"{sell_qty}주 매도 완료")
                st.rerun()

        st.divider()
        st.markdown("**🌍 전체 시장 뉴스**")
        for n in market.get("news", [])[:6]:
            st.markdown(f"""<div class="news-item">
                <div class="n-time">{time.strftime('%H:%M', time.localtime(n['ts']))} · {ASSET_BY_ID.get(n['asset'],{}).get('name','')}</div>
                <div class="n-text">{n['text']}</div></div>""", unsafe_allow_html=True)


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
            log_tx({"kind": "expense", "category": cat, "amount": amount, "memo": memo})
            st.success("기록 완료")
            st.rerun()

    st.divider()
    tx = [t for t in user["tx_log"] if t.get("kind") == "expense"]
    if not tx:
        st.info("아직 기록된 지출이 없어요.")
        return

    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.subheader("최근 지출 내역")
        rows = [{"날짜": time.strftime("%m/%d %H:%M", time.localtime(t["ts"])),
                 "카테고리": f"{CAT_BY_ID[t['category']]['icon']} {CAT_BY_ID[t['category']]['name']}",
                 "금액": format_korean_money(t["amount"]), "메모": t.get("memo", "")} for t in tx]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with col_r:
        st.subheader("카테고리별 비중")
        cat_sum = {}
        for t in tx:
            name = CAT_BY_ID[t["category"]]["name"]
            cat_sum[name] = cat_sum.get(name, 0) + t["amount"]
        fig = go.Figure(go.Pie(labels=list(cat_sum.keys()), values=list(cat_sum.values()), hole=0.55,
                                marker=dict(colors=["#5C6BC0", "#4C8DFF", "#FF5C5C", "#FFB74D", "#66BB6A", "#BA68C8", "#26C6DA", "#9AA5C0"])))
        fig.update_layout(**PLOTLY_DARK, height=260, showlegend=True, legend=dict(font=dict(size=10)))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── 예/적금 ───────────────────────────────────────────────────────────────
def render_savings(user):
    st.subheader("예/적금 가입")
    cols = st.columns(3)
    for i, p in enumerate(SAVINGS_PRODUCTS):
        with cols[i]:
            with st.container(border=True):
                st.write(f"**{p['name']}**")
                st.caption(f"연 {p['rate']*100:.1f}% · {p['desc']}")
                amt = st.number_input("가입 금액", min_value=0, step=10000, key=f"sv_{p['id']}")
                if st.button(f"가입하기", key=f"btn_{p['id']}", use_container_width=True):
                    if amt <= 0 or user["cash"] < amt:
                        st.error("금액을 확인해주세요.")
                    else:
                        user["cash"] -= amt
                        user["savings"].append({"product_id": p["id"], "amount": amt, "start": time.time()})
                        log_tx({"kind": "savings_open", "product": p["id"], "amount": amt})
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
    st.caption("최근 소비·투자·저축 데이터를 바탕으로 Gemini가 개인화된 진단을 제공합니다.")
    if st.button("AI 진단 받기", type="primary"):
        spending = {}
        for t in user["tx_log"]:
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
        with st.container(border=True):
            st.markdown(f"### {result.get('summary','')}")
            st.markdown(f"**리스크 수준:** :{risk_color}[{result.get('risk_level','-')}]")
            c1, c2 = st.columns(2)
            with c1:
                st.write("**💸 소비 분석**")
                st.write(result.get("spending_insight", ""))
            with c2:
                st.write("**📈 투자 분석**")
                st.write(result.get("investing_insight", ""))
            if result.get("action_items"):
                st.write("**✅ 추천 행동**")
                for item in result["action_items"]:
                    st.write(f"- {item}")


# ── 메인 ──────────────────────────────────────────────────────────────────
def main():
    st.markdown(CSS, unsafe_allow_html=True)
    st_autorefresh(interval=15_000, key="market_tick")

    user = get_user()
    market = tick_market()

    with st.sidebar:
        st.write("💡 **머니레벨업 체험판**")
        st.caption("로그인 없이 바로 체험할 수 있는 데모입니다. 새로고침하면 데이터가 초기화됩니다.")
        if st.button("🔄 처음부터 다시 시작"):
            for k in ("user", "market", "ai_result"):
                st.session_state.pop(k, None)
            st.rerun()
        st.divider()
        st.caption(f"시작 자금: {format_korean_money(STARTING_CASH)}")
        st.caption("실제 금전 거래가 없는 교육용 시뮬레이션입니다.")

    st.markdown("""<div class="ml-hero">
        <h1>💡 머니레벨업</h1>
        <p>사회초년생을 위한 AI 소비·투자 코칭 모의 서비스</p>
        </div>""", unsafe_allow_html=True)

    render_news_ticker(market)

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
