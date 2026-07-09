# utils/config.py
import os
from datetime import timezone, timedelta

os.environ['TZ'] = 'Asia/Seoul'
KST = timezone(timedelta(hours=9))

STARTING_CASH = 3_000_000  # 신규 유저 시작 자금: 300만원 (현실적인 사회초년생 종잣돈 규모)

# 📈 모의투자 종목 — 실제 자산군을 본뜬 가상 티커, 가격은 현실적인 원 단위
# (실제 시세 연동이 아닌 랜덤워크 시뮬레이션이며, 앱 내에 명시)
ASSET_CONFIG = [
    {"id": "KODEX200",  "name": "KODEX 200 ETF",        "type": "ETF",  "vol": 0.012, "icon": "📊"},
    {"id": "NASDAQ100",  "name": "TIGER 나스닥100",       "type": "ETF",  "vol": 0.016, "icon": "🇺🇸"},
    {"id": "SEMI",       "name": "국내 반도체 대표주",     "type": "주식", "vol": 0.022, "icon": "💾"},
    {"id": "BATT",       "name": "2차전지 대표주",        "type": "주식", "vol": 0.028, "icon": "🔋"},
    {"id": "BIOH",       "name": "바이오헬스 대표주",      "type": "주식", "vol": 0.030, "icon": "🧬"},
    {"id": "BOND",       "name": "국고채 ETF",            "type": "채권", "vol": 0.004, "icon": "📜"},
    {"id": "GOLD",       "name": "금 현물 ETF",           "type": "원자재", "vol": 0.010, "icon": "🪙"},
    {"id": "REIT",       "name": "리츠(부동산) ETF",       "type": "리츠", "vol": 0.009, "icon": "🏢"},
]

# 시작 가격대: 1만원 ~ 15만원 (실제 국내 ETF/우량주 가격대와 유사하게)
ASSET_BASE_PRICE = {
    "KODEX200": 38_000, "NASDAQ100": 21_000, "SEMI": 92_000, "BATT": 61_000,
    "BIOH": 45_000, "BOND": 105_000, "GOLD": 78_000, "REIT": 12_500,
}

# 💳 소비 카테고리 (가계부 기록용)
EXPENSE_CATEGORIES = [
    {"id": "food",      "name": "식비",        "icon": "🍚"},
    {"id": "cafe",       "name": "카페/간식",    "icon": "☕"},
    {"id": "transport",  "name": "교통",        "icon": "🚌"},
    {"id": "living",     "name": "주거/공과금",  "icon": "🏠"},
    {"id": "sub",        "name": "구독/멤버십",  "icon": "📺"},
    {"id": "shopping",   "name": "쇼핑",        "icon": "🛍️"},
    {"id": "leisure",    "name": "여가/문화",    "icon": "🎮"},
    {"id": "etc",        "name": "기타",        "icon": "✏️"},
]

# 🏦 예/적금 상품 (단순 이자 시뮬레이션)
SAVINGS_PRODUCTS = [
    {"id": "free",   "name": "자유입출금",     "rate": 0.001, "desc": "언제든 출금 가능, 이자 거의 없음"},
    {"id": "term6",  "name": "6개월 정기예금",  "rate": 0.028, "desc": "6개월 뒤 원금+이자 수령, 중도해지 시 이자 손해"},
    {"id": "term12", "name": "12개월 정기예금", "rate": 0.035, "desc": "1년 뒤 원금+이자 수령, 중도해지 시 이자 손해"},
]

# 📰 시장 뉴스 템플릿 — 특정 자산 가격에 실제로 영향을 주는 이벤트
NEWS_TEMPLATES = [
    {"asset": "SEMI",      "impact": +0.035, "text": "국내 반도체 대표주, 글로벌 수요 회복 기대감에 강세"},
    {"asset": "SEMI",      "impact": -0.028, "text": "반도체 업황 둔화 우려, 대표주 투자심리 위축"},
    {"asset": "BATT",      "impact": +0.04,  "text": "2차전지 대표주, 해외 수주 소식에 급등"},
    {"asset": "BATT",      "impact": -0.035, "text": "원자재 가격 상승에 2차전지株 수익성 우려 확대"},
    {"asset": "BIOH",      "impact": +0.045, "text": "바이오헬스 대표주, 신약 임상 기대감에 매수세 유입"},
    {"asset": "BIOH",      "impact": -0.03,  "text": "임상 지연 소식에 바이오株 하락"},
    {"asset": "NASDAQ100", "impact": +0.025, "text": "미 증시 강세에 나스닥100 ETF 동반 상승"},
    {"asset": "NASDAQ100", "impact": -0.025, "text": "美 금리 우려 재부각, 나스닥100 ETF 조정"},
    {"asset": "KODEX200",  "impact": +0.018, "text": "코스피 상승 마감, KODEX 200 ETF 동반 강세"},
    {"asset": "KODEX200",  "impact": -0.018, "text": "외국인 매도세에 코스피 약세, KODEX 200 ETF 하락"},
    {"asset": "GOLD",      "impact": +0.02,  "text": "안전자산 선호 심리 확대, 금 현물 ETF 상승"},
    {"asset": "REIT",      "impact": +0.015, "text": "금리 인하 기대감에 리츠 ETF 강세"},
    {"asset": "REIT",      "impact": -0.02,  "text": "부동산 경기 둔화 우려에 리츠 ETF 약세"},
    {"asset": "BOND",      "impact": +0.006, "text": "안전자산 수요 증가, 국고채 ETF 소폭 상승"},
]

