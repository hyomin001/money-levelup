# utils/config.py
import os
from datetime import timezone, timedelta

os.environ['TZ'] = 'Asia/Seoul'
KST = timezone(timedelta(hours=9))

STARTING_MOCK_CASH = 3_000_000  # 모의투자 전용 가상 시드머니 (실제 자금과 완전히 분리됨)
STARTING_REAL_CASH = 0          # 실제 자금(가계부/예적금)은 0원부터 시작 — "수입 추가"로 직접 채워나갑니다

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

# 📖 모의 호가창(주문창) 설정 — 실제 시세 연동이 아닌, 현재가 주변에 생성하는 가상 매수/매도 잔량
ORDERBOOK_LEVELS = 5          # 매수/매도 각 5호가
ORDERBOOK_TICK_RATIO = 0.0015 # 현재가 대비 한 호가 간격 비율

# 💳 소비 카테고리 (가계부 기록용) — 통계청 가계동향조사 대분류를 참고한 현실적 항목
EXPENSE_CATEGORIES = [
    {"id": "food",      "name": "식비",        "icon": "🍚", "color": "#FF8A65"},
    {"id": "cafe",       "name": "카페/간식",    "icon": "☕", "color": "#D7A86E"},
    {"id": "transport",  "name": "교통",        "icon": "🚌", "color": "#4FC3F7"},
    {"id": "living",     "name": "주거/공과금",  "icon": "🏠", "color": "#81C784"},
    {"id": "sub",        "name": "구독/멤버십",  "icon": "📺", "color": "#BA68C8"},
    {"id": "shopping",   "name": "쇼핑",        "icon": "🛍️", "color": "#F06292"},
    {"id": "leisure",    "name": "여가/문화",    "icon": "🎮", "color": "#7986CB"},
    {"id": "health",     "name": "의료/건강",    "icon": "💊", "color": "#4DB6AC"},
    {"id": "etc",        "name": "기타",        "icon": "✏️", "color": "#90A4AE"},
]

# 💵 수입 카테고리 (가계부 "수입 추가" 기능용 — 실제 자금을 채워 넣는 용도)
INCOME_CATEGORIES = [
    {"id": "salary",  "name": "월급/근로소득", "icon": "💼"},
    {"id": "allowance","name": "용돈",         "icon": "🎁"},
    {"id": "side",    "name": "부수입/알바",   "icon": "🧾"},
    {"id": "etc_in",  "name": "기타 수입",     "icon": "➕"},
]

# 20~30대 1인가구 평균 소비 비중 벤치마크 (통계청 가계동향조사 기반 추정치, 데모용 근사값)
BENCHMARK_SPENDING_RATIO = {
    "식비": 0.28, "카페/간식": 0.08, "교통": 0.09, "주거/공과금": 0.24,
    "구독/멤버십": 0.05, "쇼핑": 0.12, "여가/문화": 0.08, "의료/건강": 0.04, "기타": 0.02,
}

# 🏦 예/적금 추천 템플릿 — 사용자가 "새 예/적금 만들기"에서 이름/기간/금액을 직접 입력할 때
# 기본값을 채워주는 용도. (자유롭게 값을 바꿔 나만의 상품을 만들 수 있음)
SAVINGS_PRODUCTS = [
    {"id": "free",   "name": "자유입출금 통장",  "months": 0,  "rate": 0.001, "desc": "언제든 출금 가능, 이자 거의 없음", "icon": "💧"},
    {"id": "term6",  "name": "6개월 정기적금",   "months": 6,  "rate": 0.028, "desc": "6개월 뒤 목표 달성, 꾸준히 납입", "icon": "🌤️"},
    {"id": "term12", "name": "12개월 정기적금",  "months": 12, "rate": 0.035, "desc": "1년 뒤 목표 달성, 이자 조금 더", "icon": "🌳"},
    {"id": "term24", "name": "24개월 장기적금",  "months": 24, "rate": 0.041, "desc": "2년 뒤 목표 달성, 이자 우대", "icon": "🏔️"},
]

# 📰 시장 뉴스 템플릿 — 특정 자산 가격에 실제로 영향을 주는 이벤트
NEWS_TEMPLATES = [
    {"asset": "SEMI",      "impact": +0.035, "text": "국내 반도체 대표주, 글로벌 수요 회복 기대감에 강세"},
    {"asset": "SEMI",      "impact": -0.028, "text": "반도체 업황 둔화 우려, 대표주 투자심리 위축"},
    {"asset": "SEMI",      "impact": +0.022, "text": "차세대 공정 전환 발표에 반도체 대표주 매수세 유입"},
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

# 🧭 투자성향 진단 온보딩 설문 — 자금 성향뿐 아니라 소득/비상금/부채/지식 수준까지 폭넓게 진단
# 각 문항 점수는 1~3점, 총점 10~30점 범위 (utils/ai_coach.py의 RISK_PROFILE_PROMPT가 이 범위를 기준으로 분류)
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
    {
        "id": "income",
        "q": "현재 소득 상황은 어떤가요?",
        "options": [
            {"label": "아직 소득이 없다 (학생 등)", "score": 1},
            {"label": "불안정하지만 소득이 있다 (알바/프리랜서 등)", "score": 2},
            {"label": "매달 고정 소득이 있다", "score": 3},
        ],
    },
    {
        "id": "emergency_fund",
        "q": "비상금(생활비 3~6개월치)이 마련되어 있나요?",
        "options": [
            {"label": "전혀 없다", "score": 1},
            {"label": "조금 있지만 부족하다", "score": 2},
            {"label": "충분히 마련되어 있다", "score": 3},
        ],
    },
    {
        "id": "saving_rate",
        "q": "매달 저축/투자로 돌릴 수 있는 돈은 소득의 몇 % 정도인가요?",
        "options": [
            {"label": "10% 미만", "score": 1},
            {"label": "10~30%", "score": 2},
            {"label": "30% 이상", "score": 3},
        ],
    },
    {
        "id": "debt",
        "q": "현재 대출이나 갚아야 할 빚이 있나요?",
        "options": [
            {"label": "부담되는 수준의 빚이 있다", "score": 1},
            {"label": "적은 편이다 (학자금 등)", "score": 2},
            {"label": "없다", "score": 3},
        ],
    },
    {
        "id": "purpose",
        "q": "이 투자의 궁극적인 목적은 무엇에 가까운가요?",
        "options": [
            {"label": "단기간에 목돈을 마련하고 싶다", "score": 1},
            {"label": "내 집 마련 등 중기적인 목표가 있다", "score": 2},
            {"label": "노후 준비 등 장기적인 목표다", "score": 3},
        ],
    },
    {
        "id": "knowledge",
        "q": "주식/채권/ETF 같은 금융상품에 대한 이해도는?",
        "options": [
            {"label": "용어부터 거의 모른다", "score": 1},
            {"label": "기본 용어와 개념은 안다", "score": 2},
            {"label": "상품 구조와 위험까지 이해한다", "score": 3},
        ],
    },
]

# 🏅 습관 형성 뱃지 — 확률형 아이템이 아닌, 정해진 조건을 채우면 100% 지급되는 성취 배지
BADGES = [
    {"id": "first_record",     "name": "첫 발자국",       "icon": "🌱", "desc": "첫 지출 기록 남기기",               "xp": 10},
    {"id": "record_10",        "name": "기록 습관",        "icon": "📝", "desc": "지출 기록 10회 달성",               "xp": 30},
    {"id": "record_30",        "name": "기록 마스터",      "icon": "📚", "desc": "지출 기록 30회 달성",               "xp": 50},
    {"id": "category_master",  "name": "카테고리 정복",    "icon": "🗂️", "desc": "9개 소비 카테고리 모두 기록",        "xp": 40},
    {"id": "first_invest",     "name": "투자 데뷔",        "icon": "🎯", "desc": "첫 모의투자 매수",                  "xp": 15},
    {"id": "trade_10",         "name": "트레이더",         "icon": "📈", "desc": "매수/매도 거래 10회 달성",           "xp": 35},
    {"id": "diversified",      "name": "분산의 정석",      "icon": "🧩", "desc": "서로 다른 자산군 3개 이상 보유",     "xp": 40},
    {"id": "diversified_plus", "name": "분산 마스터",      "icon": "🌈", "desc": "서로 다른 자산군 5개 이상 보유",     "xp": 60},
    {"id": "all_assets",       "name": "올웨더 포트폴리오", "icon": "🌍", "desc": "14개 종목 전부 동시 보유",           "xp": 80},
    {"id": "profit_take",      "name": "첫 익절",          "icon": "💰", "desc": "수익 실현 매도 1회",                "xp": 25},
    {"id": "big_win",          "name": "빅 위너",          "icon": "🚀", "desc": "단일 거래 수익률 +15% 이상 매도",    "xp": 50},
    {"id": "first_saving",     "name": "저축 시작",        "icon": "🌰", "desc": "예/적금 첫 가입",                   "xp": 20},
    {"id": "multi_saving",     "name": "저축 포트폴리오",  "icon": "🏦", "desc": "예/적금 3개 이상 가입",              "xp": 45},
    {"id": "saving_1000",      "name": "백만원의 기적",    "icon": "💵", "desc": "저축 총액 100만원 돌파",             "xp": 30},
    {"id": "saving_5000",      "name": "오백만원 클럽",    "icon": "💎", "desc": "저축 총액 500만원 돌파",             "xp": 60},
    {"id": "goal_set",         "name": "목표 설정",        "icon": "🎯", "desc": "저축 목표 설정하기",                "xp": 15},
    {"id": "goal_reached",     "name": "목표 달성",        "icon": "🏆", "desc": "저축 목표 100% 달성",               "xp": 60},
    {"id": "goal_reached_x3",  "name": "목표 헌터",        "icon": "👑", "desc": "저축 목표 3회 달성",                "xp": 100},
    {"id": "ai_first",         "name": "AI와 첫 상담",     "icon": "🤖", "desc": "AI 코치 진단 첫 요청",              "xp": 20},
    {"id": "ai_veteran",       "name": "AI 단골",          "icon": "🧠", "desc": "AI 코치 진단 5회 요청",             "xp": 40},
    {"id": "risk_profile_done","name": "나를 알아가는 중", "icon": "🧭", "desc": "투자성향 진단 완료",                "xp": 20},
    {"id": "level_5",          "name": "레벨 5 달성",      "icon": "⭐", "desc": "캐릭터 레벨 5 달성",                "xp": 50},
    {"id": "level_10",         "name": "레벨 10 달성",     "icon": "🌟", "desc": "캐릭터 레벨 10 달성",               "xp": 100},
    {"id": "net_worth_500",    "name": "순자산 500만",     "icon": "📊", "desc": "순자산 500만원 돌파",               "xp": 40},
    {"id": "net_worth_1000",   "name": "순자산 1000만",    "icon": "💠", "desc": "순자산 1000만원 돌파",              "xp": 70},
    {"id": "net_worth_3000",   "name": "순자산 3000만",    "icon": "👑", "desc": "순자산 3000만원 돌파",              "xp": 120},
]

# 레벨업에 필요한 누적 XP (레벨 1~15)
LEVEL_XP_TABLE = [0, 30, 70, 130, 220, 340, 500, 720, 1000, 1400, 1900, 2500, 3200, 4000, 5000]
