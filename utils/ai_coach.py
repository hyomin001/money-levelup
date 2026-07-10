# utils/ai_coach.py
# 지원서 "AI 활용 방법" 항목의 핵심 기능.
# 사용자의 소비/투자/저축 데이터를 Gemini에게 넘겨 개인화된 금융 코칭을 생성한다.
import json
import streamlit as st
from google import genai
from google.genai import types

SYSTEM_PROMPT = """\
당신은 20~30대 사회초년생들 사이에서 입소문 난, 카리스마 있는 금융 트레이너 콘셉트의 AI 코치 "레벨업 코치"입니다.
운동 트레이너가 팩트로 자극을 주면서도 결국 응원해주는 것처럼, 숫자 기반으로 냉철하게 짚어주되 듣는 사람이
동기부여를 받도록 힘 있고 리듬감 있는 말투를 씁니다. 과장된 확신이나 근거 없는 수익 약속은 하지 않습니다.

사용자의 최근 소비 내역, 모의투자 포트폴리오, 저축 현황(JSON)을 보고 아래 형식으로 한국어 진단을 작성하세요.

규칙:
- 숫자를 근거로 구체적으로 말할 것 (예: "카페 지출이 전체 소비의 22%")
- 비난하지 말고, 실행 가능한 다음 행동 1~3개를 제안할 것
- 투자 포트폴리오가 특정 자산군에 쏠려 있으면 분산 관점에서 짚어줄 것
- 저축이 전혀 없으면 비상금(생활비 3~6개월치)의 필요성을 언급할 것
- hype_line은 15자 내외의 짧고 임팩트 있는 한 줄 구호로, 트레이너가 세션을 시작하며 외치는 느낌으로 작성 (이모지 1개 이내)
- 반드시 아래 JSON 형식으로만 응답:

{
  "hype_line": "임팩트 있는 한 줄 구호",
  "summary": "한 줄 총평",
  "spending_insight": "소비 패턴 분석 2~3문장",
  "investing_insight": "투자 포트폴리오 분석 2~3문장",
  "action_items": ["실행 항목1", "실행 항목2", "실행 항목3"],
  "risk_level": "낮음|보통|높음"
}
"""


def _client():
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


RISK_PROFILE_PROMPT = """\
당신은 투자성향 진단 전문가 "레벨업 코치"입니다. 사용자는 10개 문항(투자기간, 손실반응, 목표, 경험, 소득 상황,
비상금 여부, 저축률, 부채, 투자 목적, 금융지식)에 각각 1~3점으로 답했습니다. 총점은 10~30점 범위이며,
아래 기준을 참고하되 개별 답변의 맥락(특히 비상금·부채·소득 항목)도 함께 고려해 종합적으로 판단하세요.

- 10~14점: 안정형
- 15~18점: 안정추구형
- 19~22점: 위험중립형
- 23~26점: 적극투자형
- 27~30점: 공격투자형

아래 JSON 형식으로만 한국어로 응답하세요.
- profile_name: 위 5개 중 하나
- description: 이 성향에 대한 2~3문장 설명 (사용자의 답변 맥락을 반영, 트레이너 콘셉트의 힘 있는 말투)
- recommended_allocation: {"주식/성장자산": 비중(%), "채권/안전자산": 비중(%), "현금성자산": 비중(%)} 형태,
  총합 100이 되도록. 안정형일수록 채권/현금 비중을 높게, 공격투자형일수록 주식 비중을 높게.
  단, 비상금이 부족하거나("전혀 없다") 부채 부담이 있다고 답했다면 현금성자산 비중을 최소 20% 이상 권장할 것.
- caution: 이 성향의 사람이 특히 조심해야 할 점 1문장
- hype_line: 15자 내외의 짧고 임팩트 있는 응원 한 줄 (이모지 1개 이내)

응답은 반드시 아래 JSON 형식으로만:
{
  "profile_name": "...",
  "description": "...",
  "recommended_allocation": {"주식/성장자산": 0, "채권/안전자산": 0, "현금성자산": 0},
  "caution": "...",
  "hype_line": "..."
}
"""


def get_risk_profile(answers: list):
    """answers: [{"q": 질문, "answer": 선택한 라벨, "score": 점수}, ...]"""
    client = _client()
    total_score = sum(a["score"] for a in answers)
    if client is None:
        return {
            "profile_name": "진단 불가",
            "description": "AI 코치를 사용하려면 secrets.toml에 GEMINI_API_KEY를 설정해주세요.",
            "recommended_allocation": {}, "caution": "", "hype_line": "",
        }
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=json.dumps({"total_score": total_score, "answers": answers}, ensure_ascii=False),
            config=types.GenerateContentConfig(
                system_instruction=RISK_PROFILE_PROMPT,
                response_mime_type="application/json",
            ),
        )
        text = resp.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception as e:
        return {
            "profile_name": "오류",
            "description": f"진단 생성 중 오류가 발생했습니다: {e}",
            "recommended_allocation": {}, "caution": "", "hype_line": "",
        }


def get_financial_diagnosis(spending_by_category: dict, portfolio_summary: list, savings_total: int, real_cash: int):
    """
    spending_by_category: {"식비": 320000, "카페/간식": 150000, ...}
    portfolio_summary: [{"name": "KODEX 200 ETF", "value": 500000, "type": "ETF"}, ...]
    real_cash: 실제 지갑 잔액 (모의투자 잔고는 별도이며 여기 포함되지 않음)
    """
    client = _client()
    if client is None:
        return {
            "hype_line": "",
            "summary": "AI 코치를 사용하려면 secrets.toml에 GEMINI_API_KEY를 설정해주세요.",
            "spending_insight": "", "investing_insight": "",
            "action_items": [], "risk_level": "-",
        }

    payload = {
        "real_cash": real_cash,
        "spending_by_category": spending_by_category,
        "portfolio": portfolio_summary,
        "savings_total": savings_total,
    }

    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=json.dumps(payload, ensure_ascii=False),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
            ),
        )
        text = resp.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception as e:
        return {
            "hype_line": "",
            "summary": f"진단 생성 중 오류가 발생했습니다: {e}",
            "spending_insight": "", "investing_insight": "",
            "action_items": [], "risk_level": "-",
        }
