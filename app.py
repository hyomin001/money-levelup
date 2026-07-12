# app.py — 머니레벨업: 사회초년생을 위한 AI 금융 코칭 모의투자 앱
import html
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
    SCAM_SCENARIOS, LEVERAGE_OPTIONS, LEVERAGE_SEED, LEVERAGE_MAINTENANCE_RATIO,
    CRISIS_SCENARIOS, CRISIS_DECISION_CHOICES, GUIDE_SECTIONS,
)
from utils.core import (
    get_user, save_user, default_user, log_tx, delete_tx, add_income, adjust_balance,
    get_net_worth, real_net_worth, mock_portfolio_value, mock_total_value,
    get_market, tick_market, format_korean_money,
    get_level, xp_progress, check_habit_badges, award_badge, BADGE_BY_ID,
    set_goal, goal_progress, record_net_worth_point,
    create_saving, saving_progress, total_saving_amount,
    financial_health_score, predict_next_month_expense,
    record_scam_answer, scam_lab_summary, SCAM_MAX_SCORE,
    run_leverage_simulation, record_leverage_trial,
    get_crisis_path, reset_crisis_path, simulate_crisis_decisions, record_crisis_result,
    check_risk_lab_badges,
    spending_persona, estimate_retirement,
    verify_pin,
)
from utils.ai_coach import get_financial_diagnosis, get_risk_profile, get_full_report, chat_with_coach
from utils.database import db_available

st.set_page_config(page_title="머니레벨업 | AI 금융 코치", page_icon="💡", layout="wide")

ASSET_BY_ID = {a["id"]: a for a in ASSET_CONFIG}
CAT_BY_ID = {c["id"]: c for c in EXPENSE_CATEGORIES}
INCOME_CAT_BY_ID = {c["id"]: c for c in INCOME_CATEGORIES}
CRISIS_BY_ID = {c["id"]: c for c in CRISIS_SCENARIOS}
CRISIS_CHOICE_BY_ID = {c["id"]: c for c in CRISIS_DECISION_CHOICES}


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
    font=dict(color="#4B4C68", family="Noto Sans KR, sans-serif"),
    margin=dict(l=10, r=10, t=10, b=10),
)

UP_COLOR, DOWN_COLOR = "#F04452", "#364FC7"       # 국내 시세 관행: 상승=빨강, 하락=파랑
GAIN_COLOR, LOSS_COLOR = "#3182F6", "#F04452"     # 순자산 추이: 늘면 파랑(브랜드), 줄면 빨강
PIE_COLORS = ["#3182F6", "#8FBBFF", "#1B64DA", "#F5A524", "#4E5968", "#93C5FD", "#F04452", "#B0B8C1"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;800;900&family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');

:root {
    --paper: #F2F4F6; --paper-2: #FFFFFF; --ink: #191F28; --ink-soft: #4E5968;
    --ink-faint: #8B95A1; --line: #E5E8EB; --brand: #3182F6; --brand-deep: #1B64DA; --brand-soft: #E8F3FF;
    --gold: #F5A524; --gold-soft: #FFF4E0; --coral: #F04452; --coral-soft: #FFEEF0;
    --navy: #364FC7; --navy-soft: #EEF1FF;
}

.stApp { background: var(--paper); }
h1, h2, h3, h4 { font-family: 'Noto Sans KR', sans-serif !important; color: var(--ink) !important; font-weight: 800 !important; letter-spacing: -.2px; }
.stMarkdown, .stMarkdown p, .stMarkdown li, label, .stCaption, p, span, div[data-testid="stText"] {
    color: var(--ink); font-family: 'Noto Sans KR', sans-serif;
}
.stApp small, .stCaption, [data-testid="stCaptionContainer"] { color: var(--ink-faint) !important; }
[data-testid="stSidebar"] { background: var(--paper-2); border-right: 1px solid var(--line); }
hr { border-color: var(--line) !important; }

/* 상단 히어로 배너 */
.ml-hero {
    position: relative; overflow: hidden;
    background: var(--brand);
    border-radius: 20px; padding: 26px 30px; margin-bottom: 14px;
    box-shadow: 0 10px 24px -14px rgba(49,130,246,0.45);
}
.ml-hero .eyebrow {
    position: relative; font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem;
    letter-spacing: 2px; color: rgba(255,255,255,0.85); text-transform: uppercase; margin-bottom: 8px;
    display: inline-flex; align-items: center; gap: 6px;
}
.ml-hero h1 { position: relative; margin: 0; font-size: 1.7rem; color: #fff !important; font-weight: 800 !important; letter-spacing: -.3px; }
.ml-hero p  { position: relative; margin: 6px 0 0 0; color: rgba(255,255,255,0.82); font-size: 0.92rem; font-weight: 500; }

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
.ticker-item { display: inline-flex; align-items: center; gap: 8px; margin-right: 42px; font-size: 0.83rem; color: var(--ink-faint); }
.ticker-item b { color: var(--ink); }

/* 카드형 metric */
div[data-testid="stMetric"] {
    background: var(--paper-2); border: 1px solid var(--line); border-radius: 16px;
    padding: 14px 16px; box-shadow: 0 1px 2px rgba(25,31,40,0.04);
}
div[data-testid="stMetricLabel"] { color: var(--ink-faint) !important; }
div[data-testid="stMetricValue"] { color: var(--ink) !important; font-family: 'Space Grotesk', sans-serif !important; }

/* 자산 카드 */
.asset-card {
    background: var(--paper-2); border: 1px solid var(--line); border-radius: 12px;
    padding: 12px 14px; margin-bottom: 6px; transition: border-color .2s, transform .15s;
}
.asset-card:hover { border-color: var(--brand); transform: translateY(-1px); }
.asset-card .a-name { font-size: 0.8rem; color: var(--ink-soft); }
.asset-card .a-price { font-family: 'IBM Plex Mono', monospace; font-size: 1.05rem; color: var(--ink); font-weight: 700; }
.up   { color: var(--coral) !important; font-family: 'IBM Plex Mono', monospace; }
.down { color: var(--navy) !important; font-family: 'IBM Plex Mono', monospace; }

/* 클릭해서 종목을 고를 수 있는 카드형 버튼 (모의투자 상단 시세 카드) */
.asset-card-btn { margin-bottom: 6px; }
.asset-card-btn .stButton { margin: 0; }
.asset-card-btn button {
    background: var(--paper-2) !important; border: 1px solid var(--line) !important;
    border-radius: 12px !important; padding: 10px 12px !important; height: auto !important;
    white-space: pre-line !important; text-align: left !important; line-height: 1.5 !important;
    color: var(--ink) !important; font-weight: 400 !important; box-shadow: none !important;
    transition: border-color .2s, transform .15s !important;
}
.asset-card-btn button:hover { border-color: var(--brand) !important; transform: translateY(-1px); }
.asset-card-btn button p { white-space: pre-line !important; font-size: 0.85rem !important; }
.asset-card-btn.selected button {
    border: 1.5px solid var(--brand) !important; background: var(--brand-soft) !important;
    box-shadow: 0 0 0 1px var(--brand) inset !important;
}

/* 뉴스 카드 */
.news-item { border-left: 3px solid var(--brand); padding: 6px 12px; margin-bottom: 6px;
    background: var(--paper-2); border: 1px solid var(--line); border-left-width: 3px; border-radius: 0 8px 8px 0; }
.news-item .n-time { font-size: 0.72rem; color: var(--ink-soft); font-family: 'IBM Plex Mono', monospace; }
.news-item .n-text { font-size: 0.85rem; color: var(--ink); }

/* 호가창 */
.ob-wrap { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; background: var(--paper-2); }
.ob-row { position: relative; display: flex; justify-content: space-between; padding: 5px 12px; font-size: 0.8rem;
    font-family: 'IBM Plex Mono', monospace; overflow: hidden; }
.ob-row.ask { color: var(--navy); } .ob-row.bid { color: var(--coral); }
.ob-bar { position: absolute; right: 0; top: 0; bottom: 0; background: currentColor; opacity: 0.10; }
.ob-row span { position: relative; z-index: 1; }
.ob-cur { text-align: center; padding: 7px; background: var(--gold-soft); font-weight: 700; color: var(--gold);
    font-family: 'IBM Plex Mono', monospace; font-size: 0.86rem;
    border-top: 1px dashed #F0C888; border-bottom: 1px dashed #F0C888; letter-spacing: .3px; }
.ob-caption { font-size: 0.7rem; color: var(--ink-soft); text-align: center; padding: 4px 0 0 0; }

/* ── 뱃지 ── */
.stamp-cell { text-align: center; padding: 10px 6px 14px 6px; margin-bottom: 6px; }
.stamp-circle {
    width: 60px; height: 60px; border-radius: 50%; margin: 0 auto 8px auto; position: relative;
    display: flex; align-items: center; justify-content: center;
    border: 1px solid var(--line); background: var(--paper-2); transition: transform .15s ease;
}
.stamp-circle.earned {
    border: 1px solid var(--brand-soft);
    background: var(--brand-soft);
}
.stamp-circle.earned:hover { transform: translateY(-2px); }
.stamp-circle.locked { opacity: 0.4; filter: grayscale(1); }
.stamp-icon { font-size: 1.5rem; position: relative; }
.stamp-name { font-family: 'Noto Sans KR', sans-serif; font-weight: 700; font-size: 0.78rem; color: var(--ink); }
.stamp-desc { font-size: 0.66rem; color: var(--ink-faint); margin-top: 2px; min-height: 28px; }
.stamp-xp { font-family: 'IBM Plex Mono', monospace; font-size: 0.63rem; font-weight: 700; color: var(--gold); margin-top: 3px; }

/* 레벨 배지 */
.level-badge { display:inline-flex; align-items:center; gap:8px; background: var(--brand-soft); border:1px solid var(--brand-soft);
    border-radius: 999px; padding: 6px 14px; font-size: 0.82rem; color: var(--brand-deep); font-weight: 700; font-family:'Noto Sans KR',sans-serif; }

/* 온보딩 카드 */
.onb-card { background: var(--paper-2); border:1px solid var(--line); border-radius:16px; padding:20px; margin-bottom:14px; }

/* ── 가계부: 카테고리 선택 pill ── */
.stButton > button { border-radius: 10px !important; }
.cat-pill-active button {
    background: var(--brand) !important; border: 1px solid var(--brand) !important;
    color: white !important; font-weight: 700 !important; box-shadow: none !important;
}

/* 지출 카드 */
.exp-card {
    display:flex; align-items:center; gap:12px;
    background: var(--paper-2); border: 1px solid var(--line); border-left: 4px solid var(--accent, #3182F6);
    border-radius: 12px; padding: 10px 14px; margin-bottom: 8px; box-shadow: 0 1px 2px rgba(25,31,40,0.04);
}
.exp-card .exp-icon { font-size: 1.4rem; }
.exp-card .exp-main { flex: 1; }
.exp-card .exp-cat { font-size: 0.78rem; color: var(--ink-faint); }
.exp-card .exp-memo { font-size: 0.85rem; color: var(--ink); font-weight: 600; }
.exp-card .exp-amt { font-family:'Space Grotesk',sans-serif; font-weight:700; color: var(--coral); }
.exp-card .exp-time { font-size: 0.68rem; color: var(--ink-faint); margin-top: 2px; }

/* ── 목표저축 / 예적금 카드 ── */
.goal-hero {
    background: var(--brand-soft);
    border: 1px solid var(--brand-soft); border-radius: 18px; padding: 20px 22px; margin-bottom: 12px;
}
.goal-hero .g-name { font-family: 'Noto Sans KR', sans-serif; font-size: 1.1rem; font-weight: 800; color: var(--brand-deep); }
.goal-hero .g-sub { font-size: 0.82rem; color: var(--ink-soft); margin-top: 3px; font-family: 'Space Grotesk', sans-serif; }

.sv-card {
    background: var(--paper-2); border: 1px solid var(--line); border-radius: 16px;
    padding: 18px 20px; margin-bottom: 14px; box-shadow: 0 1px 2px rgba(25,31,40,0.04);
}
.sv-card .sv-title { font-family: 'Noto Sans KR', sans-serif; font-size: 1rem; font-weight: 800; color: var(--ink); }
.sv-card .sv-sub { font-size: 0.75rem; color: var(--ink-faint); margin-top: 3px; margin-bottom: 10px; font-family:'Space Grotesk',sans-serif; }
.sv-chip { display:inline-block; font-size: 0.68rem; padding: 2px 9px; border-radius: 999px; margin-left: 6px; font-family:'Noto Sans KR',sans-serif; }
.sv-chip.done { background: var(--brand-soft); color: var(--brand-deep); border: 1px solid var(--brand-soft); }
.sv-chip.live { background: var(--gold-soft); color: var(--gold); border: 1px solid var(--gold-soft); }

/* 목표 진행 바 */
.chase-wrap { margin: 10px 0 4px 0; }
.chase-track { position: relative; height: 14px; background: var(--paper); border-radius: 999px;
    border: 1px solid var(--line); overflow: visible; }
.chase-track.time { background-color: var(--paper); }
.chase-fill { position: absolute; left:0; top:0; bottom:0; border-radius: 999px; transition: width .7s ease; }
.chase-runner { position: absolute; top: 50%; transform: translateY(-50%); font-size: 1rem;
    transition: left .7s ease; }
.chase-labels { display:flex; justify-content: space-between; font-size: 0.7rem; color: var(--ink-faint);
    margin-top: 5px; font-family: 'Space Grotesk', sans-serif; }

/* ── AI 코치: 코치의 메모 카드 ── */
.coach-card {
    position: relative; border-radius: 16px; padding: 26px 28px 24px 28px; margin-top: 14px;
    background: var(--paper-2); border: 1px solid var(--line);
    box-shadow: 0 1px 2px rgba(25,31,40,0.04);
}
.coach-card::before {
    content: "코치의 메모"; position: absolute; top: -11px; left: 24px;
    background: var(--paper-2); color: var(--brand-deep); border: 1px solid var(--brand-soft);
    font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; letter-spacing: 1px;
    padding: 3px 10px; border-radius: 999px;
}
.coach-hype {
    font-family: 'Noto Sans KR', sans-serif; font-weight: 800; font-size: 1.2rem; color: var(--brand-deep);
    display: block; margin-bottom: 10px;
}
.coach-summary { font-size: 1.02rem; font-weight: 700; color: var(--ink); margin-bottom: 10px; }
.risk-chip { display:inline-block; padding: 3px 12px; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }
.risk-low { background: var(--brand-soft); color: var(--brand-deep); border: 1px solid var(--brand-soft); }
.risk-mid { background: var(--gold-soft); color: var(--gold); border: 1px solid var(--gold-soft); }
.risk-high{ background: var(--coral-soft); color: var(--coral); border: 1px solid var(--coral-soft); }

/* ── 리스크 체험관 ── */
.rl-banner {
    background: var(--coral-soft); border: 1px solid var(--coral-soft);
    border-radius: 16px; padding: 16px 20px; margin-bottom: 14px;
}
.rl-banner b { color: #B0203D; }
.rl-banner span { color: #C23A54; font-size: 0.85rem; }
.chat-bubble {
    background: var(--paper-2); border: 1px solid var(--line); border-radius: 4px 16px 16px 16px;
    padding: 14px 18px; margin: 6px 0 14px 0; box-shadow: 0 1px 2px rgba(25,31,40,0.04); position: relative;
}
.chat-bubble .cb-sender { font-family:'IBM Plex Mono', monospace; font-size: 0.72rem; color: var(--ink-faint); margin-bottom: 6px; }
.chat-bubble .cb-sender b { color: var(--ink); }
.chat-bubble .cb-msg { font-size: 0.95rem; color: var(--ink); line-height: 1.55; }
.scam-grade { display:inline-block; padding: 6px 16px; border-radius: 999px; font-weight: 800;
    font-family: 'Noto Sans KR', sans-serif; font-size: 1.05rem; margin-bottom: 6px; }
.scam-grade.g-master { background: var(--brand-soft); color: var(--brand-deep); border: 1px solid var(--brand-soft); }
.scam-grade.g-good    { background: var(--gold-soft); color: var(--gold); border: 1px solid var(--gold-soft); }
.scam-grade.g-warn    { background: var(--coral-soft); color: var(--coral); border: 1px solid var(--coral-soft); }
.scam-grade.g-danger  { background: #FFD9E1; color: #B0203D; border: 1px solid #F3A9B8; }
.liq-banner { background: #FFD9E1; border: 1px solid #F3A9B8; color: #7A1130; border-radius: 12px;
    padding: 12px 16px; font-weight: 700; margin: 10px 0; }
.persona-card { display:flex; align-items:center; gap:16px; background: var(--brand-soft);
    border: 1px solid var(--brand-soft); border-radius: 16px; padding: 16px 20px; margin: 10px 0 18px 0; }
.persona-card .persona-icon { font-size: 2.1rem; }
.persona-card .persona-name { font-family:'Noto Sans KR', sans-serif; font-weight: 800; color: var(--brand-deep); font-size: 1.05rem; }
.persona-card .persona-desc { font-size: 0.82rem; color: var(--ink-soft); margin-top: 2px; }

/* ── 이용 가이드 ── */
.guide-hero {
    background: var(--brand); color: #fff;
    border-radius: 20px; padding: 26px 30px; margin-bottom: 18px; box-shadow: 0 10px 24px -14px rgba(49,130,246,0.45);
}
.guide-hero h1 { color: #fff !important; margin: 0 0 6px 0; font-size: 1.4rem; }
.guide-hero p { margin: 0; opacity: .88; font-size: 0.9rem; }
.guide-step-num {
    display:inline-flex; align-items:center; justify-content:center; width:24px; height:24px; border-radius:50%;
    background: var(--brand-soft); color:var(--brand-deep); font-weight:800; font-size:0.75rem; margin-right:8px; flex-shrink:0;
}

/* ══════════════════════════════════════════════════════════════════
   UI/UX 패치 — Streamlit 기본 위젯을 절제된 핀테크 톤으로 재단장
   ══════════════════════════════════════════════════════════════════ */

/* 전체 진입 애니메이션 */
.main .block-container { animation: ml-fade-in .35s ease-out; }
@keyframes ml-fade-in { from { opacity: 0; transform: translateY(4px);} to { opacity: 1; transform: translateY(0);} }

/* 스크롤바 */
::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-track { background: var(--paper); }
::-webkit-scrollbar-thumb { background: var(--line); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: var(--brand); }

/* ── 탭 내비게이션: 여백 중심 세그먼트 컨트롤 ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px; background: var(--paper-2); padding: 5px; border-radius: 12px;
    border: 1px solid var(--line);
    flex-wrap: wrap;
}
.stTabs [data-baseweb="tab"] {
    height: auto; padding: 8px 16px; border-radius: 9px; background: transparent;
    color: var(--ink-faint); font-family: 'Noto Sans KR', sans-serif; font-weight: 600; font-size: 0.87rem;
    transition: background .15s, color .15s;
}
.stTabs [data-baseweb="tab"]:hover { background: var(--brand-soft); color: var(--brand-deep); }
.stTabs [aria-selected="true"] {
    background: var(--brand) !important; color: #fff !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 18px; }

/* ── 버튼 ── */
.stButton > button {
    border: 1px solid var(--line) !important; background: var(--paper-2) !important;
    color: var(--ink) !important; font-weight: 700 !important; font-family: 'Noto Sans KR', sans-serif !important;
    transition: border-color .12s ease, color .12s ease; padding: 0.5rem 1.1rem !important;
    box-shadow: none !important;
}
.stButton > button:hover { border-color: var(--brand) !important; color: var(--brand-deep) !important; }
.stButton > button[kind="primary"], .stButton > button[data-testid="baseButton-primary"] {
    background: var(--brand) !important; border: 1px solid var(--brand) !important; color: #fff !important;
    box-shadow: none !important;
}
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="baseButton-primary"]:hover {
    background: var(--brand-deep) !important; color: #fff !important;
}
.stDownloadButton > button { border-radius: 10px !important; border: 1px solid var(--brand-soft) !important;
    background: var(--brand-soft) !important; color: var(--brand-deep) !important; font-weight: 700 !important; }

/* ── 입력 위젯 ── */
div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"] textarea {
    border-radius: 10px !important; border-color: var(--line) !important; background: var(--paper-2) !important;
}
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within > div {
    border-color: var(--brand) !important; box-shadow: 0 0 0 2px var(--brand-soft) !important;
}
.stSlider [data-baseweb="slider"] div[role="slider"] { background: var(--brand) !important; border-color: var(--brand-deep) !important; }
.stSlider [data-baseweb="slider"] > div > div { background: var(--brand) !important; }

/* ── 라디오/체크박스: 선택 칩처럼 ── */
div[role="radiogroup"] label, .stCheckbox label { border-radius: 10px !important; }
div[role="radiogroup"] label:has(input:checked) {
    background: var(--brand-soft); border: 1px solid var(--brand-soft); border-radius: 10px; padding: 2px 8px;
}

/* ── 폼 컨테이너 & 보더 컨테이너 ── */
div[data-testid="stForm"] {
    background: var(--paper-2); border: 1px solid var(--line) !important; border-radius: 16px !important;
    padding: 18px 20px !important; box-shadow: none;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
    border-radius: 16px !important;
}
[data-testid="stExpander"] {
    border: 1px solid var(--line) !important; border-radius: 14px !important; background: var(--paper-2) !important;
    overflow: hidden;
}
[data-testid="stExpander"] summary { font-weight: 700 !important; color: var(--ink) !important; }

/* ── 진행률 바 ── */
div[data-testid="stProgress"] > div > div { background: var(--line) !important; border-radius: 999px !important; }
div[data-testid="stProgress"] > div > div > div {
    background: var(--brand) !important; border-radius: 999px !important;
}

/* ── 알림 박스 ── */
div[data-testid="stAlert"] { border-radius: 12px !important; border-width: 1px !important; font-size: 0.9rem; }
div[data-testid="stNotificationContentInfo"] { color: var(--navy) !important; }
div[data-testid="stNotificationContentSuccess"] { color: var(--brand-deep) !important; }
div[data-testid="stNotificationContentWarning"] { color: #B36B00 !important; }
div[data-testid="stNotificationContentError"] { color: var(--coral) !important; }

/* ── 사이드바 ── */
[data-testid="stSidebar"] .stButton > button { width: 100%; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { font-size: 1.05rem !important; }

/* ── 링크 컬러 통일 ── */
a, a:visited { color: var(--brand-deep) !important; }

/* ── 반응형: 좁은 화면에서 히어로/탭 여백 축소 ── */
@media (max-width: 640px) {
    .ml-hero { padding: 18px 18px; border-radius: 16px; }
    .ml-hero h1 { font-size: 1.4rem; }
    .stTabs [data-baseweb="tab"] { padding: 7px 10px; font-size: 0.78rem; }
}

/* ══════════════ 대시보드: 토스 스타일 ══════════════ */

/* 인사 헤더 */
.db-greet { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom: 14px; gap: 12px; flex-wrap: wrap; }
.db-greet .db-hello { font-size: 1.28rem; font-weight: 800; color: var(--ink); font-family:'Noto Sans KR',sans-serif; letter-spacing:-.2px; }
.db-greet .db-sub { font-size: 0.86rem; color: var(--ink-faint); margin-top: 5px; font-weight: 500; }

/* 통계 카드 그리드 (총자산 / 이번달지출 / 재무건강점수) */
.stat-grid { display:grid; grid-template-columns: 1.3fr 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.stat-box {
    background: var(--paper-2); border: 1px solid var(--line); border-radius: 18px;
    padding: 18px 20px; box-shadow: 0 1px 2px rgba(25,31,40,0.04);
}
.stat-box .stat-label { font-size: 0.8rem; color: var(--ink-faint); font-weight: 700; margin-bottom: 10px; }
.stat-box .stat-value { font-family:'Space Grotesk',sans-serif; font-size: 1.55rem; font-weight: 700; color: var(--ink); letter-spacing: -.3px; }
.stat-box .stat-unit { font-size: 0.85rem; color: var(--ink-faint); font-weight: 500; }
.stat-box .stat-foot { font-size: 0.74rem; color: var(--ink-faint); margin-top: 8px; font-weight: 500; }
.stat-box.primary {
    background: linear-gradient(135deg, var(--brand) 0%, var(--brand-deep) 100%);
    border: none; box-shadow: 0 12px 26px -14px rgba(49,130,246,0.55);
}
.stat-box.primary .stat-label { color: rgba(255,255,255,0.82); }
.stat-box.primary .stat-value { color: #fff; }
.stat-box.primary .stat-foot { color: rgba(255,255,255,0.78); }
.stat-box.mock {
    background: var(--gold-soft); border: 1px solid #F5E3BC;
}
.stat-box.mock .stat-label { color: #B36B00; }
.stat-box.mock .stat-value { color: #8A5A00; }
.stat-box.mock .stat-foot { color: #B36B00; opacity: .85; }
.stat-grid-2 { grid-template-columns: 1fr 1fr; }
.tag-real, .tag-mock {
    display:inline-block; font-size: 0.66rem; font-weight: 700; padding: 2px 8px; border-radius: 999px;
    margin-left: 6px; vertical-align: middle; font-family: 'Noto Sans KR', sans-serif;
}
.stat-box.primary .tag-real { background: rgba(255,255,255,0.22); color: #fff; }
.stat-box.mock .tag-mock { background: rgba(179,107,0,0.14); color: #B36B00; }
@media (max-width: 900px) {
    .stat-grid { grid-template-columns: 1fr 1fr; }
    .stat-grid-2 { grid-template-columns: 1fr; }
    .stat-box.primary { grid-column: 1 / -1; }
}

/* 보유 종목 리스트 (모의투자) */
.holding-card { display:flex; flex-direction:column; }
.holding-row { display:flex; align-items:center; gap: 12px; padding: 10px 2px; border-bottom: 1px solid var(--line); }
.holding-row:last-child { border-bottom: none; padding-bottom: 2px; }
.hold-icon { width: 38px; height: 38px; border-radius: 50%; background: var(--paper); display:flex; align-items:center; justify-content:center; font-size: 1.1rem; flex-shrink:0; }
.hold-main { flex: 1; min-width: 0; }
.hold-title { font-size: 0.88rem; font-weight: 700; color: var(--ink); }
.hold-sub { font-size: 0.72rem; color: var(--ink-faint); margin-top: 2px; }
.hold-right { text-align: right; flex-shrink: 0; }
.hold-value { font-family:'Space Grotesk',sans-serif; font-weight: 700; font-size: 0.88rem; color: var(--ink); }
.hold-pnl { font-size: 0.74rem; font-weight: 700; margin-top: 2px; font-family:'Space Grotesk',sans-serif; }
.hold-pnl.up { color: var(--coral); }
.hold-pnl.down { color: var(--navy); }
.hold-pnl.flat { color: var(--ink-faint); }

/* 카드 안 소제목 */
.card-head { font-size: 0.95rem; font-weight: 800; color: var(--ink); margin-bottom: 12px; display:flex; align-items:center; gap:6px; }

/* 최근 내역 리스트 */
.activity-card { display:flex; flex-direction:column; }
.activity-row { display:flex; align-items:center; gap: 12px; padding: 10px 2px; border-bottom: 1px solid var(--line); }
.activity-row:last-child { border-bottom: none; padding-bottom: 2px; }
.act-icon { width: 38px; height: 38px; border-radius: 50%; background: var(--paper); display:flex; align-items:center; justify-content:center; font-size: 1.1rem; flex-shrink:0; }
.act-main { flex: 1; min-width: 0; }
.act-title { font-size: 0.88rem; font-weight: 700; color: var(--ink); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.act-sub { font-size: 0.72rem; color: var(--ink-faint); margin-top: 2px; }
.act-amt { font-family:'Space Grotesk',sans-serif; font-weight: 700; font-size: 0.88rem; white-space:nowrap; }
.act-amt.neg { color: var(--ink); }
.act-amt.pos { color: var(--brand-deep); }

/* 하단 미니 뱃지 스트립 */
.mini-badge-row { display:flex; flex-wrap: wrap; gap: 8px; }
.mini-badge { display:inline-flex; align-items:center; gap: 6px; background: var(--paper); border: 1px solid var(--line);
    border-radius: 999px; padding: 7px 13px; font-size: 0.76rem; font-weight: 700; color: var(--ink-soft); }
.mini-badge .mb-icon { font-size: 0.92rem; }

/* border=True 컨테이너를 카드처럼 */
div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
    background: var(--paper-2) !important;
    box-shadow: 0 1px 2px rgba(25,31,40,0.04);
}
</style>
"""


def price_chart(asset_id, market):
    hist = market["history"].get(asset_id, [])
    if len(hist) < 2:
        hist = hist * 2
    up = hist[-1] >= hist[0]
    line_color = UP_COLOR if up else DOWN_COLOR
    fill_color = "rgba(255,77,109,0.10)" if up else "rgba(62,123,250,0.10)"
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
                              line=dict(color="#364FC7", width=2.5, dash="dot"), marker=dict(size=4)))
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
        textinfo="label+percent", textfont=dict(size=11, color="#191F28"),
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
        textinfo="label+percent", textfont=dict(size=11, color="#191F28"),
    ))
    fig.update_layout(**PLOTLY_DARK, height=280, showlegend=False)
    return fig


def combined_asset_donut(user, market):
    """전체 자산 배분 한눈에 보기 (예/적금 · 모의투자 평가액 · 현금)."""
    save_amt = total_saving_amount(user)
    invest_amt = mock_portfolio_value(user, market)
    cash_amt = user.get("real_cash", 0) + user.get("mock_cash", 0)
    labels, values = [], []
    for label, val in [("예금/적금", save_amt), ("주식형(모의투자)", invest_amt), ("현금", cash_amt)]:
        if val > 0:
            labels.append(label)
            values.append(val)
    if not values:
        return None
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.62,
        marker=dict(colors=PIE_COLORS),
        textinfo="label+percent", textfont=dict(size=11, color="#191F28"),
    ))
    fig.update_layout(**PLOTLY_DARK, height=260, showlegend=False)
    return fig


def _tx_row_data(t):
    """가계부/투자 로그 한 건을 (아이콘, 제목, 부제, 부호있는 금액)으로 변환."""
    kind = t.get("kind")
    if kind == "expense":
        cat = CAT_BY_ID.get(t.get("category"), {})
        icon = cat.get("icon", "🧾")
        title = t.get("memo") or cat.get("name", "지출")
        sub = cat.get("name", "지출")
        amt = -t.get("amount", 0)
    elif kind == "income":
        cat = INCOME_CAT_BY_ID.get(t.get("category"), {})
        icon = cat.get("icon", "💵")
        title = t.get("memo") or cat.get("name", "수입")
        sub = cat.get("name", "수입")
        amt = t.get("amount", 0)
    elif kind in ("invest_buy", "invest_sell"):
        a = ASSET_BY_ID.get(t.get("asset"), {})
        icon = a.get("icon", "📈")
        title = f"{a.get('name', '자산')} {'매수' if kind == 'invest_buy' else '매도'}"
        sub = "모의투자"
        val = t.get("qty", 0) * t.get("price", 0)
        amt = -val if kind == "invest_buy" else val
    elif kind == "savings_open":
        icon, title, sub, amt = "🏦", t.get("name", "예/적금"), "예적금 가입", -t.get("amount", 0)
    elif kind == "savings_deposit":
        icon, title, sub, amt = "💰", t.get("name", "예/적금"), "추가 납입", -t.get("amount", 0)
    elif kind == "savings_close":
        icon, title, sub, amt = "🔓", t.get("name", "예/적금"), "해지", t.get("amount", 0)
    else:
        icon, title, sub, amt = "•", kind or "활동", "", 0
    return icon, title, sub, amt


def render_news_ticker(market):
    items = market.get("news", [])
    if not items:
        ticker_html = "<div class='ticker-item'>📡 시장 뉴스를 수신 대기 중입니다...</div>"
    else:
        ticker_html = "".join(
            f"<span class='ticker-item'>📰 <b>{ASSET_BY_ID.get(n['asset'],{}).get('name', n['asset'])}</b> · {n['text']}</span>"
            for n in items[:8]
        )
    st.markdown(f"""<div class="ticker-wrap">
        <div class="ticker-tag">NEWS</div>
        <div class="ticker-scroll"><div class="ticker-inner">{ticker_html}{ticker_html}</div></div>
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
        color_from, color_to = "#94A3C4", "#4E5968"
        runner = "🏁" if pct >= 1.0 else "🚶"
        track_cls = "chase-track time"
    else:
        color_from, color_to = "#8FBBFF", "#3182F6"
        if pct >= 1.0:
            runner = "🌳"
        elif pct >= 0.6:
            runner = "🌿"
        elif pct >= 0.25:
            runner = "🌱"
        else:
            runner = "🌰"
        track_cls = "chase-track"

    st.markdown(f"""<div class="chase-wrap">
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


def render_dashboard(user, market, display_name: str = "회원"):
    real_nw = real_net_worth(user)
    mock_val = mock_total_value(user, market)
    invest_val = mock_portfolio_value(user, market)

    month_start = time.mktime(time.strptime(time.strftime("%Y-%m-01"), "%Y-%m-%d"))
    month_expense = sum(t["amount"] for t in user["tx_log"]
                         if t.get("kind") == "expense" and t.get("ts", 0) >= month_start)
    fh = financial_health_score(user, market)
    level, pct, next_ceil = xp_progress(user["xp"])

    # ── 인사 헤더 ──
    st.markdown(f"""<div class="db-greet">
        <div>
            <div class="db-hello">안녕하세요, {html.escape(display_name)}님 👋</div>
            <div class="db-sub">오늘도 좋은 소비 습관 이어가볼까요?</div>
        </div>
        <span class="level-badge">⭐ Lv.{level} · {fh['grade']}등급</span>
        </div>""", unsafe_allow_html=True)

    # ── 실제 자산 / 모의투자 (완전히 분리해서 표시 — 헷갈리지 않도록) ──
    st.markdown(f"""<div class="stat-grid stat-grid-2">
        <div class="stat-box primary">
            <div class="stat-label">💰 실제 자산 <span class="tag-real">내가 입력한 진짜 돈</span></div>
            <div class="stat-value">{format_korean_money(real_nw)}</div>
            <div class="stat-foot">지갑 {format_korean_money(user.get('real_cash', 0))} · 저축 {format_korean_money(total_saving_amount(user))}</div>
        </div>
        <div class="stat-box mock">
            <div class="stat-label">🧪 모의투자 <span class="tag-mock">연습용 가상 시드머니</span></div>
            <div class="stat-value">{format_korean_money(mock_val)}</div>
            <div class="stat-foot">모의 현금 {format_korean_money(user.get('mock_cash', 0))} · 투자평가액 {format_korean_money(invest_val)}</div>
        </div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="stat-grid stat-grid-2">
        <div class="stat-box">
            <div class="stat-label">이번 달 지출</div>
            <div class="stat-value">{format_korean_money(month_expense)}</div>
            <div class="stat-foot">가계부 탭에서 자세히 보기</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">재무 건강 점수</div>
            <div class="stat-value">{fh['score']}<span class="stat-unit"> / 100</span></div>
            <div class="stat-foot">{fh['comment']}</div>
        </div>
        </div>""", unsafe_allow_html=True)

    # ── 자산 배분: 실제 자산 vs 모의투자 (도넛도 분리) ──
    col_pie1, col_pie2 = st.columns([1, 1])
    with col_pie1:
        with st.container(border=True):
            st.markdown('<div class="card-head">💰 실제 자산 배분</div>', unsafe_allow_html=True)
            fig_real = real_asset_donut(user)
            if fig_real:
                st.plotly_chart(fig_real, use_container_width=True, config={"displayModeBar": False})
            else:
                st.caption("지갑에 돈을 채우거나 저축을 시작하면 표시돼요.")
    with col_pie2:
        with st.container(border=True):
            st.markdown('<div class="card-head">🧪 모의투자 배분</div>', unsafe_allow_html=True)
            fig_mock = mock_portfolio_donut(user, market)
            if fig_mock:
                st.plotly_chart(fig_mock, use_container_width=True, config={"displayModeBar": False})
            else:
                st.caption("모의투자를 시작하면 표시돼요.")

    # ── 보유 종목 (모의투자) — 어떤 종목을 얼마에 샀고 수익률이 어떤지 항상 볼 수 있게 ──
    with st.container(border=True):
        st.markdown('<div class="card-head">📊 보유 종목 (모의투자)</div>', unsafe_allow_html=True)
        held = [(aid, pos) for aid, pos in user.get("portfolio", {}).items() if pos.get("qty", 0) > 0]
        if held:
            rows_html = []
            for aid, pos in held:
                a = ASSET_BY_ID[aid]
                cur = market["prices"].get(aid, 0)
                val = pos["qty"] * cur
                pnl = (cur - pos["avg_price"]) * pos["qty"]
                pnl_pct = (cur / pos["avg_price"] - 1) * 100 if pos["avg_price"] else 0
                cls = "up" if pnl > 0 else ("down" if pnl < 0 else "flat")
                sign = "+" if pnl > 0 else ""
                rows_html.append(f"""<div class="holding-row">
                    <div class="hold-icon">{a['icon']}</div>
                    <div class="hold-main">
                        <div class="hold-title">{html.escape(a['name'])}</div>
                        <div class="hold-sub">{pos['qty']}주 · 평단 {format_korean_money(pos['avg_price'])} · 현재가 {format_korean_money(cur)}</div>
                    </div>
                    <div class="hold-right">
                        <div class="hold-value">{format_korean_money(val)}</div>
                        <div class="hold-pnl {cls}">{sign}{format_korean_money(pnl)} ({sign}{pnl_pct:.1f}%)</div>
                    </div>
                    </div>""")
            st.markdown(f'<div class="holding-card">{"".join(rows_html)}</div>', unsafe_allow_html=True)
        else:
            st.caption("아직 보유 종목이 없어요. '모의투자' 탭에서 관심 있는 종목을 사보세요.")

    # ── 순자산 추이 ──
    with st.container(border=True):
        st.markdown('<div class="card-head">📈 순자산 추이</div>', unsafe_allow_html=True)
        nw_fig = net_worth_chart(user)
        if nw_fig:
            st.plotly_chart(nw_fig, use_container_width=True, config={"displayModeBar": False})
            st.caption("빨강=실제 자금 · 파랑 점선=모의투자 (세션 내 기록 기준)")
        else:
            st.caption("기록이 쌓이면 순자산 추이를 보여드려요.")

    # ── 최근 내역 ──
    with st.container(border=True):
        st.markdown('<div class="card-head">🕒 최근 내역</div>', unsafe_allow_html=True)
        if user.get("tx_log"):
            rows_html = []
            for t in user["tx_log"][:6]:
                icon, title, sub, amt = _tx_row_data(t)
                amt_cls = "pos" if amt > 0 else "neg"
                amt_str = f"{'+' if amt > 0 else ''}{format_korean_money(amt)}" if amt != 0 else "0원"
                when = relative_time(t.get("ts", time.time()))
                rows_html.append(f"""<div class="activity-row">
                    <div class="act-icon">{icon}</div>
                    <div class="act-main">
                        <div class="act-title">{html.escape(str(title))}</div>
                        <div class="act-sub">{html.escape(str(sub))} · {when}</div>
                    </div>
                    <div class="act-amt {amt_cls}">{amt_str}</div>
                    </div>""")
            st.markdown(f'<div class="activity-card">{"".join(rows_html)}</div>', unsafe_allow_html=True)
        else:
            st.caption("아직 기록이 없어요. '가계부' 탭에서 첫 지출을 기록해보세요.")

    tip = TIPS[int(time.strftime("%j")) % len(TIPS)]
    st.info(tip)

    # ── 획득 뱃지 스트립 ──
    earned = [b for b in BADGES if b["id"] in user.get("badges", [])]
    g = goal_progress(user)
    n_held = len(held)
    chips = []
    if earned:
        for b in earned[-3:][::-1]:
            chips.append(f'<span class="mini-badge"><span class="mb-icon">{b["icon"]}</span>{b["name"]}</span>')
    chips.append(f'<span class="mini-badge"><span class="mb-icon">🏅</span>뱃지 {len(earned)}/{len(BADGES)}</span>')
    chips.append(f'<span class="mini-badge"><span class="mb-icon">📈</span>보유 종목 {n_held}개</span>')
    goal_pct_str = f"{g['pct']*100:.0f}%" if g else "목표 없음"
    chips.append(f'<span class="mini-badge"><span class="mb-icon">🎯</span>목표 달성률 {goal_pct_str}</span>')
    st.write("")
    st.markdown(f'<div class="mini-badge-row">{"".join(chips)}</div>', unsafe_allow_html=True)

    # ── 다음 달 예상 지출 (상세, 접어두기) ──
    forecast = predict_next_month_expense(user)
    with st.expander("🔮 다음 달 예상 지출 · 재무 건강 점수 상세 보기"):
        fcol, hcol = st.columns([1, 1])
        with fcol:
            st.markdown("**다음 달 예상 지출**")
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
        with hcol:
            st.markdown(f"**재무 건강 점수 구성 · {fh['score']}점 ({fh['grade']}등급)**")
            st.progress(min(1.0, fh["score"] / 100))
            for b in fh["breakdown"]:
                st.write(f"**{b['key']}** — {b['points']}/{b['max']}점")
                st.caption(b["detail"])


# ── 모의투자 ──────────────────────────────────────────────────────────────
def render_invest(user, market):
    st.caption("⚠️ 실제 시세가 아닌 랜덤워크+뉴스 이벤트 기반 가상 시뮬레이션입니다. (약 15초마다 갱신)")
    st.info(f"🧪 모의투자 잔고: **{format_korean_money(user['mock_cash'])}** — 실제 자금과 완전히 분리된 연습용 가상 머니예요.")

    if "invest_selected_asset" not in st.session_state:
        st.session_state.invest_selected_asset = ASSET_CONFIG[0]["id"]

    cols = st.columns(4)
    for i, a in enumerate(ASSET_CONFIG):
        with cols[i % 4]:
            price = market["prices"][a["id"]]
            hist = market["history"].get(a["id"], [price])
            chg = (price - hist[0]) / hist[0] * 100 if hist[0] else 0
            cls = "up" if chg >= 0 else "down"
            arrow = "▲" if chg >= 0 else "▼"
            active = st.session_state.invest_selected_asset == a["id"]
            st.markdown(f'<div class="asset-card-btn {"selected" if active else ""}">', unsafe_allow_html=True)
            clicked = st.button(
                f"{a['icon']} {a['name']}\n{format_korean_money(price)}\n{arrow} {chg:+.2f}%",
                key=f"asset_card_{a['id']}", use_container_width=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)
            if clicked:
                st.session_state.invest_selected_asset = a["id"]
                st.rerun()

    st.divider()
    _asset_ids = [a["id"] for a in ASSET_CONFIG]
    _default_idx = _asset_ids.index(st.session_state.invest_selected_asset)
    asset_id = st.selectbox("🔎 종목 선택", _asset_ids, index=_default_idx,
                             format_func=lambda x: f"{ASSET_BY_ID[x]['icon']} {ASSET_BY_ID[x]['name']} ({ASSET_BY_ID[x]['type']})")
    if asset_id != st.session_state.invest_selected_asset:
        st.session_state.invest_selected_asset = asset_id
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
                elif amount > user.get("real_cash", 0):
                    st.error("지갑 잔액이 부족합니다. 가계부 탭에서 수입을 먼저 추가하거나 지갑 잔액을 조정해주세요.")
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
                c = INCOME_CAT_BY_ID.get(t.get("category"), {"icon": "💵", "name": "수입", "color": "#3182F6"})
                sign, accent = "+", "#3182F6"
            else:
                c = CAT_BY_ID[t["category"]]
                sign, accent = "-", c.get("color", "#F04452")
            row_l, row_r = st.columns([6, 1])
            with row_l:
                st.markdown(f"""<div class="exp-card" style="--accent:{accent}">
                        <div class="exp-icon">{c['icon']}</div>
                        <div class="exp-main">
                            <div class="exp-cat">{c['name']}</div>
                            <div class="exp-memo">{html.escape(t.get('memo') or '메모 없음')}</div>
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
            <div class="g-name">🏁 {html.escape(g['name'])}</div>
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
                <div class="sv-title">{s.get('icon','🏦')} {html.escape(s['name'])} {chips}</div>
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
def render_badges(user, market, display_name: str = "회원"):
    level, pct, next_ceil = xp_progress(user["xp"])
    st.subheader(f"🏅 레벨 {level}")
    st.progress(pct, text=f"XP {user['xp']} / {next_ceil}")
    st.caption(f"확률형 아이템이 아닌, 조건을 채우면 100% 지급되는 성취 배지입니다. ({len(user['badges'])} / {len(BADGES)} 개 획득)")

    persona = spending_persona(user)
    st.markdown(f"""<div class="persona-card">
        <div class="persona-icon">{persona['icon']}</div>
        <div><div class="persona-name">{persona['name']}</div>
        <div class="persona-desc">{persona['desc']}</div></div>
        </div>""", unsafe_allow_html=True)

    with st.expander("📇 내 금융 리포트 카드 다운로드"):
        st.caption("레벨·뱃지·재무 건강 점수·리스크 체험관 성적을 한 장으로 모은 요약 카드예요. 공모전 제출용 캡처나 공유에 써보세요.")
        html_report = build_report_card_html(user, market, display_name)
        st.components.v1.html(html_report, height=560, scrolling=True)
        st.download_button("⬇️ HTML로 다운로드", data=html_report,
                            file_name=f"{display_name or 'user'}_머니레벨업_리포트카드.html",
                            mime="text/html")

    cols = st.columns(6)
    for i, b in enumerate(BADGES):
        earned = b["id"] in user["badges"]
        with cols[i % 6]:
            cls = "earned" if earned else "locked"
            st.markdown(f"""<div class="stamp-cell">
                <div class="stamp-circle {cls}">
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
                                        marker=dict(colors=["#3182F6", "#4E5968", "#F5A524"])))
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
        hype_html = f'<div class="coach-hype">{hype}</div>' if hype else ''
        st.markdown(f"""<div class="coach-card">{hype_html}
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


# ── 🚨 리스크 체험관 ─────────────────────────────────────────────────────
def render_scam_lab(user):
    st.markdown("##### 🎣 금융사기 대응 훈련")
    st.caption("실제 신고가 많은 유형을 재구성한 가상 메시지입니다. 지금 당신이라면 어떻게 하시겠어요?")

    idx = st.session_state.get("_scam_idx", 0)

    if idx >= len(SCAM_SCENARIOS):
        summary = scam_lab_summary(user)
        grade_cls = {"사기 방어 마스터": "g-master", "양호": "g-good",
                     "주의 필요": "g-warn", "위험": "g-danger"}.get(summary["grade"], "g-warn")
        with st.container(border=True):
            st.markdown(f'<span class="scam-grade {grade_cls}">{summary["grade"]}</span>', unsafe_allow_html=True)
            st.markdown(f"**{summary['total']} / {summary['max']}점** ({summary['completed']}/{summary['n_scenarios']}개 완료)")
            st.write(summary["comment"])
        if st.button("🔁 처음부터 다시 훈련하기"):
            st.session_state["_scam_idx"] = 0
            st.rerun()
        return

    scenario = SCAM_SCENARIOS[idx]
    st.progress((idx) / len(SCAM_SCENARIOS), text=f"{idx + 1} / {len(SCAM_SCENARIOS)}")
    st.markdown(f'<div class="chat-bubble"><div class="cb-sender">{scenario["channel"]} · <b>{scenario["sender"]}</b></div>'
                f'<div class="cb-msg">{scenario["message"]}</div></div>', unsafe_allow_html=True)

    answered_key = f"_scam_answered_{scenario['id']}"
    if st.session_state.get(answered_key) is not None:
        choice = scenario["choices"][st.session_state[answered_key]]
        if choice["score"] >= 10:
            st.success(f"**+{choice['score']}점** — {choice['feedback']}")
        elif choice["score"] >= 5:
            st.warning(f"**+{choice['score']}점** — {choice['feedback']}")
        else:
            st.error(f"**+{choice['score']}점** — {choice['feedback']}")
        st.info(f"💡 핵심: {scenario['lesson']}")
        if st.button("다음 시나리오 ▶", type="primary"):
            st.session_state["_scam_idx"] = idx + 1
            st.session_state[answered_key] = None
            st.rerun()
    else:
        choice_label = st.radio("당신의 선택은?", [c["label"] for c in scenario["choices"]],
                                 key=f"_scam_radio_{scenario['id']}", index=None)
        if st.button("선택하기", type="primary", disabled=choice_label is None):
            ci = next(i for i, c in enumerate(scenario["choices"]) if c["label"] == choice_label)
            record_scam_answer(user, scenario["id"], ci)
            st.session_state[answered_key] = ci
            _persist(user)
            st.rerun()


def render_leverage_lab(user):
    st.markdown("##### 🎢 레버리지 위험 시뮬레이터")
    st.caption(f"실제/모의 자금과 무관한 학습 전용 가상 시드머니 {format_korean_money(LEVERAGE_SEED)}로, "
               f"배율에 따라 변동성이 얼마나 무섭게 증폭되는지 직접 겪어보세요.")

    volatile_assets = [a for a in ASSET_CONFIG if a["type"] in ("주식", "대체자산")]
    c1, c2 = st.columns([2, 1])
    with c1:
        asset_label = st.selectbox("종목 선택", [f'{a["icon"]} {a["name"]} (변동성 {a["vol"]*100:.1f}%/일)' for a in volatile_assets])
        asset = volatile_assets[[f'{a["icon"]} {a["name"]} (변동성 {a["vol"]*100:.1f}%/일)' for a in volatile_assets].index(asset_label)]
    with c2:
        lev_label = st.radio("레버리지 배율", [f"{x}배" for x in LEVERAGE_OPTIONS], horizontal=True, index=1)
        leverage = LEVERAGE_OPTIONS[[f"{x}배" for x in LEVERAGE_OPTIONS].index(lev_label)]

    if st.button("▶ 30일 시뮬레이션 실행", type="primary"):
        result = run_leverage_simulation(asset["id"], leverage)
        record_leverage_trial(user, result)
        st.session_state["_lev_result"] = result
        _persist(user)

    result = st.session_state.get("_lev_result")
    if result:
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=result["equity_base"], mode="lines", name="레버리지 없음 (1배)",
                                  line=dict(color="#364FC7", width=2, dash="dot")))
        fig.add_trace(go.Scatter(y=result["equity_lev"], mode="lines", name=f"{result['leverage']}배 레버리지",
                                  line=dict(color=DOWN_COLOR if result["liquidated"] else UP_COLOR, width=2.6)))
        fig.update_layout(**PLOTLY_DARK, height=280, showlegend=True, legend=dict(font=dict(size=11)))
        fig.update_xaxes(title="일차", showgrid=False)
        fig.update_yaxes(title="평가금액(원)", showgrid=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        m1, m2, m3 = st.columns(3)
        m1.metric(f"{result['leverage']}배 최종 평가액", format_korean_money(result["final_lev"]),
                   delta=f"{(result['final_lev']/result['seed']-1)*100:+.1f}%")
        m2.metric("1배(무레버리지) 최종 평가액", format_korean_money(result["final_base"]),
                   delta=f"{(result['final_base']/result['seed']-1)*100:+.1f}%")
        m3.metric("종목 30일 변동", f"{(result['final_base']/result['seed']-1)*100:+.1f}%")

        if result["liquidated"]:
            st.markdown(f'<div class="liq-banner">💥 {result["liquidated_day"]}일차에 강제 청산(로스컷)됐어요! '
                        f'같은 하락폭이어도 레버리지 없이 투자했다면 잃지 않았을 돈입니다.</div>', unsafe_allow_html=True)
        st.caption("같은 날짜의 시세 변동을 그대로 사용해, 레버리지 유무에 따른 차이만 비교하도록 설계했습니다. "
                   "실제 레버리지 상품은 이자·수수료가 추가로 붙어 여기보다 더 불리한 경우가 많습니다.")


def render_crisis_lab(user):
    st.markdown("##### 🌪️ 시장 위기 리플레이")
    st.caption("실제 사건의 '충격 형태'를 단순화한 가상 시나리오입니다. 폭락장 한가운데서 당신의 선택을 시험해보세요.")

    scenario_label = st.selectbox("시나리오 선택", [c["name"] for c in CRISIS_SCENARIOS], key="_crisis_select")
    scenario = next(c for c in CRISIS_SCENARIOS if c["name"] == scenario_label)
    st.write(scenario["desc"])

    path = get_crisis_path(scenario["id"])
    fig = go.Figure(go.Scatter(y=path, mode="lines", line=dict(color=DOWN_COLOR, width=2.2),
                                fill="tozeroy", fillcolor="rgba(255,77,109,0.10)"))
    for dday in scenario["decision_days"]:
        fig.add_vline(x=dday, line_width=1, line_dash="dash", line_color="#F5A524")
    fig.update_layout(**PLOTLY_DARK, height=240, showlegend=False)
    fig.update_xaxes(title="경과일", showgrid=False)
    fig.update_yaxes(title="지수(시작=100)", showgrid=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    if st.button("🔄 다른 흐름으로 다시 생성"):
        reset_crisis_path(scenario["id"])
        st.rerun()

    st.markdown("**1,000,000원을 시작 시점에 투자했다고 가정합니다.** 그래프의 점선 시점마다 당신의 선택은?")
    with st.form(f"crisis_form_{scenario['id']}"):
        decisions = {}
        for dday, label in zip(scenario["decision_days"], scenario["decision_labels"]):
            pct = (path[dday] / path[0] - 1) * 100
            st.markdown(f"**{dday}일차** · 지수 {path[dday]:.1f} (시작 대비 {pct:+.1f}%) — _{label}_")
            choice_label = st.radio("선택", [c["label"] for c in CRISIS_DECISION_CHOICES],
                                     key=f"_crisis_d_{scenario['id']}_{dday}", horizontal=False, label_visibility="collapsed")
            decisions[dday] = next(c["id"] for c in CRISIS_DECISION_CHOICES if c["label"] == choice_label)
        submitted = st.form_submit_button("📊 결과 확인하기", type="primary")

    if submitted:
        result = simulate_crisis_decisions(scenario["id"], decisions)
        record_crisis_result(user, scenario["id"], result)
        _persist(user)
        st.session_state[f"_crisis_result_{scenario['id']}"] = result

    result = st.session_state.get(f"_crisis_result_{scenario['id']}")
    if result:
        fig2 = go.Figure()
        baseline_curve = [(1_000_000 / path[0]) * v for v in path]
        fig2.add_trace(go.Scatter(y=baseline_curve, mode="lines", name="계속 보유(Buy & Hold)",
                                   line=dict(color="#364FC7", width=2, dash="dot")))
        fig2.add_trace(go.Scatter(y=result["user_curve"], mode="lines", name="내 선택대로",
                                   line=dict(color=GAIN_COLOR if result["final_value"] >= result["principal"] else LOSS_COLOR, width=2.6)))
        fig2.update_layout(**PLOTLY_DARK, height=260, showlegend=True, legend=dict(font=dict(size=11)))
        fig2.update_xaxes(title="경과일", showgrid=False)
        fig2.update_yaxes(title="평가금액(원)", showgrid=False)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        m1, m2, m3 = st.columns(3)
        m1.metric("내 최종 결과", format_korean_money(round(result["final_value"])),
                   delta=f"{(result['final_value']/result['principal']-1)*100:+.1f}% (원금 대비)")
        m2.metric("계속 보유했다면", format_korean_money(round(result["baseline_value"])),
                   delta=f"{(result['baseline_value']/1_000_000-1)*100:+.1f}%")
        diff = result["final_value"] - result["baseline_value"]
        m3.metric("Buy & Hold 대비 차이", format_korean_money(round(abs(diff))),
                   delta="더 나음" if diff > 0 else ("동일" if diff == 0 else "더 나쁨"))
        if diff < 0:
            st.info("공포에 판단해 이탈했다가 반등을 놓쳤을 가능성이 높아요. 하락장에서의 매도 타이밍은 늘 계속 보유보다 어렵습니다.")
        elif diff > 0:
            st.info("이번 시나리오에서는 당신의 판단이 계속 보유보다 나은 결과를 만들었어요. 다만 매번 통하는 전략은 아니라는 점도 기억해두세요.")


def render_risk_lab(user):
    st.markdown('<div class="rl-banner"><b>🚨 리스크 체험관</b><br>'
                '<span>실제 돈을 걸기 전에 먼저 겪어보는 위험 학습 공간입니다. '
                '여기서 다루는 모든 자산은 실제 자금·모의투자와 완전히 분리된 학습 전용 가상 자산이에요.</span></div>',
                unsafe_allow_html=True)
    sub = st.tabs(["🎣 사기 대응 훈련", "🎢 레버리지 시뮬레이터", "🌪️ 위기 리플레이"])
    with sub[0]:
        render_scam_lab(user)
    with sub[1]:
        render_leverage_lab(user)
    with sub[2]:
        render_crisis_lab(user)


# ── 🧓 노후 준비 설계 ────────────────────────────────────────────────────
def render_retirement(user, age: int):
    st.subheader("🧓 노후 준비 설계")
    st.caption("지금의 저축 속도로 은퇴 시점에 얼마가 모이는지, 필요한 노후자금과 비교해봅니다. "
               "'연간 생활비의 25배' 휴리스틱(4% 인출룰 근사)을 사용한 교육용 근사 계산입니다.")

    current_total = round(real_net_worth(user) + mock_total_value(user, get_market()))
    c1, c2, c3 = st.columns(3)
    with c1:
        current_age = st.number_input("현재 나이", min_value=15, max_value=80, value=int(age), step=1)
        retire_age = st.number_input("은퇴 목표 나이", min_value=current_age + 1, max_value=90, value=max(current_age + 1, 65), step=1)
    with c2:
        current_assets = st.number_input("현재 총자산(원)", min_value=0, value=max(0, current_total), step=100_000,
                                          help="대시보드의 순자산(실제+모의)을 기본값으로 불러왔어요. 직접 수정 가능합니다.")
        monthly_saving = st.number_input("매월 추가 저축/투자액(원)", min_value=0, value=300_000, step=50_000)
    with c3:
        annual_return = st.slider("예상 연 수익률(%)", 0.0, 12.0, 5.0, 0.5)
        inflation = st.slider("예상 물가상승률(%)", 0.0, 6.0, 2.5, 0.5)
    monthly_expense_today = st.number_input("은퇴 후 희망 월 생활비(오늘 기준, 원)", min_value=0, value=2_500_000, step=100_000)

    result = estimate_retirement(current_age, retire_age, current_assets, monthly_saving,
                                  annual_return, monthly_expense_today, inflation)

    fig = go.Figure()
    fig.add_trace(go.Scatter(y=result["curve"], mode="lines", name="예상 자산 곡선",
                              line=dict(color="#3182F6", width=2.6), fill="tozeroy", fillcolor="rgba(49,130,246,0.10)"))
    fig.add_hline(y=result["needed_corpus"], line_dash="dash", line_color="#F04452",
                  annotation_text="목표 노후자금", annotation_font_color="#F04452")
    fig.update_layout(**PLOTLY_DARK, height=300, showlegend=False)
    fig.update_xaxes(title="개월 수", showgrid=False)
    fig.update_yaxes(title="자산(원)", showgrid=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    m1, m2, m3 = st.columns(3)
    m1.metric(f"{result['years']}년 후 예상 자산", format_korean_money(round(result["projected_corpus"])))
    m2.metric("필요한 노후자금", format_korean_money(round(result["needed_corpus"])),
               help=f"은퇴 시점 월 생활비 {format_korean_money(round(result['future_monthly_expense']))} 기준 (물가상승 반영) × 12개월 × 25배")
    m3.metric("달성률", f"{result['achieved_pct']*100:.0f}%",
               delta=format_korean_money(round(result["gap"])) + (" 여유" if result["gap"] >= 0 else " 부족"))

    if result["gap"] >= 0:
        st.success(f"현재 페이스면 목표 노후자금을 달성할 수 있을 것으로 예상돼요. "
                   f"매월 {format_korean_money(round(result['required_monthly']))}만 저축해도 이론상 충분해요.")
    else:
        st.warning(f"현재 페이스로는 목표에 {format_korean_money(round(abs(result['gap'])))}만큼 부족할 것으로 예상돼요. "
                   f"목표 달성을 위해서는 매월 약 {format_korean_money(round(result['required_monthly']))}씩 저축해야 해요 "
                   f"(현재 설정: {format_korean_money(monthly_saving)}).")
    st.caption("⚠️ 실제 연금·세제 혜택(연금저축·IRP 등), 국민연금 수령액은 반영되지 않은 단순화된 교육용 계산입니다.")


# ── 📇 금융 리포트 카드 (다운로드/공유용) ──────────────────────────────────
def build_report_card_html(user, market, display_name: str = "회원") -> str:
    level, pct, next_ceil = xp_progress(user["xp"])
    hs = financial_health_score(user, market)
    persona = spending_persona(user)
    scam = scam_lab_summary(user)
    rl = user.get("risk_lab", {})
    nw = round(real_net_worth(user) + mock_total_value(user, market))
    badge_count = len(user.get("badges", []))
    today = date.today().strftime("%Y.%m.%d")
    name = html.escape(display_name or "회원")

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<title>{name}님의 머니레벨업 리포트 카드</title>
<style>
  body {{ margin:0; padding:40px; background:#F2F4F6; font-family:'Noto Sans KR',sans-serif; }}
  .card {{ max-width:640px; margin:0 auto; background:#FFFFFF; border:1px solid #E5E8EB; border-radius:20px;
           padding:34px 38px; box-shadow:0 1px 2px rgba(25,31,40,0.04); }}
  .hd {{ background:#3182F6; color:#fff; border-radius:16px;
         padding:22px 26px; margin-bottom:22px; }}
  .hd h1 {{ font-family:'Noto Sans KR',sans-serif; font-weight:800; margin:0 0 4px 0; font-size:1.4rem; }}
  .hd p {{ margin:0; opacity:.85; font-size:.85rem; }}
  .row {{ display:flex; gap:14px; margin-bottom:16px; flex-wrap:wrap; }}
  .stat {{ flex:1; min-width:130px; background:#F2F4F6; border:1px solid #E5E8EB; border-radius:14px; padding:14px 16px; }}
  .stat .k {{ font-size:.72rem; color:#4E5968; margin-bottom:4px; }}
  .stat .v {{ font-family:'Noto Sans KR',sans-serif; font-size:1.2rem; color:#191F28; font-weight:800; }}
  .section {{ margin-top:22px; }}
  .section h2 {{ font-family:'Noto Sans KR',sans-serif; font-weight:800; font-size:1.02rem; color:#191F28; border-bottom:2px solid #3182F6;
                 display:inline-block; padding-bottom:3px; margin-bottom:12px; }}
  .persona {{ display:flex; align-items:center; gap:14px; background:#E8F3FF; border:1px solid #E8F3FF;
              border-radius:14px; padding:14px 18px; }}
  .persona .icon {{ font-size:2rem; }}
  .persona .name {{ font-weight:800; color:#1B64DA; font-size:1.05rem; }}
  .persona .desc {{ font-size:.82rem; color:#4E5968; margin-top:2px; }}
  .footer {{ margin-top:26px; text-align:center; font-size:.72rem; color:#4E5968; }}
  .grade {{ display:inline-block; padding:4px 14px; border-radius:999px; font-weight:800; background:#FFF4E0; color:#F5A524; border:1px solid #FFF4E0; }}
</style></head>
<body>
  <div class="card">
    <div class="hd">
      <h1>💡 {name}님의 머니레벨업 리포트 카드</h1>
      <p>{today} 기준 · 실제 돈이 아닌 학습용 시뮬레이션 데이터입니다</p>
    </div>

    <div class="row">
      <div class="stat"><div class="k">레벨</div><div class="v">Lv.{level}</div></div>
      <div class="stat"><div class="k">누적 XP</div><div class="v">{user['xp']}</div></div>
      <div class="stat"><div class="k">획득 뱃지</div><div class="v">{badge_count}개</div></div>
      <div class="stat"><div class="k">순자산</div><div class="v">{format_korean_money(nw)}</div></div>
    </div>

    <div class="section">
      <h2>재무 건강 점수</h2>
      <p><span class="grade">{hs['grade']}등급</span> &nbsp; {hs['score']}/100점 — {hs['comment']}</p>
    </div>

    <div class="section">
      <h2>소비 페르소나</h2>
      <div class="persona">
        <div class="icon">{persona['icon']}</div>
        <div><div class="name">{persona['name']}</div><div class="desc">{persona['desc']}</div></div>
      </div>
    </div>

    <div class="section">
      <h2>🚨 리스크 체험관 성적</h2>
      <div class="row">
        <div class="stat"><div class="k">사기 대응 훈련</div><div class="v">{scam['total']}/{scam['max']}점</div></div>
        <div class="stat"><div class="k">레버리지 체험</div><div class="v">{rl.get('leverage_trials',0)}회</div></div>
        <div class="stat"><div class="k">위기 리플레이</div><div class="v">{len(rl.get('crisis_completed',{}))}/4개</div></div>
      </div>
    </div>

    <div class="footer">머니레벨업 — 사회초년생을 위한 AI 소비·투자 코칭 모의 서비스<br>실제 돈 없이, 실패해도 되는 연습장</div>
  </div>
</body></html>"""


# ── 📖 이용 가이드 ─────────────────────────────────────────────────────
def render_guide_sections(expand_first: bool = True):
    for i, sec in enumerate(GUIDE_SECTIONS):
        with st.expander(f"{sec['icon']}  {sec['title']}", expanded=(expand_first and i == 0)):
            st.markdown(f'<span class="guide-step-num">{i+1}</span>&nbsp;{sec["body"]}', unsafe_allow_html=True)
            for tip in sec.get("tips", []):
                st.caption(f"💡 {tip}")


def render_guide_tab(user):
    st.subheader("📖 이용 가이드")
    st.caption("머니레벨업의 각 기능을 처음부터 다시 훑어보고 싶을 때 여기서 확인하세요.")
    if st.button("🎬 처음 봤던 튜토리얼 화면으로 다시 보기"):
        st.session_state["_show_guide_overlay"] = True
        st.rerun()
    render_guide_sections(expand_first=False)


def render_guide_page(user, first_visit: bool):
    st.markdown(f"""<div class="guide-hero">
        <h1>📖 머니레벨업, 이렇게 써보세요</h1>
        <p>{"처음 오셨네요! 시작하기 전에 이 앱이 어떻게 구성돼 있는지 3분만 훑어볼까요?" if first_visit else "언제든 다시 볼 수 있는 이용 가이드예요."}</p>
        </div>""", unsafe_allow_html=True)

    render_guide_sections(expand_first=True)

    st.divider()
    label = "🚀 이제 시작할게요!" if first_visit else "닫고 앱으로 돌아가기"
    if st.button(label, type="primary", use_container_width=True):
        if first_visit:
            user["guide_seen"] = True
            _persist(user)
        st.session_state["_show_guide_overlay"] = False
        st.rerun()
    if first_visit:
        if st.button("나중에 볼게요 (건너뛰기)"):
            user["guide_seen"] = True
            _persist(user)
            st.rerun()


def _make_uid(name: str, birth_year: int) -> str:
    slug = "".join(ch for ch in name.strip().lower() if ch.isalnum())
    return f"{slug}_{birth_year}"


def render_signup_gate():
    st.markdown("""<div class="ml-hero">
        <div class="eyebrow">⚡ LEVEL UP JOURNEY · Lv.1 부터 시작</div>
        <h1>💡 머니레벨업</h1>
        <p>사회초년생을 위한 AI 소비·투자 코칭 모의 서비스 — 실제 돈 없이, 실패해도 되는 연습장</p>
        </div>""", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("""<div class="asset-card" style="min-height:108px">
            <div style="font-size:1.5rem">🧭</div>
            <div class="a-name" style="margin-top:4px">AI가 나의 성향을 진단</div>
            <div style="font-size:0.78rem;color:var(--ink-soft);margin-top:2px">10문항으로 투자성향·자산배분 추천</div>
            </div>""", unsafe_allow_html=True)
    with f2:
        st.markdown("""<div class="asset-card" style="min-height:108px">
            <div style="font-size:1.5rem">🚨</div>
            <div class="a-name" style="margin-top:4px">위험은 여기서 먼저 겪는다</div>
            <div style="font-size:0.78rem;color:var(--ink-soft);margin-top:2px">사기·레버리지·폭락장을 가상으로 미리 체험</div>
            </div>""", unsafe_allow_html=True)
    with f3:
        st.markdown("""<div class="asset-card" style="min-height:108px">
            <div style="font-size:1.5rem">🏅</div>
            <div class="a-name" style="margin-top:4px">기록이 곧 레벨이 된다</div>
            <div style="font-size:0.78rem;color:var(--ink-soft);margin-top:2px">가계부·저축 습관이 XP와 뱃지로 쌓임</div>
            </div>""", unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("시작하기 전에")
        if db_available():
            st.caption("계정 가입 없이, 이름·출생연도·4자리 PIN만 입력하면 돼요. 같은 이름+출생연도로 다시 오실 땐 처음 정한 PIN을 입력하면 이어서 할 수 있어요. (PIN은 동명이인끼리 데이터가 섞이지 않도록 확인하는 용도예요)")
        else:
            st.caption("⚠️ 현재 저장소(DB)가 연결되지 않아 이번 방문 동안만 데이터가 유지돼요.")
        with st.form("signup_form"):
            name = st.text_input("이름 (또는 닉네임)", placeholder="예: 김효민")
            birth_year = st.number_input("출생연도", min_value=1950, max_value=2015, value=2000, step=1)
            pin = st.text_input("4자리 PIN", placeholder="숫자 4자리, 예: 1234", max_chars=4, type="password",
                                  help="비밀번호 대신 쓰는 4자리 숫자예요. 다음에 같은 이름+출생연도로 올 때 이 PIN을 똑같이 입력해야 내 기록을 이어서 볼 수 있어요.")
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
                elif not (pin.isdigit() and len(pin) == 4):
                    st.error("PIN은 숫자 4자리로 입력해주세요.")
                else:
                    uid = _make_uid(name, int(birth_year))
                    ok, err = verify_pin(uid, pin)
                    if not ok:
                        st.error(err)
                    else:
                        st.session_state.profile = {"name": name.strip(), "birth_year": int(birth_year), "uid": uid}
                        st.session_state["_pending_initial_cash"] = int(initial_cash)
                        st.session_state["_pending_initial_savings"] = int(initial_savings)
                        st.session_state["_pending_pin"] = pin
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
                     initial_savings=st.session_state.pop("_pending_initial_savings", 0),
                     pin=st.session_state.pop("_pending_pin", None))
    market = tick_market()
    record_net_worth_point(user, market)
    newly = check_habit_badges(user, market) + check_risk_lab_badges(user)
    for bid in newly:
        st.toast(f"🏅 뱃지 획득: {BADGE_BY_ID[bid]['name']}", icon="🎉")

    if not user.get("guide_seen") or st.session_state.get("_show_guide_overlay"):
        render_guide_page(user, first_visit=not user.get("guide_seen"))
        return

    age = time.localtime().tm_year - profile["birth_year"] + 1  # 한국식 나이

    with st.sidebar:
        st.write(f"👋 **{profile['name']}**님 ({age}세)")
        if st.button("📖 이용 가이드 다시 보기", use_container_width=True):
            st.session_state["_show_guide_overlay"] = True
            st.rerun()
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
                                           min_value=0, value=max(0, int(user.get("real_cash", 0))), step=10_000,
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
        <div class="eyebrow">⚡ LEVEL UP JOURNEY · Lv.{get_level(user['xp'])}</div>
        <h1>💡 머니레벨업</h1>
        <p>{html.escape(profile['name'])}님, 오늘도 한 걸음 레벨업 해봐요</p>
        </div>""", unsafe_allow_html=True)

    render_news_ticker(market)

    tabs = st.tabs(["📖 가이드", "📊 대시보드", "🧭 투자성향", "📈 모의투자", "🧾 가계부",
                    "🎯 목표저축", "🏦 예/적금", "🚨 리스크 체험관", "🧓 노후 준비", "🤖 AI 코치", "💬 AI 상담", "🏅 뱃지"])
    with tabs[0]:
        render_guide_tab(user)
    with tabs[1]:
        render_dashboard(user, market, profile['name'])
    with tabs[2]:
        render_onboarding(user)
    with tabs[3]:
        render_invest(user, market)
    with tabs[4]:
        render_expense(user)
    with tabs[5]:
        render_goals(user)
    with tabs[6]:
        render_savings(user)
    with tabs[7]:
        render_risk_lab(user)
    with tabs[8]:
        render_retirement(user, age)
    with tabs[9]:
        render_ai_coach(user, market)
    with tabs[10]:
        render_ai_chat(user, market)
    with tabs[11]:
        render_badges(user, market, profile['name'])

    _persist(user)  # 뱃지/XP/순자산 추이 등 명시적 rerun 없이 바뀐 값도 매 실행마다 저장


if __name__ == "__main__":
    main()
