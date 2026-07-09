# utils/config.py
import os
from datetime import timezone, timedelta

os.environ['TZ'] = 'Asia/Seoul'
KST = timezone(timedelta(hours=9))

STARTING_CASH = 3_000_000  # 신규 유저 시작 자금: 300만원 (현실적인 사회초년생 종잣돈 규모)

# 📈 모의투자 종목 — 실제 자산군을 본뜬 가상 티커, 가격은 현실적인 원 단위
# (실제 시세 연동이 아닌 랜덤워크+뉴스이벤트 시뮬레이션이며, 앱 내에 명시)
ASSET_CONFIG = [
    {"id": "KODEX200",  "name": "KODEX 200 ETF",       "type": "국내ETF", "vol": 0.012, "icon": "📊"},
    {"id": "KOSDAQ150", "name": "KODEX 코스닥150",       "type": "국내ETF", "vol": 0.017, "icon": "📈"},
    {"id": "NASDAQ100", "name": "TIGER 나스닥100",       "type": "해외ETF", "vol": 0.016, "icon": "🇺🇸"},
    {"id": "SP500",     "name": "TIGER S&P500",         "type": "해외ETF", "vol": 0.013, "icon": "🗽"},
    {"id": "SEMI",      "name": "국내 반도체 대표주",     "type": "주식",   "vol": 0.022, "icon": "💾"},
    {"id": "BATT",      "name": "2차전지 대표주",        "type": "주식",   "vol": 0.028, "icon": "🔋"},
    {"id": "BIOH",      "name": "바이오헬스 대표주",      "type": "주식",   "vol": 0.030, "icon": "🧬"},
    {"id": "PLAT",      "name": "플랫폼 대표주",         "type": "주식",   "vol": 0.024, "icon": "📱"},
    {"id": "BOND",      "name": "국고채 ETF",            "type": "채권",   "vol": 0.004, "icon": "📜"},
    {"id": "USBOND",    "name": "미국 장기채 ETF",       "type": "채권",   "vol": 0.007, "icon": "🏦"},
    {"id": "GOLD",      "name": "금 현물 ETF",           "type": "원자재", "vol": 0.010, "icon": "🪙"},
    {"id": "OIL",       "name": "원유 선물 ETF",         "type": "원자재", "vol": 0.026, "icon": "🛢️"},
    {"id": "REIT",      "name": "리츠(부동산) ETF",       "type": "리츠",   "vol": 0.009, "icon": "🏢"},
    {"id": "DIGITAL",   "name": "디지털자산 ETF",        "type": "대체자산", "vol": 0.045, "icon": "🌐"},
]

ASSET_BASE_PRICE = {
    "KODEX200": 38_000, "KOSDAQ150": 14_200, "NASDAQ100": 21_000, "SP500": 19_500,
    "SEMI": 92_000, "BATT": 61_000, "BIOH": 45_000, "PLAT": 53_000,
    "BOND": 105_000, "USBOND": 41_000, "GOLD": 78_000, "OIL": 27_500,
    "REIT": 12_500, "DIGITAL": 33_000,
}

# 💳 소비 카테고리 (가계부 기록용) — 통계청 가계동향조사 대분류를 참고한 현실적 항목
EXPENSE_CATEGORIES = [
    {"id": "food",      "name": "식비",        "icon": "🍚"},
    {"id": "cafe",       "name": "카페/간식",    "icon": "☕"},
    {"id": "transport",  "name": "교통",        "icon": "🚌"},
    {"id": "living",     "name": "주거/공과금",  "icon": "🏠"},
    {"id": "sub",        "name": "구독/멤버십",  "icon": "📺"},
    {"id": "shopping",   "name": "쇼핑",        "icon": "🛍️"},
    {"id": "leisure",    "name": "여가/문화",    "icon": "🎮"},
    {"id": "health",     "name": "의료/건강",    "icon": "💊"},
    {"id": "etc",        "name": "기타",        "icon": "✏️"},
]

# 20~30대 1인가구 평균 소비 비중 벤치마크 (통계청 가계동향조사 기반 추정치, 데모용 근사값)
BENCHMARK_SPENDING_RATIO = {
    "식비": 0.28, "카페/간식": 0.08, "교통": 0.09, "주거/공과금": 0.24,
    "구독/멤버십": 0.05, "쇼핑": 0.12, "여가/문화": 0.08, "의료/건강": 0.04, "기타": 0.02,
}

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
    {"asset": "PLAT",      "impact": +0.03,  "text": "플랫폼 대표주, 신규 서비스 출시에 강세"},
    {"asset": "PLAT",      "impact": -0.025, "text": "플랫폼 규제 우려에 관련주 조정"},
    {"asset": "NASDAQ100", "impact": +0.025, "text": "미 증시 강세에 나스닥100 ETF 동반 상승"},
    {"asset": "NASDAQ100", "impact": -0.025, "text": "美 금리 우려 재부각, 나스닥100 ETF 조정"},
    {"asset": "SP500",     "impact": +0.02,  "text": "S&P500 사상 최고치 경신에 관련 ETF 강세"},
    {"asset": "KODEX200",  "impact": +0.018, "text": "코스피 상승 마감, KODEX 200 ETF 동반 강세"},
    {"asset": "KODEX200",  "impact": -0.018, "text": "외국인 매도세에 코스피 약세, KODEX 200 ETF 하락"},
    {"asset": "KOSDAQ150", "impact": -0.03,  "text": "코스닥 변동성 확대, 중소형주 ETF 약세"},
    {"asset": "GOLD",      "impact": +0.02,  "text": "안전자산 선호 심리 확대, 금 현물 ETF 상승"},
    {"asset": "OIL",       "impact": +0.035, "text": "지정학적 리스크에 원유 ETF 급등"},
    {"asset": "OIL",       "impact": -0.03,  "text": "수요 둔화 우려에 원유 ETF 하락"},
    {"asset": "REIT",      "impact": +0.015, "text": "금리 인하 기대감에 리츠 ETF 강세"},
    {"asset": "REIT",      "impact": -0.02,  "text": "부동산 경기 둔화 우려에 리츠 ETF 약세"},
    {"asset": "DIGITAL",   "impact": +0.06,  "text": "디지털자산 ETF, 글로벌 자금 유입에 급등"},
    {"asset": "DIGITAL",   "impact": -0.055, "text": "디지털자산 ETF, 규제 우려에 급락"},
    {"asset": "BOND",      "impact": +0.006, "text": "안전자산 수요 증가, 국고채 ETF 소폭 상승"},
    {"asset": "USBOND",    "impact": +0.008, "text": "美 금리 인하 기대에 장기채 ETF 상승"},
]

# 🧭 투자성향 진단 온보딩 설문 (AI 코치가 결과를 분석해 추천 자산배분 제시)
ONBOARDING_QUESTIONS = [
    {
        "id": "horizon",
        "q": "지금 모의투자로 굴릴 돈, 언제쯤 쓸 계획인가요?",
        "options": [
            {"label": "1년 안에 쓸 수도 있어요", "score": 1},
            {"label": "1~3년은 안 건드릴 것 같아요", "score": 2},
            {"label": "3년 이상 그냥 묻어둘 생각이에요", "score": 3},
        ],
    },
    {
        "id": "reaction",
        "q": "투자한 돈이 한 달 만에 -15% 됐다면?",
        "options": [
            {"label": "바로 다 팔고 정리한다", "score": 1},
            {"label": "불안하지만 좀 더 지켜본다", "score": 2},
            {"label": "오히려 추가 매수를 고민한다", "score": 3},
        ],
    },
    {
        "id": "goal",
        "q": "이 돈으로 가장 하고 싶은 건?",
        "options": [
            {"label": "절대 잃지 않고 지키고 싶다", "score": 1},
            {"label": "적당히 불리면서 안정도 챙기고 싶다", "score": 2},
            {"label": "크게 불려보고 싶다", "score": 3},
        ],
    },
    {
        "id": "experience",
        "q": "실제 투자 경험은 어느 정도인가요?",
        "options": [
            {"label": "거의 없다", "score": 1},
            {"label": "예적금 위주로 조금 해봤다", "score": 2},
            {"label": "주식/펀드 등을 실제로 운용해봤다", "score": 3},
        ],
    },
]

# 🏅 습관 형성 뱃지 — 확률형 아이템이 아닌, 정해진 조건을 채우면 100% 지급되는 성취 배지
BADGES = [
    {"id": "first_record",  "name": "첫 발자국",     "icon": "🌱", "desc": "첫 지출 기록 남기기",           "xp": 10},
    {"id": "record_10",     "name": "기록 습관",      "icon": "📝", "desc": "지출 기록 10회 달성",           "xp": 30},
    {"id": "first_invest",  "name": "투자 데뷔",      "icon": "🎯", "desc": "첫 모의투자 매수",              "xp": 15},
    {"id": "diversified",   "name": "분산의 정석",    "icon": "🧩", "desc": "서로 다른 자산군 3개 이상 보유", "xp": 40},
    {"id": "first_saving",  "name": "저축 시작",      "icon": "🌰", "desc": "예/적금 첫 가입",               "xp": 20},
    {"id": "goal_set",      "name": "목표 설정",      "icon": "🎯", "desc": "저축 목표 설정하기",            "xp": 15},
    {"id": "goal_reached",  "name": "목표 달성",      "icon": "🏆", "desc": "저축 목표 100% 달성",           "xp": 60},
    {"id": "ai_first",      "name": "AI와 첫 상담",   "icon": "🤖", "desc": "AI 코치 진단 첫 요청",          "xp": 20},
]

LEVEL_XP_TABLE = [0, 30, 70, 130, 220, 340, 500, 720, 1000, 1400]  # 레벨업에 필요한 누적 XP
