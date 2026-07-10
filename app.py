# app.py — 머니레벨업: 사회초년생을 위한 AI 금융 코칭 모의투자 앱
import time
from datetime import date

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

from utils.config import (
    ASSET_CONFIG, EXPENSE_CATEGORIES, INCOME_CATEGORIES, SAVINGS_PRODUCTS,
    STARTING_MOCK_CASH, STARTING_REAL_CASH,
    ONBOARDING_QUESTIONS, BADGES, BENCHMARK_SPENDING_RATIO,
)
from utils.core import (
    get_user, save_user, default_user, log_tx, delete_tx, add_income, adjust_balance,
    get_net_worth, real_net_worth, mock_portfolio_value, mock_total_value,
    get_market, tick_market, format_korean_money,
    get_level, xp_progress, check_habit_badges, award_badge, BADGE_BY_ID,
    set_goal, goal_progress, record_net_worth_point,
    create_saving, saving_progress, total_saving_amount,
    financial_health_score, predict_next_month_expense,
)
from utils.ai_coach import get_financial_diagnosis, get_risk_profile, get_full_report, chat_with_coach
from utils.database import db_available

st.set_page_config(page_title="머니레벨업 | AI 금융 코치", page_icon="💡", layout="wide")

ASSET_BY_ID = {a["id"]: a for a in ASSET_CONFIG}
CAT_BY_ID = {c["id"]: c for c in EXPENSE_CATEGORIES}
INCOME_CAT_BY_ID = {c["id"]: c for c in INCOME_CATEGORIES}


def _persist(user):
    """현재 유저 데이터를 DB에 저장하고, 저장 성공 여부와 시각을 세션에 기록한다 (사이드바 상태 표시용)."""
    profile = st.session_state.get("profile")
    if not profile:
        return
    ok = save_user(profile["uid"], user)
    st.session_state["_last_save_ok"] = ok
    st.session_state["_last_save_ts"] = time.time()


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
    font=dict(color="#3C4A40", family="Noto Sans KR, sans-serif"),
    margin=dict(l=10, r=10, t=10, b=10),
)

UP_COLOR, DOWN_COLOR = "#B8442F", "#2F5D8A"      # 국내 시세 관행: 상승=빨강, 하락=파랑
GAIN_COLOR, LOSS_COLOR = "#0E7C5A", "#B8442F"     # 순자산 추이: 늘면 초록, 줄면 빨강
PIE_COLORS = ["#0E7C5A", "#B8862F", "#2F5D8A", "#B8442F", "#6B8F71", "#8C6D46", "#4C7A6B", "#9AA5C0"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@600;700;900&family=Noto+Sans+KR:wght@400;500;700;900&family=IBM+Plex+Mono:wght@500;600;700&display=swap');

:root {
    --paper: #F3F6EF; --paper-2: #FFFDF8; --ink: #1C2B24; --ink-soft: #5B6B60;
    --line: #DCE6D8; --brand: #0E7C5A; --brand-deep: #0A5A40; --brand-soft: #E4F1EA;
    --gold: #A9791F; --gold-soft: #F6EBD3; --coral: #B8442F; --coral-soft: #F8E7E2;
    --navy: #2F3F5C; --navy-soft: #E6EAF2;
}

.stApp {
    background:
        linear-gradient(0deg, rgba(14,124,90,0.05) 1px, transparent 1px) 0 0/100% 27px,
        var(--paper);
}
h1, h2, h3, h4 { font-family: 'Noto Serif KR', serif !important; color: var(--ink) !important; letter-spacing: .2px; }
.stMarkdown, .stMarkdown p, .stMarkdown li, label, .stCaption, p, span, div[data-testid="stText"] {
    color: var(--ink); font-family: 'Noto Sans KR', sans-serif;
}
.stApp small, .stCaption, [data-testid="stCaptionContainer"] { color: var(--ink-soft) !important; }
[data-testid="stSidebar"] { background: var(--paper-2); border-right: 1px solid var(--line); }
hr { border-color: var(--line) !important; }

/* 상단 통장 표지 (hero) */
.ml-hero {
    position: relative; overflow: hidden;
    background: linear-gradient(155deg, var(--brand-deep) 0%, #0D3F2E 60%, #0A2E22 100%);
    border-radius: 20px; padding: 26px 30px; margin-bottom: 14px;
    box-shadow: 0 16px 32px -16px rgba(10,58,42,0.55);
}
.ml-hero::before {
    content: ""; position: absolute; inset: 0;
    background: repeating-linear-gradient(115deg, rgba(255,255,255,0.05) 0 2px, transparent 2px 22px);
    pointer-events: none;
}
.ml-hero::after {
    content: ""; position: absolute; inset: 9px; border-radius: 13px;
    border: 1px dashed rgba(244,241,228,0.28); pointer-events: none;
}
.ml-hero .eyebrow {
    position: relative; font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem;
    letter-spacing: 2px; color: #C9A24B; text-transform: uppercase; margin-bottom: 6px;
}
.ml-hero h1 { position: relative; margin: 0; font-size: 1.85rem; color: #F5F1E4 !important; font-weight: 900; }
.ml-hero p  { position: relative; margin: 6px 0 0 0; color: rgba(245,241,228,0.72); font-size: 0.92rem; }

/* 뉴스 티커 */
.ticker-wrap {
    overflow: hidden; white-space: nowrap; display: flex; align-items: center;
    background: var(--paper-2); border: 1px solid var(--line);
    border-radius: 10px; padding: 0; margin-bottom: 16px;
}
.ticker-tag {
    flex-shrink: 0; font-family: 'IBM Plex Mono', monospace; font-size: 0.66rem; font-weight: 700;
    letter-spacing: 1.5px; color: #fff; background: var(--brand); padding: 9px 12px; border-radius: 10px 0 0 10px;
}
.ticker-scroll { overflow: hidden; flex: 1; padding: 9px 0; }
.ticker-inner { display: inline-block; animation: ticker-scroll 28s linear infinite; padding-left: 14px; }
.ticker-inner:hover { animation-play-state: paused; }
@keyframes ticker-scroll { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
.ticker-item { display: inline-flex; align-items: center; gap: 8px; margin-right: 42px; font-size: 0.83rem; color: var(--ink-soft); }
.ticker-item b { color: var(--ink); }

/* 카드형 metric */
div[data-testid="stMetric"] {
    background: var(--paper-2); border: 1px solid var(--line); border-radius: 14px;
    padding: 14px 16px; box-shadow: 0 1px 2px rgba(28,43,36,0.04);
}
div[data-testid="stMetricLabel"] { color: var(--ink-soft) !important; }
div[data-testid="stMetricValue"] { color: var(--ink) !important; font-family: 'IBM Plex Mono', monospace !important; }

/* 자산 카드 (원장 스타일) */
.asset-card {
    background: var(--paper-2); border: 1px solid var(--line); border-radius: 12px;
    padding: 12px 14px; margin-bottom: 6px; transition: border-color .2s, transform .15s;
}
.asset-card:hover { border-color: var(--brand); transform: translateY(-1px); }
.asset-card .a-name { font-size: 0.8rem; color: var(--ink-soft); }
.asset-card .a-price { font-family: 'IBM Plex Mono', monospace; font-size: 1.05rem; color: var(--ink); font-weight: 700; }
.up   { color: var(--coral) !important; font-family: 'IBM Plex Mono', monospace; }
.down { color: var(--navy) !important; font-family: 'IBM Plex Mono', monospace; }

/* 뉴스 카드 */
.news-item { border-left: 3px solid var(--brand); padding: 6px 12px; margin-bottom: 6px;
    background: var(--paper-2); border: 1px solid var(--line); border-left-width: 3px; border-radius: 0 8px 8px 0; }
.news-item .n-time { font-size: 0.72rem; color: var(--ink-soft); font-family: 'IBM Plex Mono', monospace; }
.news-item .n-text { font-size: 0.85rem; color: var(--ink); }

/* 호가창 (원장 테이블) */
.ob-wrap { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; background: var(--paper-2); }
.ob-row { position: relative; display: flex; justify-content: space-between; padding: 5px 12px; font-size: 0.8rem;
    font-family: 'IBM Plex Mono', monospace; overflow: hidden; }
.ob-row.ask { color: var(--navy); } .ob-row.bid { color: var(--coral); }
.ob-bar { position: absolute; right: 0; top: 0; bottom: 0; background: currentColor; opacity: 0.10; }
.ob-row span { position: relative; z-index: 1; }
.ob-cur { text-align: center; padding: 7px; background: var(--gold-soft); font-weight: 700; color: var(--gold);
    font-family: 'IBM Plex Mono', monospace; font-size: 0.86rem;
    border-top: 1px dashed #D8C08A; border-bottom: 1px dashed #D8C08A; letter-spacing: .3px; }
.ob-caption { font-size: 0.7rem; color: var(--ink-soft); text-align: center; padding: 4px 0 0 0; }

/* ── 뱃지: 도장(스탬프) ── */
.stamp-cell { text-align: center; padding: 10px 6px 14px 6px; margin-bottom: 6px; }
.stamp-circle {
    width: 62px; height: 62px; border-radius: 50%; margin: 0 auto 8px auto; position: relative;
    display: flex; align-items: center; justify-content: center;
    border: 2.5px solid var(--line); background: var(--paper-2);
}
.stamp-circle::after {
    content: ""; position: absolute; inset: 5px; border-radius: 50%; border: 1px dashed var(--line);
}
.stamp-circle.earned { border-color: var(--brand); background: var(--brand-soft);
    box-shadow: 0 2px 0 rgba(14,124,90,0.18); }
.stamp-circle.earned::after { border-color: rgba(14,124,90,0.4); }
.stamp-circle.locked { opacity: 0.42; filter: grayscale(1); }
.stamp-icon { font-size: 1.55rem; position: relative; }
.stamp-name { font-family: 'Noto Serif KR', serif; font-weight: 700; font-size: 0.78rem; color: var(--ink); }
.stamp-desc { font-size: 0.66rem; color: var(--ink-soft); margin-top: 2px; min-height: 28px; }
.stamp-xp { font-family: 'IBM Plex Mono', monospace; font-size: 0.63rem; color: var(--gold); margin-top: 3px; }

/* 레벨 배지 */
.level-badge { display:inline-flex; align-items:center; gap:8px; background: var(--paper-2); border:1px solid var(--gold);
    border-radius: 999px; padding: 6px 14px; font-size: 0.82rem; color: var(--ink); font-family:'IBM Plex Mono',monospace; }

/* 온보딩 카드 */
.onb-card { background: var(--paper-2); border:1px solid var(--line); border-radius:16px; padding:20px; margin-bottom:14px; }

/* ── 가계부: 카테고리 선택 pill ── */
.stButton > button { border-radius: 10px !important; }
.cat-pill-active button {
    background: var(--brand) !important; border: 1px solid var(--brand-deep) !important;
    color: white !important; font-weight: 700 !important; box-shadow: 0 3px 0 var(--brand-deep) !important;
}

/* 지출 카드 (원장 줄 스타일) */
.exp-card {
    display:flex; align-items:center; gap:12px;
    background: var(--paper-2); border: 1px solid var(--line); border-left: 4px solid var(--accent, #7C8CFF);
    border-radius: 12px; padding: 10px 14px; margin-bottom: 8px; box-shadow: 0 1px 2px rgba(28,43,36,0.04);
}
.exp-card .exp-icon { font-size: 1.4rem; }
.exp-card .exp-main { flex: 1; }
.exp-card .exp-cat { font-size: 0.78rem; color: var(--ink-soft); }
.exp-card .exp-memo { font-size: 0.85rem; color: var(--ink); font-weight: 600; }
.exp-card .exp-amt { font-family:'IBM Plex Mono',monospace; font-weight:700; color: var(--coral); }
.exp-card .exp-time { font-size: 0.68rem; color: var(--ink-soft); margin-top: 2px; }

/* ── 목표저축 / 예적금 카드 ── */
.goal-hero {
    background: linear-gradient(135deg, var(--brand-soft), var(--paper-2));
    border: 1px solid var(--brand); border-radius: 18px; padding: 20px 22px; margin-bottom: 12px;
}
.goal-hero .g-name { font-family: 'Noto Serif KR', serif; font-size: 1.15rem; font-weight: 800; color: var(--brand-deep); }
.goal-hero .g-sub { font-size: 0.82rem; color: var(--ink-soft); margin-top: 3px; font-family: 'IBM Plex Mono', monospace; }

.sv-card {
    background: var(--paper-2); border: 1px solid var(--line); border-radius: 16px;
    padding: 18px 20px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(28,43,36,0.05);
}
.sv-card .sv-title { font-family: 'Noto Serif KR', serif; font-size: 1.02rem; font-weight: 800; color: var(--ink); }
.sv-card .sv-sub { font-size: 0.75rem; color: var(--ink-soft); margin-top: 3px; margin-bottom: 10px; font-family:'IBM Plex Mono',monospace; }
.sv-chip { display:inline-block; font-size: 0.68rem; padding: 2px 9px; border-radius: 999px; margin-left: 6px; font-family:'Noto Sans KR'; }
.sv-chip.done { background: var(--brand-soft); color: var(--brand-deep); border: 1px solid var(--brand); }
.sv-chip.live { background: var(--gold-soft); color: var(--gold); border: 1px solid var(--gold); }

/* 쫓아가는 성장 진행 바 */
.chase-wrap { margin: 10px 0 4px 0; }
.chase-track { position: relative; height: 18px; background: #EAF0E6; border-radius: 999px;
    border: 1px solid var(--line); overflow: visible; }
.chase-track.time { background-color: #EDF1F7;
    background-image: repeating-linear-gradient(90deg, transparent 0 6px, rgba(47,63,92,0.14) 6px 9px); }
.chase-fill { position: absolute; left:0; top:0; bottom:0; border-radius: 999px; transition: width .7s ease; }
.chase-runner { position: absolute; top: 50%; transform: translateY(-50%); font-size: 1.05rem;
    filter: drop-shadow(0 1px 1px rgba(0,0,0,.25)); transition: left .7s ease; }
.chase-labels { display:flex; justify-content: space-between; font-size: 0.7rem; color: var(--ink-soft);
    margin-top: 5px; font-family: 'IBM Plex Mono', monospace; }

/* ── AI 코치: 코치의 메모 카드 ── */
.coach-card {
    position: relative; border-radius: 16px; padding: 28px 28px 24px 28px; margin-top: 10px;
    background: var(--paper-2); border: 1px solid var(--line);
    box-shadow: 0 12px 26px -16px rgba(28,43,36,0.3);
}
.coach-card::before {
    content: "코치의 메모"; position: absolute; top: -12px; left: 26px;
    background: var(--gold-soft); color: var(--gold); border: 1px solid #D8C08A;
    font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem; letter-spacing: 1px;
    padding: 3px 10px; border-radius: 999px; transform: rotate(-2deg);
}
.coach-hype {
    font-family: 'Noto Serif KR', serif; font-weight: 800; font-size: 1.3rem; color: var(--brand-deep);
    display: inline-block; border-bottom: 2px dashed var(--gold-soft); padding-bottom: 8px; margin-bottom: 10px;
}
.coach-summary { font-size: 1.05rem; font-weight: 700; color: var(--ink); margin-bottom: 10px; }
.risk-chip { display:inline-block; padding: 3px 12px; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }
.risk-low { background: var(--brand-soft); color: var(--brand-deep); border: 1px solid var(--brand); }
.risk-mid { background: var(--gold-soft); color: var(--gold); border: 1px solid #D8C08A; }
.risk-high{ background: var(--coral-soft); color: var(--coral); border: 1px solid #D9A99C; }
</style>
"""


def price_chart(asset_id, market):
    hist = market["history"].get(asset_id, [])
    if len(hist) < 2:
        hist = hist * 2
    up = hist[-1] >= hist[0]
    line_color = UP_COLOR if up else DOWN_COLOR
    fill_color = "rgba(184,68,47,0.08)" if up else "rgba(47,93,138,0.08)"
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
    reals = [h.get("real", h.get("value", 0)) for h in hist]
    mocks = [h.get("mock", 0) for h in hist]
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=reals, mode="lines+markers", name="실제 자금",
                              line=dict(color=GAIN_COLOR, width=2.5), marker=dict(size=4)))
    fig.add_trace(go.Scatter(y=mocks, mode="lines+markers", name="모의투자",
                              line=dict(color="#2F5D8A", width=2.5, dash="dot"), marker=dict(size=4)))
    fig.update_layout(**PLOTLY_DARK, height=200, showlegend=True, legend=dict(font=dict(size=10)))
    fig.update_xaxes(showgrid=False, showticklabels=False)
    fig.update_yaxes(showgrid=False)
    return fig


def mock_portfolio_donut(user, market):
    """모의투자 계좌 배분 (연습용 가상자산만 — 실제 자금과 무관)."""
    labels, values = [], []
    for aid, pos in user.get("portfolio", {}).items():
        val = pos["qty"] * market["prices"].get(aid, 0)
        if val > 0:
            labels.append(ASSET_BY_ID[aid]["name"])
            values.append(val)
    if user.get("mock_cash", 0) > 0:
        labels.append("모의 현금")
        values.append(user["mock_cash"])
    if not values:
        return None
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.62,
        marker=dict(colors=PIE_COLORS),
        textinfo="label+percent", textfont=dict(size=11, color="#1C2B24"),
    ))
    fig.update_layout(**PLOTLY_DARK, height=280, showlegend=False)
    return fig


def real_asset_donut(user):
    """실제 자금 배분 (지갑 잔액 + 예/적금 상품별)."""
    labels, values = [], []
    if user.get("real_cash", 0) > 0:
        labels.append("지갑 잔액")
        values.append(user["real_cash"])
    for s in user.get("savings", []):
        if s.get("amount", 0) > 0:
            labels.append(s["name"])
            values.append(s["amount"])
    if not values:
        return None
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.62,
        marker=dict(colors=PIE_COLORS),
        textinfo="label+percent", textfont=dict(size=11, color="#1C2B24"),
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
    st.markdown(f"""<div class="ticker-wrap">
        <div class="ticker-tag">NEWS</div>
        <div class="ticker-scroll"><div class="ticker-inner">{html}{html}</div></div>
        </div>""", unsafe_allow_html=True)


def chase_bar(pct, left_label, right_label, theme="growth"):
    """theme='growth': 저축/목표 금액 진행률 (새싹 → 나무로 자라남) / theme='time': 기간 진행률 (걸어서 만기까지)"""
    pct = max(0.0, min(1.0, pct))
    left_pos = f"calc({pct*100:.1f}% - 11px)"
    if pct <= 0.02:
        left_pos = "2px"
    if pct >= 0.98:
        left_pos = "calc(100% - 20px)"

    if theme == "time":
        color_from, color_to = "#4C6690", "#2F3F5C"
        runner = "🏁" if pct >= 1.0 else "🚶"
        track_cls = "chase-track time"
    else:
        color_from, color_to = "#3FA179", "#0A5A40"
        if pct >= 1.0:
            runner = "🌳"
        elif pct >= 0.6:
            runner = "🌿"
        elif pct >= 0.25:
            runner = "🌱"
        else:
            runner = "🌰"
        track_cls = "chase-track"

    st.markdown(f"""
        <div class="chase-wrap">
            <div class="{track_cls}">
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
    real_nw = real_net_worth(user)
    mock_val = mock_total_value(user, market)
    invest_val = mock_portfolio_value(user, market)

    st.markdown("#### 💰 실제 자금 (내가 진짜 가진 돈)")
    r1, r2, r3 = st.columns(3)
    r1.metric("실제 순자산", format_korean_money(real_nw))
    r2.metric("지갑 잔액", format_korean_money(user.get("real_cash", 0)))
    r3.metric("저축액", format_korean_money(total_saving_amount(user)))

    st.write("")
    st.markdown("#### 🧪 모의투자 (연습용, 실제 자금 아님)")
    m1, m2, m3 = st.columns(3)
    m1.metric("모의투자 계좌 총액", format_korean_money(mock_val))
    m2.metric("모의 현금", format_korean_money(user.get("mock_cash", 0)))
    m3.metric("투자 평가액", format_korean_money(invest_val))

    st.write("")
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

    st.write("")
    fh = financial_health_score(user, market)
    forecast = predict_next_month_expense(user)
    hcol, fcol = st.columns([1, 1])
    with hcol:
        with st.container(border=True):
            st.markdown(f"#### 🩺 재무 건강 점수 · {fh['score']}점 ({fh['grade']}등급)")
            st.progress(min(1.0, fh["score"] / 100))
            st.caption(fh["comment"])
            with st.expander("점수 구성 자세히 보기"):
                for b in fh["breakdown"]:
                    st.write(f"**{b['key']}** — {b['points']}/{b['max']}점")
                    st.caption(b["detail"])
    with fcol:
        with st.container(border=True):
            st.markdown("#### 🔮 다음 달 예상 지출")
            if forecast:
                st.metric("예상 지출액", format_korean_money(forecast["forecast"]))
                if forecast["anomaly"]:
                    st.warning("⚠️ 최근 지출 흐름이 평소보다 크게 늘었어요. 가계부에서 원인을 점검해보세요.")
                if forecast["history"]:
                    hist_df = pd.DataFrame(forecast["history"], columns=["월", "지출액"])
                    st.caption("최근 월별 지출 추이 (가중평균 + 추세로 예측)")
                    st.dataframe(hist_df, use_container_width=True, hide_index=True)
            else:
                st.caption("가계부 기록이 쌓이면 다음 달 지출을 예측해드려요.")

    nw_fig = net_worth_chart(user)
    if nw_fig:
        st.write("")
        st.caption("📈 실제자금 vs 모의투자 추이 (세션 내, 초록=실제자금 · 파랑=모의투자)")
        st.plotly_chart(nw_fig, use_container_width=True, config={"displayModeBar": False})

    tip = TIPS[int(time.strftime("%j")) % len(TIPS)]
    st.info(tip)

    st.write("")
    col_l, col_r = st.columns([3, 2])
    with col_l:
        if user.get("portfolio"):
            st.subheader("보유 포트폴리오 (모의투자)")
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
                kind_label = {"expense": "🧾 지출", "income": "💵 수입", "invest_buy": "📈 매수", "invest_sell": "📉 매도",
                              "savings_open": "🏦 예적금 가입", "savings_deposit": "💰 추가 납입",
                              "savings_close": "🔓 예적금 해지"}.get(t.get("kind"), t.get("kind"))
                st.caption(f"{relative_time(t.get('ts', time.time()))} · {kind_label}")
    with col_r:
        st.subheader("💰 실제 자금 배분")
        fig_real = real_asset_donut(user)
        if fig_real:
            st.plotly_chart(fig_real, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("지갑에 돈을 채우거나 저축을 시작하면 여기에 표시돼요.")

        st.subheader("🧪 모의투자 배분")
        fig_mock = mock_portfolio_donut(user, market)
        if fig_mock:
            st.plotly_chart(fig_mock, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("모의투자를 시작하면 여기에 표시돼요.")

        earned = [b for b in BADGES if b["id"] in user.get("badges", [])]
        if earned:
            st.caption(f"🏅 최근 획득 뱃지 ({len(earned)}개 보유 중)")
            recent = earned[-3:][::-1]
            st.write(" ".join(f"{b['icon']} {b['name']}" for b in recent))


# ── 모의투자 ──────────────────────────────────────────────────────────────
def render_invest(user, market):
    st.caption("⚠️ 실제 시세가 아닌 랜덤워크+뉴스 이벤트 기반 가상 시뮬레이션입니다. (약 15초마다 갱신)")
    st.info(f"🧪 모의투자 잔고: **{format_korean_money(user['mock_cash'])}** — 실제 자금과 완전히 분리된 연습용 가상 머니예요.")

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
            if user["mock_cash"] < cost:
                st.error("모의투자 잔고가 부족합니다. (실제 자금과는 별개예요)")
            else:
                user["mock_cash"] -= cost
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
                user["mock_cash"] += sell_qty * price
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
    bal = user.get("real_cash", 0)
    bal_color = "🟢" if bal >= 0 else "🔴"
    st.markdown(f"### 💰 실제 잔액: {bal_color} {format_korean_money(bal)}")
    if bal < 0:
        st.caption("⚠️ 기록된 지출이 수입보다 많아요. 아래 '수입 추가'에서 채워 넣을 수 있어요.")

    tab_out, tab_in = st.tabs(["🧾 지출 기록", "💵 수입 추가"])

    with tab_out:
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
                if amount <= 0:
                    st.error("금액을 확인해주세요.")
                else:
                    user["real_cash"] = user.get("real_cash", 0) - amount
                    log_tx(user, {"kind": "expense", "category": sel["id"], "amount": amount, "memo": memo})
                    _persist(user)
                    st.success("기록 완료! 오늘도 한 걸음 레벨업 🌱")
                    st.rerun()

    with tab_in:
        st.caption("월급, 용돈, 부수입 등 실제로 들어온 돈을 기록하면 잔액에 바로 반영돼요.")
        with st.container(border=True):
            ic = st.selectbox("수입 종류", [c["id"] for c in INCOME_CATEGORIES],
                               format_func=lambda x: f"{INCOME_CAT_BY_ID[x]['icon']} {INCOME_CAT_BY_ID[x]['name']}")
            c1, c2 = st.columns([1, 2])
            with c1:
                in_amount = st.number_input("금액(원)", min_value=0, step=10000, value=100000, key="income_amt")
            with c2:
                in_memo = st.text_input("메모", placeholder="예: 7월 월급", key="income_memo")
            if st.button("💵 수입 추가하기", type="primary", use_container_width=True):
                if in_amount <= 0:
                    st.error("금액을 확인해주세요.")
                else:
                    add_income(user, ic, in_amount, in_memo)
                    _persist(user)
                    st.success("수입이 추가됐어요!")
                    st.rerun()

    st.divider()
    tx = [t for t in user["tx_log"] if t.get("kind") in ("expense", "income")]
    if not tx:
        st.info("아직 기록된 내역이 없어요. 위에서 첫 기록을 남겨보세요!")
        return

    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.subheader("최근 내역")
        for t in tx[:15]:
            is_income = t.get("kind") == "income"
            if is_income:
                c = INCOME_CAT_BY_ID.get(t.get("category"), {"icon": "💵", "name": "수입", "color": "#0E7C5A"})
                sign, accent = "+", "#0E7C5A"
            else:
                c = CAT_BY_ID[t["category"]]
                sign, accent = "-", c.get("color", "#B8442F")
            row_l, row_r = st.columns([6, 1])
            with row_l:
                st.markdown(f"""
                    <div class="exp-card" style="--accent:{accent}">
                        <div class="exp-icon">{c['icon']}</div>
                        <div class="exp-main">
                            <div class="exp-cat">{c['name']}</div>
                            <div class="exp-memo">{t.get('memo') or '메모 없음'}</div>
                            <div class="exp-time">{relative_time(t['ts'])}</div>
                        </div>
                        <div class="exp-amt">{sign}{format_korean_money(t['amount'])}</div>
                    </div>""", unsafe_allow_html=True)
            with row_r:
                if st.button("🗑️", key=f"del_{t['id']}", help="이 기록 삭제"):
                    delete_tx(user, t["id"])
                    _persist(user)
                    st.rerun()

        expense_tx = [t for t in tx if t.get("kind") == "expense"]
        if expense_tx:
            st.subheader("또래 평균 대비 소비 비중")
            st.caption("20~30대 1인가구 평균 소비 비중 대비 내 소비 비중 (통계청 가계동향조사 기반 추정치)")
            cat_sum = {}
            for t in expense_tx:
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
        expense_tx = [t for t in tx if t.get("kind") == "expense"]
        if expense_tx:
            st.subheader("카테고리별 비중")
            cat_sum = {}
            for t in expense_tx:
                name = CAT_BY_ID[t["category"]]["name"]
                cat_sum[name] = cat_sum.get(name, 0) + t["amount"]
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
                  if g["pct"] < 1 else "목표 달성! 🎉", theme="growth")
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
    st.info(f"💰 현재 지갑 잔액: **{format_korean_money(user.get('real_cash', 0))}** (모의투자와 무관한 실제 자금이에요)")

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
                elif user["real_cash"] < initial:
                    st.error("실제 지갑 잔액이 부족합니다. 가계부 탭에서 수입을 먼저 추가해보세요.")
                else:
                    icon = preset["icon"] if preset else "🏦"
                    s = create_saving(name.strip(), start.isoformat(), int(months), int(target_amount),
                                       rate / 100, int(initial), icon)
                    user["real_cash"] -= initial
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
                chase_bar(prog["time_pct"], f"기간 진행 {prog['time_pct']*100:.0f}%", d_label, theme="time")
            if prog["amount_pct"] is not None:
                remain = max(0, s["target_amount"] - s["amount"])
                chase_bar(prog["amount_pct"], f"{format_korean_money(s['amount'])} 납입",
                          f"목표까지 {format_korean_money(remain)}" if remain > 0 else "목표 금액 달성! 🎉",
                          theme="growth")

            dc1, dc2, dc3 = st.columns([2, 1, 1])
            with dc1:
                add_amt = st.number_input("추가 납입액", min_value=0, step=10000, value=50000,
                                           key=f"add_{s['id']}", label_visibility="collapsed")
            with dc2:
                if st.button("💰 추가 납입", key=f"depbtn_{s['id']}", use_container_width=True):
                    if add_amt <= 0 or user["real_cash"] < add_amt:
                        st.error("금액을 확인해주세요.")
                    else:
                        user["real_cash"] -= add_amt
                        s["amount"] += add_amt
                        log_tx(user, {"kind": "savings_deposit", "name": s["name"], "amount": add_amt})
                        _persist(user)
                        st.rerun()
            with dc3:
                if st.button("🔓 해지(환급)", key=f"closebtn_{s['id']}", use_container_width=True):
                    user["real_cash"] += s["amount"]
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
    ROTATIONS = [-5, 3, -3, 6, -6, 2]
    for i, b in enumerate(BADGES):
        earned = b["id"] in user["badges"]
        with cols[i % 6]:
            cls = "earned" if earned else "locked"
            rot = ROTATIONS[i % len(ROTATIONS)]
            st.markdown(f"""<div class="stamp-cell">
                <div class="stamp-circle {cls}" style="transform: rotate({rot}deg);">
                    <span class="stamp-icon">{b['icon'] if earned else '🔒'}</span>
                </div>
                <div class="stamp-name">{b['name']}</div>
                <div class="stamp-desc">{b['desc']}</div>
                <div class="stamp-xp">+{b['xp']} XP</div>
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
            result = get_financial_diagnosis(spending, portfolio_summary, savings_total, user.get("real_cash", 0))
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

    st.divider()
    st.markdown("### 📄 종합 재무 리포트 (다운로드용)")
    st.caption("재무 건강 점수, 지출 예측, 투자·저축 현황을 하나로 묶은 상세 리포트를 생성해요. 인쇄하거나 저장해서 보관할 수 있어요.")
    if st.button("📄 종합 리포트 생성하기", use_container_width=True):
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

        report_data = {
            "financial_health": financial_health_score(user, market),
            "forecast": predict_next_month_expense(user),
            "spending_by_category": spending,
            "portfolio": portfolio_summary,
            "savings_total": total_saving_amount(user),
            "real_cash": user.get("real_cash", 0),
            "goal": goal_progress(user),
        }
        with st.spinner("리포트를 작성하는 중..."):
            report_md = get_full_report(report_data)
        st.session_state["ai_report_md"] = report_md

    report_md = st.session_state.get("ai_report_md")
    if report_md:
        with st.container(border=True):
            st.markdown(report_md)
        st.download_button("⬇️ 리포트 다운로드 (.md)", data=report_md,
                            file_name=f"머니레벨업_재무리포트_{date.today().isoformat()}.md",
                            mime="text/markdown", use_container_width=True)


# ── AI 상담 (멀티턴 챗봇) ───────────────────────────────────────────────────
def render_ai_chat(user, market):
    st.markdown("## 💬 AI 상담 챗봇")
    st.caption("자유롭게 질문해보세요. 코치가 당신의 최신 가계부·투자·저축 데이터를 참고해 답해드려요.")

    for msg in user.get("chat_history", []):
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.write(msg["text"])

    question = st.chat_input("예: 이번 달 소비 어때? / 지금 포트폴리오 괜찮아?")
    if question:
        user.setdefault("chat_history", []).append({"role": "user", "text": question})
        with st.chat_message("user"):
            st.write(question)

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
        context = {
            "real_cash": user.get("real_cash", 0),
            "savings_total": total_saving_amount(user),
            "spending_by_category": spending,
            "portfolio": portfolio_summary,
            "financial_health_score": financial_health_score(user, market)["score"],
            "risk_profile": (user.get("risk_profile") or {}).get("profile_name"),
        }
        history_payload = [{"role": ("user" if m["role"] == "user" else "model"), "text": m["text"]}
                            for m in user["chat_history"][-10:]]

        with st.chat_message("assistant"):
            with st.spinner("생각하는 중..."):
                answer = chat_with_coach(history_payload, context)
            st.write(answer)
        user["chat_history"].append({"role": "coach", "text": answer})
        user["chat_history"] = user["chat_history"][-40:]
        user["ai_coach_count"] = user.get("ai_coach_count", 0) + 1
        if award_badge(user, "ai_first"):
            st.toast("🏅 뱃지 획득: AI와 첫 상담", icon="🎉")
        _persist(user)

    if user.get("chat_history") and st.button("🧹 대화 초기화"):
        user["chat_history"] = []
        _persist(user)
        st.rerun()


def _make_uid(name: str, birth_year: int) -> str:
    slug = "".join(ch for ch in name.strip().lower() if ch.isalnum())
    return f"{slug}_{birth_year}"


def render_signup_gate():
    st.markdown("""<div class="ml-hero">
        <div class="eyebrow">MONEY PASSBOOK · Lv.1 부터 시작</div>
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
            st.markdown("**💰 이미 갖고 있는 돈이 있나요?** (처음 한 번만 입력하면 돼요, 나중에 사이드바에서 수정 가능)")
            ic1, ic2 = st.columns(2)
            with ic1:
                initial_cash = st.number_input("현재 통장/지갑 잔액 (원)", min_value=0, value=0, step=10_000,
                                                 help="이미 갖고 있는 현금·예금 등 바로 쓸 수 있는 돈")
            with ic2:
                initial_savings = st.number_input("이미 들고 있는 예/적금 총액 (원)", min_value=0, value=0, step=10_000,
                                                    help="가입해둔 적금·예금이 있다면 그 합계를 입력하세요")
            st.caption("둘 다 0으로 두면 기존처럼 0원부터 시작해요. 모의투자 시드머니는 이 설정과 무관하게 별도로 지급됩니다.")
            submitted = st.form_submit_button("시작하기", type="primary", use_container_width=True)
            if submitted:
                if not name.strip():
                    st.error("이름을 입력해주세요.")
                else:
                    uid = _make_uid(name, int(birth_year))
                    st.session_state.profile = {"name": name.strip(), "birth_year": int(birth_year), "uid": uid}
                    st.session_state["_pending_initial_cash"] = int(initial_cash)
                    st.session_state["_pending_initial_savings"] = int(initial_savings)
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
    user = get_user(uid,
                     initial_real_cash=st.session_state.pop("_pending_initial_cash", None),
                     initial_savings=st.session_state.pop("_pending_initial_savings", 0))
    market = tick_market()
    record_net_worth_point(user, market)
    newly = check_habit_badges(user, market)
    for bid in newly:
        st.toast(f"🏅 뱃지 획득: {BADGE_BY_ID[bid]['name']}", icon="🎉")

    age = time.localtime().tm_year - profile["birth_year"] + 1  # 한국식 나이

    with st.sidebar:
        st.write(f"👋 **{profile['name']}**님 ({age}세)")
        if db_available():
            st.caption("✅ 저장소 연결됨 — 같은 이름+출생연도로 다시 오면 오늘까지의 기록이 그대로 이어져요.")
            last_ok = st.session_state.get("_last_save_ok")
            last_ts = st.session_state.get("_last_save_ts")
            if last_ts:
                when = relative_time(last_ts)
                if last_ok:
                    st.caption(f"💾 마지막 저장: {when}")
                else:
                    st.warning(f"⚠️ 마지막 저장 실패 ({when}) — 네트워크나 DB 설정을 확인해주세요.")
        else:
            st.warning("⚠️ DB 미연결 — 이번 방문 동안만 데이터가 유지돼요. secrets에 MONGO_URI를 설정하면 매일 이어서 쓸 수 있어요.")
        level, pct, next_ceil = xp_progress(user["xp"])
        st.markdown(f"<span class='level-badge'>⭐ 레벨 {level} · XP {user['xp']}</span>", unsafe_allow_html=True)
        st.progress(pct)
        st.caption(f"🏅 뱃지 {len(user.get('badges', []))} / {len(BADGES)}개 보유")
        if st.button("🔄 처음부터 다시 시작"):
            save_user(uid, default_user())  # 저장된 기록도 함께 초기화
            for k in ("user", "market", "ai_result", "profile", "_last_save_ok", "_last_save_ts"):
                st.session_state.pop(k, None)
            st.rerun()

        with st.expander("🔧 지갑 잔액 직접 수정"):
            st.caption("깜빡하고 초기 자금을 잘못 넣었거나, 실제 통장 잔액에 맞춰 보정하고 싶을 때 사용하세요.")
            new_balance = st.number_input("현재 지갑 잔액을 이 값으로 맞추기 (원)",
                                           min_value=0, value=int(user.get("real_cash", 0)), step=10_000,
                                           key="_balance_fix_input")
            if st.button("잔액 반영", use_container_width=True):
                diff = adjust_balance(user, new_balance)
                _persist(user)
                if diff == 0:
                    st.toast("변동 없음")
                else:
                    st.toast(f"잔액을 {format_korean_money(new_balance)}로 맞췄어요 ({'+' if diff > 0 else ''}{format_korean_money(diff)})")
                st.rerun()

        st.divider()
        st.caption(f"실제 자금은 시작 시 설정한 금액부터, 모의투자는 {format_korean_money(STARTING_MOCK_CASH)}부터 시작해요.")
        st.caption("모의투자는 실제 금전 거래가 없는 연습용 시뮬레이션입니다.")

    st.markdown(f"""<div class="ml-hero">
        <div class="eyebrow">MONEY PASSBOOK · Lv.{get_level(user['xp'])}</div>
        <h1>💡 머니레벨업</h1>
        <p>{profile['name']}님, 오늘도 한 걸음 레벨업 해봐요</p>
        </div>""", unsafe_allow_html=True)

    render_news_ticker(market)

    tabs = st.tabs(["📊 대시보드", "🧭 투자성향", "📈 모의투자", "🧾 가계부",
                    "🎯 목표저축", "🏦 예/적금", "🤖 AI 코치", "💬 AI 상담", "🏅 뱃지"])
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
        render_ai_chat(user, market)
    with tabs[8]:
        render_badges(user)

    _persist(user)  # 뱃지/XP/순자산 추이 등 명시적 rerun 없이 바뀐 값도 매 실행마다 저장


if __name__ == "__main__":
    main()
