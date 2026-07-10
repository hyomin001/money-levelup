# app.py — 머니레벨업: 사회초년생을 위한 AI 금융 코칭 모의투자 앱
import time
from datetime import date

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

from utils.config import (
    ASSET_CONFIG, EXPENSE_CATEGORIES, SAVINGS_PRODUCTS, STARTING_CASH,
    ONBOARDING_QUESTIONS, BADGES, BENCHMARK_SPENDING_RATIO,
)
from utils.core import (
    get_user, save_user, default_user, log_tx, get_net_worth,
    get_market, tick_market, format_korean_money,
    get_level, xp_progress, check_habit_badges, award_badge, BADGE_BY_ID,
    set_goal, goal_progress, record_net_worth_point,
    create_saving, saving_progress, total_saving_amount,
)
from utils.ai_coach import get_financial_diagnosis, get_risk_profile
from utils.database import db_available

st.set_page_config(page_title="머니레벨업 | AI 금융 코치", page_icon="💡", layout="wide")

ASSET_BY_ID = {a["id"]: a for a in ASSET_CONFIG}
CAT_BY_ID = {c["id"]: c for c in EXPENSE_CATEGORIES}


def _persist(user):
    """현재 유저 데이터를 DB에 저장 (미연결 시 조용히 무시됨)."""
    profile = st.session_state.get("profile")
    if profile:
        save_user(profile["uid"], user)


def relative_time(ts):
    diff = time.time() - ts
    if diff < 60:
        return "방금 전"
    if diff < 3600:
        return f"{int(diff // 60)}분 전"
    if diff < 86400:
        return f"{int(diff // 3600)}시간 전"
    return time.strftime("%m/%d", time.localtime(ts))


PLOTLY_DARK = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E1", family="Noto Sans KR, sans-serif"),
    margin=dict(l=10, r=10, t=10, b=10),
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;800&family=Noto+Sans+KR:wght@400;500;700;900&display=swap');

.stApp { background: radial-gradient(1200px 800px at 10% -10%, #14142A 0%, #0A0A12 55%); }
h1, h2, h3, h4 { font-family: 'Noto Sans KR', sans-serif !important; }

/* 기본 텍스트 대비 보정 (다크 테마 위 회색 텍스트가 배경에 묻히지 않도록) */
.stMarkdown, .stMarkdown p, .stMarkdown li, label, .stCaption, p, span, div[data-testid="stText"] {
    color: #E7EAF6;
}
.stApp small, .stCaption, [data-testid="stCaptionContainer"] { color: #97A0C0 !important; }

/* 상단 타이틀 그라디언트 */
.ml-hero {
    background: linear-gradient(135deg,#1B1B36,#0D0D18);
    border: 1px solid #2A2A50; border-radius: 20px;
    padding: 24px 28px; margin-bottom: 14px;
    box-shadow: 0 8px 30px rgba(76,90,255,0.08);
}
.ml-hero h1 { margin: 0; font-size: 1.8rem; color: #F1F3FC; }
.ml-hero p  { margin: 6px 0 0 0; color: #9AA5C0; font-size: 0.9rem; }

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
.ticker-item b { color: #E7EAF6; }

/* 카드형 metric */
div[data-testid="stMetric"] {
    background: #12121F; border: 1px solid #23233B; border-radius: 14px;
    padding: 14px 16px;
}
div[data-testid="stMetricLabel"] { color: #97A0C0 !important; }
div[data-testid="stMetricValue"] { color: #F1F3FC !important; }

/* 자산 카드 */
.asset-card {
    background: #10101C; border: 1px solid #1E2035; border-radius: 14px;
    padding: 12px 14px; margin-bottom: 6px; transition: border-color .2s;
}
.asset-card:hover { border-color: #4C5AFF; }
.asset-card .a-name { font-size: 0.8rem; color: #97A0C0; }
.asset-card .a-price { font-family: 'Orbitron', monospace; font-size: 1.05rem; color: #F1F3FC; font-weight: 700; }
.up   { color: #FF5C6E !important; }
.down { color: #4C8DFF !important; }

/* 뉴스 카드 */
.news-item { border-left: 3px solid #3D4270; padding: 6px 12px; margin-bottom: 6px; background: #10101C; border-radius: 0 8px 8px 0; }
.news-item .n-time { font-size: 0.72rem; color: #6C7592; }
.news-item .n-text { font-size: 0.85rem; color: #D7DBEE; }

/* 호가창 */
.ob-wrap { border: 1px solid #23233B; border-radius: 12px; overflow: hidden; background: #0D0D18; }
.ob-row { position: relative; display: flex; justify-content: space-between; padding: 4px 12px; font-size: 0.8rem;
    font-family: 'Orbitron', monospace; overflow: hidden; }
.ob-row.ask { color: #7EB8FF; } .ob-row.bid { color: #FF8FA3; }
.ob-bar { position: absolute; right: 0; top: 0; bottom: 0; background: currentColor; opacity: 0.14; }
.ob-row span { position: relative; z-index: 1; }
.ob-cur { text-align: center; padding: 6px; background: #191A38; font-weight: 800; color: #F1F3FC;
    font-size: 0.88rem; border-top: 1px solid #2A2A50; border-bottom: 1px solid #2A2A50; letter-spacing: .3px; }
.ob-caption { font-size: 0.7rem; color: #6C7592; text-align: center; padding: 4px 0 0 0; }

/* 뱃지 카드 */
.badge-card { text-align:center; border-radius: 14px; padding: 14px 8px; margin-bottom: 10px; }
.badge-card.earned { background: linear-gradient(160deg,#22245A,#181933); border: 1px solid #4C5AFF;
    box-shadow: 0 0 16px rgba(76,90,255,0.18); }
.badge-card.locked { background: #101018; border: 1px solid #1E2035; opacity: 0.4; }
.badge-card .b-icon { font-size: 1.7rem; }
.badge-card .b-name { font-size: 0.78rem; color: #F1F3FC; font-weight: 700; margin-top: 4px; }
.badge-card .b-desc { font-size: 0.68rem; color: #8891A8; margin-top: 2px; min-height: 26px; }
.badge-card .b-xp { font-size: 0.65rem; color: #7EB8FF; margin-top: 3px; }

/* 레벨 바 */
.level-badge { display:inline-flex; align-items:center; gap:8px; background:#12121F; border:1px solid #23233B;
    border-radius: 999px; padding: 6px 14px; font-size: 0.82rem; color:#F1F3FC; }

/* 온보딩 카드 */
.onb-card { background:#10101C; border:1px solid #1E2035; border-radius:16px; padding:20px; margin-bottom:14px; }

/* ── 가계부: 카테고리 선택 pill ── */
.stButton > button {
    border-radius: 12px !important;
}
.cat-pill-active button {
    background: linear-gradient(135deg,#4C5AFF,#7C8CFF) !important;
    border: 1px solid #7C8CFF !important; color: white !important; font-weight: 700 !important;
}

/* 지출 카드 (귀엽게) */
.exp-card {
    display:flex; align-items:center; gap:12px;
    background: #12121F; border: 1px solid #23233B; border-left: 4px solid var(--accent, #7C8CFF);
    border-radius: 14px; padding: 10px 14px; margin-bottom: 8px;
}
.exp-card .exp-icon { font-size: 1.4rem; }
.exp-card .exp-main { flex: 1; }
.exp-card .exp-cat { font-size: 0.78rem; color: #97A0C0; }
.exp-card .exp-memo { font-size: 0.85rem; color: #E7EAF6; font-weight: 600; }
.exp-card .exp-amt { font-family:'Orbitron',monospace; font-weight:700; color:#FF8FA3; }
.exp-card .exp-time { font-size: 0.68rem; color: #6C7592; margin-top: 2px; }

/* ── 목표저축 / 예적금 카드 ── */
.goal-hero {
    background: linear-gradient(135deg,#241B3D,#141433);
    border: 1px solid #3D2E6B; border-radius: 18px; padding: 20px 22px; margin-bottom: 12px;
}
.goal-hero .g-name { font-size: 1.15rem; font-weight: 800; color: #F1F3FC; }
.goal-hero .g-sub { font-size: 0.8rem; color: #B7A9E8; margin-top: 2px; }

.sv-card {
    background: linear-gradient(160deg,#151530,#101022);
    border: 1px solid #23233B; border-radius: 18px; padding: 18px 20px; margin-bottom: 14px;
}
.sv-card .sv-title { font-size: 1.02rem; font-weight: 800; color: #F1F3FC; }
.sv-card .sv-sub { font-size: 0.75rem; color: #97A0C0; margin-top: 2px; margin-bottom: 10px; }
.sv-chip { display:inline-block; font-size: 0.68rem; padding: 2px 9px; border-radius: 999px; margin-left: 6px; }
.sv-chip.done { background: rgba(102,187,106,0.18); color: #81D186; border: 1px solid #3E7A44; }
.sv-chip.live { background: rgba(124,140,255,0.18); color: #A9B4FF; border: 1px solid #4C5AFF; }

/* 쫓아가는 진행 바 */
.chase-wrap { margin: 10px 0 4px 0; }
.chase-track { position: relative; height: 20px; background: #1A1A2C; border-radius: 999px;
    border: 1px solid #2A2A44; overflow: visible; }
.chase-fill { position: absolute; left:0; top:0; bottom:0; border-radius: 999px;
    background-size: 200% 100%; animation: chase-shimmer 2.2s linear infinite; transition: width .7s ease; }
@keyframes chase-shimmer { 0%{background-position:0% 0} 100%{background-position:200% 0} }
.chase-runner { position: absolute; top: 50%; transform: translateY(-50%); font-size: 1.05rem;
    filter: drop-shadow(0 0 4px rgba(0,0,0,.7)); transition: left .7s ease; }
.chase-labels { display:flex; justify-content: space-between; font-size: 0.7rem; color: #97A0C0; margin-top: 5px; }

/* ── AI 코치 ── */
.coach-card {
    position: relative; border-radius: 20px; padding: 24px 26px; margin-top: 6px;
    background: linear-gradient(160deg,#1A1338,#0E0E22);
    border: 1px solid #4C3F9C;
    box-shadow: 0 0 0 rgba(124,140,255,0.0);
    animation: coach-glow 2.6s ease-in-out infinite;
}
@keyframes coach-glow {
    0%, 100% { box-shadow: 0 0 18px rgba(124,140,255,0.10); border-color: #4C3F9C; }
    50% { box-shadow: 0 0 34px rgba(124,140,255,0.28); border-color: #7C8CFF; }
}
.coach-hype {
    font-family: 'Orbitron', sans-serif; font-weight: 800; font-size: 1.25rem;
    background: linear-gradient(90deg,#7C8CFF,#FF8FA3,#7C8CFF);
    background-size: 200% auto; -webkit-background-clip: text; background-clip: text; color: transparent;
    animation: coach-shine 3s linear infinite; margin-bottom: 6px;
}
@keyframes coach-shine { to { background-position: 200% center; } }
.coach-summary { font-size: 1.05rem; font-weight: 700; color: #F1F3FC; margin-bottom: 10px; }
.risk-chip { display:inline-block; padding: 3px 12px; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }
.risk-low { background: rgba(102,187,106,0.18); color:#81D186; border:1px solid #3E7A44; }
.risk-mid { background: rgba(255,183,77,0.18); color:#FFC96B; border:1px solid #8A6A2E; }
.risk-high{ background: rgba(255,92,110,0.18); color:#FF8FA3; border:1px solid #8A3040; }
</style>
"""


def price_chart(asset_id, market):
    hist = market["history"].get(asset_id, [])
    if len(hist) < 2:
        hist = hist * 2
    up = hist[-1] >= hist[0]
    line_color = "#FF5C6E" if up else "#4C8DFF"
    fill_color = "rgba(255,92,110,0.10)" if up else "rgba(76,141,255,0.10)"
    fig = go.Figure(go.Scatter(
        x=list(range(len(hist))), y=hist, mode="lines",
        line=dict(color=line_color, width=2.2),
        fill="tozeroy", fillcolor=fill_color,
    ))
    fig.update_layout(**PLOTLY_DARK, height=220, showlegend=False)
    fig.update_yaxes(showgrid=False, range=[min(hist) * 0.985, max(hist) * 1.015])
    fig.update_xaxes(showgrid=False, showticklabels=False)
    return fig


def net_worth_chart(user):
    hist = user.get("nw_history", [])
    if len(hist) < 2:
        return None
    vals = [h["value"] for h in hist]
    up = vals[-1] >= vals[0]
    color = "#66BB6A" if up else "#FF5C6E"
    fig = go.Figure(go.Scatter(y=vals, mode="lines+markers", line=dict(color=color, width=2.5),
                                marker=dict(size=4)))
    fig.update_layout(**PLOTLY_DARK, height=200, showlegend=False)
    fig.update_xaxes(showgrid=False, showticklabels=False)
    fig.update_yaxes(showgrid=False)
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
    if total_saving_amount(user) > 0:
        labels.append("저축")
        values.append(total_saving_amount(user))
    if not values:
        return None
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.62,
        marker=dict(colors=["#5C6BC0", "#4C8DFF", "#FF5C6E", "#FFB74D", "#66BB6A", "#BA68C8", "#26C6DA", "#9AA5C0"]),
        textinfo="label+percent", textfont=dict(size=11, color="#E7EAF6"),
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


def chase_bar(pct, left_label, right_label, color_from="#7C8CFF", color_to="#FF8FA3", runner="🐇"):
    pct = max(0.0, min(1.0, pct))
    left_pos = f"calc({pct*100:.1f}% - 12px)"
    if pct <= 0.02:
        left_pos = "2px"
    if pct >= 0.98:
        left_pos = "calc(100% - 22px)"
    st.markdown(f"""
        <div class="chase-wrap">
            <div class="chase-track">
                <div class="chase-fill" style="width:{pct*100:.1f}%; background:linear-gradient(90deg,{color_from},{color_to});"></div>
                <div class="chase-runner" style="left:{left_pos};">{runner}</div>
            </div>
            <div class="chase-labels"><span>{left_label}</span><span>{right_label}</span></div>
        </div>
    """, unsafe_allow_html=True)


def render_orderbook(asset_id, market):
    ob = market.get("orderbook", {}).get(asset_id)
    price = market["prices"][asset_id]
    if not ob:
        st.caption("호가 정보를 불러오는 중...")
        return
    max_qty = max(ob["max_qty"], 1)
    rows = []
    for lvl in ob["asks"]:
        w = int(lvl["qty"] / max_qty * 100)
        rows.append(f"""<div class="ob-row ask"><div class="ob-bar" style="width:{w}%;"></div>
            <span>{lvl['price']:,}</span><span>{lvl['qty']:,}주</span></div>""")
    rows.append(f'<div class="ob-cur">현재가 {price:,.0f}원</div>')
    for lvl in ob["bids"]:
        w = int(lvl["qty"] / max_qty * 100)
        rows.append(f"""<div class="ob-row bid"><div class="ob-bar" style="width:{w}%;"></div>
            <span>{lvl['price']:,}</span><span>{lvl['qty']:,}주</span></div>""")
    st.markdown(f'<div class="ob-wrap">{"".join(rows)}</div>'
                f'<div class="ob-caption">모의 호가창 · 시세 갱신마다(약 15초) 새로 생성됩니다</div>',
                unsafe_allow_html=True)


# ── 대시보드 ──────────────────────────────────────────────────────────────
TIPS = [
    "💡 소비를 기록하는 것만으로도 절약 효과가 생겨요.",
    "💡 자산은 한 곳에 몰지 않고 나누는 게 기본이에요.",
    "💡 비상금은 투자보다 먼저 챙기는 게 안전해요.",
    "💡 작은 습관이 쌓이면 레벨이 오릅니다.",
    "💡 목표 금액을 정하면 저축이 게임처럼 재밌어져요.",
    "💡 손실이 무서울수록 분산 투자가 힘이 됩니다.",
]


def render_dashboard(user, market):
    nw = get_net_worth(user, market)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("순자산", format_korean_money(nw))
    c2.metric("현금", format_korean_money(user.get("cash", 0)))
    invest_val = sum(pos["qty"] * market["prices"].get(aid, 0) for aid, pos in user.get("portfolio", {}).items())
    c3.metric("투자 평가액", format_korean_money(invest_val))
    c4.metric("저축액", format_korean_money(total_saving_amount(user)))

    month_start = time.mktime(time.strptime(time.strftime("%Y-%m-01"), "%Y-%m-%d"))
    month_expense = sum(t["amount"] for t in user["tx_log"]
                         if t.get("kind") == "expense" and t.get("ts", 0) >= month_start)
    n_badges = len(user.get("badges", []))
    n_held = len([1 for pos in user.get("portfolio", {}).values() if pos.get("qty", 0) > 0])
    g = goal_progress(user)

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("이번 달 지출", format_korean_money(month_expense))
    c6.metric("획득 뱃지", f"{n_badges} / {len(BADGES)}")
    c7.metric("보유 종목 수", f"{n_held}개")
    c8.metric("목표 달성률", f"{g['pct']*100:.0f}%" if g else "목표 없음")

    nw_fig = net_worth_chart(user)
    if nw_fig:
        st.write("")
        st.caption("📈 순자산 추이 (세션 내)")
        st.plotly_chart(nw_fig, use_container_width=True, config={"displayModeBar": False})

    tip = TIPS[int(time.strftime("%j")) % len(TIPS)]
    st.info(tip)

    st.write("")
    col_l, col_r = st.columns([3, 2])
    with col_l:
        if user.get("portfolio"):
            st.subheader("보유 포트폴리오")
            rows = []
            for aid, pos in user["portfolio"].items():
                if pos.get("qty", 0) <= 0:
                    continue
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
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("아직 투자한 자산이 없어요. '모의투자' 탭에서 시작해보세요.")

        if user.get("tx_log"):
            st.subheader("최근 활동")
            for t in user["tx_log"][:5]:
                kind_label = {"expense": "🧾 지출", "invest_buy": "📈 매수", "invest_sell": "📉 매도",
                              "savings_open": "🏦 예적금 가입", "savings_deposit": "💰 추가 납입"}.get(t.get("kind"), t.get("kind"))
                st.caption(f"{relative_time(t.get('ts', time.time()))} · {kind_label}")
    with col_r:
        st.subheader("자산 배분")
        fig = portfolio_donut(user, market)
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("자산이 쌓이면 여기에 배분 차트가 표시돼요.")

        earned = [b for b in BADGES if b["id"] in user.get("badges", [])]
        if earned:
            st.caption(f"🏅 최근 획득 뱃지 ({len(earned)}개 보유 중)")
            recent = earned[-3:][::-1]
            st.write(" ".join(f"{b['icon']} {b['name']}" for b in recent))


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
    asset_id = st.selectbox("🔎 종목 선택", [a["id"] for a in ASSET_CONFIG],
                             format_func=lambda x: f"{ASSET_BY_ID[x]['icon']} {ASSET_BY_ID[x]['name']} ({ASSET_BY_ID[x]['type']})")
    price = market["prices"][asset_id]

    c_chart, c_ob, c_trade = st.columns([2.4, 1.6, 1.7])

    with c_chart:
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

    with c_ob:
        st.markdown("**📖 실시간 호가창**")
        render_orderbook(asset_id, market)

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
                log_tx(user, {"kind": "invest_buy", "asset": asset_id, "qty": buy_qty, "price": price})
                _persist(user)
                st.success(f"{buy_qty}주 매수 완료")
                st.rerun()

        own_qty = user["portfolio"].get(asset_id, {}).get("qty", 0)
        sell_qty = st.number_input(f"매도 수량 (보유 {own_qty})", min_value=1, value=1, key="sell_qty")
        if st.button("매도", use_container_width=True):
            if own_qty < sell_qty:
                st.error("보유 수량이 부족합니다.")
            else:
                avg_price = user["portfolio"][asset_id]["avg_price"]
                pnl = (price - avg_price) * sell_qty
                pnl_pct = (price / avg_price - 1) * 100 if avg_price else 0
                user["cash"] += sell_qty * price
                user["portfolio"][asset_id]["qty"] -= sell_qty
                if user["portfolio"][asset_id]["qty"] == 0:
                    del user["portfolio"][asset_id]
                log_tx(user, {"kind": "invest_sell", "asset": asset_id, "qty": sell_qty, "price": price,
                               "pnl": pnl, "pnl_pct": pnl_pct})
                _persist(user)
                st.success(f"{sell_qty}주 매도 완료 (손익 {format_korean_money(pnl)})")
                st.rerun()

        st.divider()
        st.markdown("**🌍 전체 시장 뉴스**")
        for n in market.get("news", [])[:5]:
            st.markdown(f"""<div class="news-item">
                <div class="n-time">{time.strftime('%H:%M', time.localtime(n['ts']))} · {ASSET_BY_ID.get(n['asset'],{}).get('name','')}</div>
                <div class="n-text">{n['text']}</div></div>""", unsafe_allow_html=True)


# ── 가계부 ────────────────────────────────────────────────────────────────
def render_expense(user):
    st.markdown("### 🧾 오늘 뭐 썼어요?")
    st.caption("카테고리를 톡 눌러서 골라주세요")

    if "exp_cat" not in st.session_state:
        st.session_state.exp_cat = EXPENSE_CATEGORIES[0]["id"]

    cols = st.columns(len(EXPENSE_CATEGORIES))
    for i, c in enumerate(EXPENSE_CATEGORIES):
        with cols[i]:
            active = st.session_state.exp_cat == c["id"]
            st.markdown(f'<div class="{"cat-pill-active" if active else ""}">', unsafe_allow_html=True)
            if st.button(f"{c['icon']}\n{c['name']}", key=f"catbtn_{c['id']}", use_container_width=True):
                st.session_state.exp_cat = c["id"]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    sel = CAT_BY_ID[st.session_state.exp_cat]
    with st.container(border=True):
        st.write(f"선택한 카테고리: **{sel['icon']} {sel['name']}**")
        c1, c2 = st.columns([1, 2])
        with c1:
            amount = st.number_input("금액(원)", min_value=0, step=1000, value=10000)
        with c2:
            memo = st.text_input("메모", placeholder="예: 친구랑 점심 😋")
        if st.button("💾 기록하기", type="primary", use_container_width=True):
            if amount <= 0 or user["cash"] < amount:
                st.error("금액을 확인해주세요. (현금 부족 시 기록 불가)")
            else:
                user["cash"] -= amount
                log_tx(user, {"kind": "expense", "category": sel["id"], "amount": amount, "memo": memo})
                _persist(user)
                st.success("기록 완료! 오늘도 한 걸음 레벨업 🌱")
                st.rerun()

    st.divider()
    tx = [t for t in user["tx_log"] if t.get("kind") == "expense"]
    if not tx:
        st.info("아직 기록된 지출이 없어요. 위에서 첫 기록을 남겨보세요!")
        return

    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.subheader("최근 지출 내역")
        for t in tx[:12]:
            c = CAT_BY_ID[t["category"]]
            st.markdown(f"""
                <div class="exp-card" style="--accent:{c['color']}">
                    <div class="exp-icon">{c['icon']}</div>
                    <div class="exp-main">
                        <div class="exp-cat">{c['name']}</div>
                        <div class="exp-memo">{t.get('memo') or '메모 없음'}</div>
                        <div class="exp-time">{relative_time(t['ts'])}</div>
                    </div>
                    <div class="exp-amt">-{format_korean_money(t['amount'])}</div>
                </div>""", unsafe_allow_html=True)

        st.subheader("또래 평균 대비 소비 비중")
        st.caption("20~30대 1인가구 평균 소비 비중 대비 내 소비 비중 (통계청 가계동향조사 기반 추정치)")
        cat_sum = {}
        for t in tx:
            name = CAT_BY_ID[t["category"]]["name"]
            cat_sum[name] = cat_sum.get(name, 0) + t["amount"]
        total = sum(cat_sum.values()) or 1
        for name, amt in sorted(cat_sum.items(), key=lambda x: -x[1]):
            my_ratio = amt / total
            bench = BENCHMARK_SPENDING_RATIO.get(name, 0.1)
            diff = (my_ratio - bench) * 100
            st.caption(f"{name} · 나 {my_ratio*100:.1f}% vs 또래 {bench*100:.1f}% ({diff:+.1f}%p)")
            st.progress(min(1.0, my_ratio))
    with col_r:
        st.subheader("카테고리별 비중")
        fig = go.Figure(go.Pie(labels=list(cat_sum.keys()), values=list(cat_sum.values()), hole=0.55,
                                marker=dict(colors=[CAT_BY_ID[c["id"]]["color"] for c in EXPENSE_CATEGORIES
                                                     if c["name"] in cat_sum])))
        fig.update_layout(**PLOTLY_DARK, height=280, showlegend=True, legend=dict(font=dict(size=10)))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── 목표 저축 (대표 목표 1개, 저축 총액 기준 추적) ─────────────────────────────
def render_goals(user):
    st.markdown("### 🎯 목표 저축")
    st.caption("목표를 정하면 예/적금 총액 기준으로 달성률을 쫓아가듯 추적해드려요.")

    g = goal_progress(user)
    if g:
        st.markdown(f"""<div class="goal-hero">
            <div class="g-name">🏁 {g['name']}</div>
            <div class="g-sub">{format_korean_money(g['current'])} / {format_korean_money(g['target'])}</div>
            </div>""", unsafe_allow_html=True)
        chase_bar(g["pct"], f"{g['pct']*100:.1f}% 달성", format_korean_money(g["target"] - g["current"]) + " 남음"
                  if g["pct"] < 1 else "목표 달성! 🎉", runner="🐢" if g["pct"] < 1 else "🏆")
        if g["pct"] >= 1.0:
            if award_badge(user, "goal_reached"):
                st.balloons()
            st.success("🎉 목표를 달성했어요! 새로운 목표를 세워볼까요?")
        st.divider()

    with st.form("goal_form"):
        st.write("✨ 새 목표 설정하기" if not g else "✏️ 목표 다시 설정하기")
        name = st.text_input("목표 이름", placeholder="예: 비상금 500만원 모으기, 유럽여행 자금")
        target = st.number_input("목표 금액(원)", min_value=10000, step=100000, value=5_000_000)
        submitted = st.form_submit_button("목표 설정", type="primary")
        if submitted:
            if not name.strip():
                st.error("목표 이름을 입력해주세요.")
            else:
                set_goal(user, name.strip(), target)
                _persist(user)
                st.success("목표가 설정되었어요! 예/적금 탭에서 저축을 시작해보세요 🚀")
                st.rerun()


# ── 예/적금 (이름·기간·목표금액을 자유 입력해 나만의 상품 생성) ─────────────────
def render_savings(user):
    st.markdown("### 🏦 나만의 예/적금 만들기")
    st.caption("이름, 시작일, 기간, 목표금액까지 전부 자유롭게 정하고, 진행 바가 쫓아가는 걸 지켜보세요.")

    with st.expander("➕ 새 예/적금 개설하기", expanded=not user.get("savings")):
        preset_names = ["직접 입력"] + [p["name"] for p in SAVINGS_PRODUCTS]
        preset_choice = st.selectbox("추천 템플릿에서 시작하기 (선택)", preset_names)
        preset = next((p for p in SAVINGS_PRODUCTS if p["name"] == preset_choice), None)

        with st.form("saving_form"):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("상품 이름", value=(preset["name"] if preset else ""),
                                      placeholder="예: 내맘대로 여행적금")
                start = st.date_input("시작일", value=date.today())
                months = st.number_input("기간(개월, 0=기간 없음)", min_value=0, max_value=120,
                                          value=(preset["months"] if preset else 12))
            with c2:
                target_amount = st.number_input("목표 금액(원, 0=목표 없음)", min_value=0, step=100000,
                                                  value=3_000_000)
                rate = st.number_input("연 이자율(%, 선택)", min_value=0.0, max_value=20.0, step=0.1,
                                        value=(preset["rate"] * 100 if preset else 3.0))
                initial = st.number_input("첫 납입액(원)", min_value=0, step=10000, value=100000)
            submitted = st.form_submit_button("🌱 개설하기", type="primary", use_container_width=True)
            if submitted:
                if not name.strip():
                    st.error("상품 이름을 입력해주세요.")
                elif user["cash"] < initial:
                    st.error("현금이 부족합니다.")
                else:
                    icon = preset["icon"] if preset else "🏦"
                    s = create_saving(name.strip(), start.isoformat(), int(months), int(target_amount),
                                       rate / 100, int(initial), icon)
                    user["cash"] -= initial
                    user["savings"].append(s)
                    log_tx(user, {"kind": "savings_open", "name": s["name"], "amount": initial})
                    _persist(user)
                    st.success("개설 완료! 꾸준히 납입하면서 쫓아가봐요 🐇")
                    st.rerun()

    if not user.get("savings"):
        st.info("아직 개설한 예/적금이 없어요. 위에서 첫 상품을 만들어보세요.")
        return

    st.divider()
    st.subheader(f"내 예/적금 ({len(user['savings'])}개) · 총 {format_korean_money(total_saving_amount(user))}")

    for s in user["savings"]:
        prog = saving_progress(s)
        with st.container():
            chips = ""
            if prog["matured"]:
                chips += '<span class="sv-chip done">✅ 만기</span>'
            else:
                chips += '<span class="sv-chip live">⏳ 진행중</span>'
            st.markdown(f"""<div class="sv-card">
                <div class="sv-title">{s.get('icon','🏦')} {s['name']} {chips}</div>
                <div class="sv-sub">시작일 {s['start']}{' · 만기 ' + s['end'] if s.get('end') else ' · 기간 없음(자유적립)'}</div>
                </div>""", unsafe_allow_html=True)

            if prog["time_pct"] is not None:
                d_label = f"D-{prog['days_left']}" if prog["days_left"] and prog["days_left"] > 0 else "만기 도달"
                chase_bar(prog["time_pct"], f"기간 진행 {prog['time_pct']*100:.0f}%", d_label,
                          color_from="#4C8DFF", color_to="#7EE7FF", runner="🚗")
            if prog["amount_pct"] is not None:
                remain = max(0, s["target_amount"] - s["amount"])
                chase_bar(prog["amount_pct"], f"{format_korean_money(s['amount'])} 납입",
                          f"목표까지 {format_korean_money(remain)}" if remain > 0 else "목표 금액 달성! 🎉",
                          color_from="#7C8CFF", color_to="#FF8FA3", runner="🐇")

            dc1, dc2, dc3 = st.columns([2, 1, 1])
            with dc1:
                add_amt = st.number_input("추가 납입액", min_value=0, step=10000, value=50000,
                                           key=f"add_{s['id']}", label_visibility="collapsed")
            with dc2:
                if st.button("💰 추가 납입", key=f"depbtn_{s['id']}", use_container_width=True):
                    if add_amt <= 0 or user["cash"] < add_amt:
                        st.error("금액을 확인해주세요.")
                    else:
                        user["cash"] -= add_amt
                        s["amount"] += add_amt
                        log_tx(user, {"kind": "savings_deposit", "name": s["name"], "amount": add_amt})
                        _persist(user)
                        st.rerun()
            with dc3:
                if st.button("🔓 해지(환급)", key=f"closebtn_{s['id']}", use_container_width=True):
                    user["cash"] += s["amount"]
                    log_tx(user, {"kind": "savings_close", "name": s["name"], "amount": s["amount"]})
                    user["savings"] = [x for x in user["savings"] if x["id"] != s["id"]]
                    _persist(user)
                    st.rerun()
            st.write("")


# ── 뱃지 / 레벨 ───────────────────────────────────────────────────────────
def render_badges(user):
    level, pct, next_ceil = xp_progress(user["xp"])
    st.subheader(f"🏅 레벨 {level}")
    st.progress(pct, text=f"XP {user['xp']} / {next_ceil}")
    st.caption(f"확률형 아이템이 아닌, 조건을 채우면 100% 지급되는 성취 배지입니다. ({len(user['badges'])} / {len(BADGES)} 개 획득)")

    cols = st.columns(6)
    for i, b in enumerate(BADGES):
        earned = b["id"] in user["badges"]
        with cols[i % 6]:
            cls = "earned" if earned else "locked"
            st.markdown(f"""<div class="badge-card {cls}">
                <div class="b-icon">{b['icon'] if earned else '🔒'}</div>
                <div class="b-name">{b['name']}</div>
                <div class="b-desc">{b['desc']}</div>
                <div class="b-xp">+{b['xp']} XP</div>
                </div>""", unsafe_allow_html=True)


# ── 온보딩 (투자성향 진단) ─────────────────────────────────────────────────
def render_onboarding(user):
    st.subheader("🧭 투자성향 진단")
    st.caption(f"{len(ONBOARDING_QUESTIONS)}개 질문에 답하면 AI가 소득·비상금·부채까지 종합해 투자성향을 분석해드려요.")

    if user.get("risk_profile"):
        rp = user["risk_profile"]
        with st.container(border=True):
            if rp.get("hype_line"):
                st.markdown(f"#### {rp['hype_line']}")
            st.markdown(f"### 당신의 투자성향: **{rp.get('profile_name','')}**")
            st.write(rp.get("description", ""))
            alloc = rp.get("recommended_allocation", {})
            if alloc:
                fig = go.Figure(go.Pie(labels=list(alloc.keys()), values=list(alloc.values()), hole=0.55,
                                        marker=dict(colors=["#4C8DFF", "#66BB6A", "#FFB74D"])))
                fig.update_layout(**PLOTLY_DARK, height=260, showlegend=True)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            if rp.get("caution"):
                st.warning(rp["caution"])
        if st.button("다시 진단받기"):
            user["risk_profile"] = None
            _persist(user)
            st.rerun()
        return

    answers = {}
    with st.form("onboarding_form"):
        for q in ONBOARDING_QUESTIONS:
            choice = st.radio(q["q"], [o["label"] for o in q["options"]], key=f"onb_{q['id']}")
            answers[q["id"]] = next(o for o in q["options"] if o["label"] == choice)
        submitted = st.form_submit_button("진단 받기", type="primary")
        if submitted:
            payload = [{"q": q["q"], "answer": answers[q["id"]]["label"], "score": answers[q["id"]]["score"]}
                       for q in ONBOARDING_QUESTIONS]
            with st.spinner("AI가 투자성향을 분석하는 중..."):
                result = get_risk_profile(payload)
            user["risk_profile"] = result
            _persist(user)
            st.rerun()


# ── AI 코치 ───────────────────────────────────────────────────────────────
def render_ai_coach(user, market):
    st.markdown("## 🤖 AI 금융 코치")
    st.caption("최근 소비·투자·저축 데이터를 바탕으로 Gemini 기반 코치가 당신만을 위한 진단을 내려드립니다.")

    if st.button("⚡ 코치 소환하기", type="primary", use_container_width=True):
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

        savings_total = total_saving_amount(user)

        with st.status("코치를 소환하는 중...", expanded=True) as status:
            st.write("📡 소비·투자·저축 데이터 수집 중...")
            time.sleep(0.4)
            st.write("🧠 패턴 분석 중...")
            time.sleep(0.4)
            result = get_financial_diagnosis(spending, portfolio_summary, savings_total, user.get("cash", 0))
            st.write("✨ 인사이트 정리 중...")
            time.sleep(0.3)
            status.update(label="진단 완료!", state="complete", expanded=False)

        st.session_state["ai_result"] = result
        user["ai_coach_count"] = user.get("ai_coach_count", 0) + 1
        if award_badge(user, "ai_first"):
            st.toast("🏅 뱃지 획득: AI와 첫 상담", icon="🎉")
        _persist(user)

    result = st.session_state.get("ai_result")
    if result:
        risk_cls = {"낮음": "risk-low", "보통": "risk-mid", "높음": "risk-high"}.get(result.get("risk_level"), "risk-mid")
        hype = result.get("hype_line", "")
        st.markdown(f"""
            <div class="coach-card">
                {f'<div class="coach-hype">{hype}</div>' if hype else ''}
                <div class="coach-summary">{result.get('summary','')}</div>
                <span class="risk-chip {risk_cls}">리스크 수준 · {result.get('risk_level','-')}</span>
            </div>
        """, unsafe_allow_html=True)
        st.write("")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**💸 소비 분석**")
            st.write(result.get("spending_insight", ""))
        with c2:
            st.markdown("**📈 투자 분석**")
            st.write(result.get("investing_insight", ""))
        if result.get("action_items"):
            st.markdown("**✅ 추천 행동**")
            for item in result["action_items"]:
                st.write(f"- {item}")


def _make_uid(name: str, birth_year: int) -> str:
    slug = "".join(ch for ch in name.strip().lower() if ch.isalnum())
    return f"{slug}_{birth_year}"


def render_signup_gate():
    st.markdown("""<div class="ml-hero">
        <h1>💡 머니레벨업</h1>
        <p>사회초년생을 위한 AI 소비·투자 코칭 모의 서비스</p>
        </div>""", unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("시작하기 전에")
        if db_available():
            st.caption("계정/비밀번호 없이, 이름과 출생연도만 입력하면 돼요. 같은 이름+출생연도로 다시 오시면 이어서 할 수 있어요.")
        else:
            st.caption("⚠️ 현재 저장소(DB)가 연결되지 않아 이번 방문 동안만 데이터가 유지돼요.")
        with st.form("signup_form"):
            name = st.text_input("이름 (또는 닉네임)", placeholder="예: 김효민")
            birth_year = st.number_input("출생연도", min_value=1950, max_value=2015, value=2000, step=1)
            submitted = st.form_submit_button("시작하기", type="primary", use_container_width=True)
            if submitted:
                if not name.strip():
                    st.error("이름을 입력해주세요.")
                else:
                    uid = _make_uid(name, int(birth_year))
                    st.session_state.profile = {"name": name.strip(), "birth_year": int(birth_year), "uid": uid}
                    st.rerun()


# ── 메인 ──────────────────────────────────────────────────────────────────
def main():
    st.markdown(CSS, unsafe_allow_html=True)

    if "profile" not in st.session_state:
        render_signup_gate()
        return

    st_autorefresh(interval=15_000, key="market_tick")

    profile = st.session_state.profile
    uid = profile["uid"]
    user = get_user(uid)
    market = tick_market()
    record_net_worth_point(user, market)
    newly = check_habit_badges(user, market)
    for bid in newly:
        st.toast(f"🏅 뱃지 획득: {BADGE_BY_ID[bid]['name']}", icon="🎉")

    age = time.localtime().tm_year - profile["birth_year"] + 1  # 한국식 나이

    with st.sidebar:
        st.write(f"👋 **{profile['name']}**님 ({age}세)")
        if db_available():
            st.caption("데이터가 저장돼요 — 같은 이름+출생연도로 다시 오면 이어할 수 있어요.")
        else:
            st.caption("⚠️ DB 미연결 — 이번 방문 동안만 데이터가 유지돼요.")
        level, pct, next_ceil = xp_progress(user["xp"])
        st.markdown(f"<span class='level-badge'>⭐ 레벨 {level} · XP {user['xp']}</span>", unsafe_allow_html=True)
        st.progress(pct)
        st.caption(f"🏅 뱃지 {len(user.get('badges', []))} / {len(BADGES)}개 보유")
        if st.button("🔄 처음부터 다시 시작"):
            save_user(uid, default_user())  # 저장된 기록도 함께 초기화
            for k in ("user", "market", "ai_result", "profile"):
                st.session_state.pop(k, None)
            st.rerun()
        st.divider()
        st.caption(f"시작 자금: {format_korean_money(STARTING_CASH)}")
        st.caption("실제 금전 거래가 없는 교육용 시뮬레이션입니다.")

    st.markdown(f"""<div class="ml-hero">
        <h1>💡 머니레벨업</h1>
        <p>{profile['name']}님, 오늘도 한 걸음 레벨업 해봐요</p>
        </div>""", unsafe_allow_html=True)

    render_news_ticker(market)

    tabs = st.tabs(["📊 대시보드", "🧭 투자성향", "📈 모의투자", "🧾 가계부",
                    "🎯 목표저축", "🏦 예/적금", "🤖 AI 코치", "🏅 뱃지"])
    with tabs[0]:
        render_dashboard(user, market)
    with tabs[1]:
        render_onboarding(user)
    with tabs[2]:
        render_invest(user, market)
    with tabs[3]:
        render_expense(user)
    with tabs[4]:
        render_goals(user)
    with tabs[5]:
        render_savings(user)
    with tabs[6]:
        render_ai_coach(user, market)
    with tabs[7]:
        render_badges(user)

    _persist(user)  # 뱃지/XP/순자산 추이 등 명시적 rerun 없이 바뀐 값도 매 실행마다 저장


if __name__ == "__main__":
    main()
