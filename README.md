# utils/ai_coach.py
# 지원서 "AI 활용 방법" 항목의 핵심 기능.
# 사용자의 소비/투자/저축 데이터를 Gemini에게 넘겨 개인화된 금융 코칭을 생성한다.
import json
import streamlit as st
from google import genai
from google.genai import types

SYSTEM_PROMPT = """\
당신은 20~30대 사회초년생을 위한 다정하지만 냉정한 금융 코치입니다.
사용자의 최근 소비 내역, 모의투자 포트폴리오, 저축 현황(JSON)을 보고 아래 형식으로 한국어 진단을 작성하세요.

규칙:
- 숫자를 근거로 구체적으로 말할 것 (예: "카페 지출이 전체 소비의 22%")
- 비난하지 말고, 실행 가능한 다음 행동 1~3개를 제안할 것
- 투자 포트폴리오가 특정 자산군에 쏠려 있으면 분산 관점에서 짚어줄 것
- 저축이 전혀 없으면 비상금(생활비 3~6개월치)의 필요성을 언급할 것
- 반드시 아래 JSON 형식으로만 응답:

{
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
당신은 투자성향 진단 전문가입니다. 사용자가 5점 척도가 아닌 4개 문항(투자기간, 손실반응, 목표, 경험)에
답한 점수 합계(4~12점)와 각 답변 내용을 보고, 아래 JSON 형식으로만 한국어로 응답하세요.

- profile_name: "안정형" | "안정추구형" | "위험중립형" | "적극투자형" | "공격투자형" 중 점수에 맞는 하나
  (4~5점: 안정형, 6~7점: 안정추구형, 8~9점: 위험중립형, 10~11점: 적극투자형, 12점: 공격투자형)
- description: 이 성향에 대한 2~3문장 설명 (사용자의 답변 맥락을 반영)
- recommended_allocation: {"주식/성장자산": 비중(%), "채권/안전자산": 비중(%), "현금성자산": 비중(%)} 형태,
  총합 100이 되도록. 안정형일수록 채권/현금 비중을 높게, 공격투자형일수록 주식 비중을 높게.
- caution: 이 성향의 사람이 특히 조심해야 할 점 1문장

응답은 반드시 아래 JSON 형식으로만:
{
  "profile_name": "...",
  "description": "...",
  "recommended_allocation": {"주식/성장자산": 0, "채권/안전자산": 0, "현금성자산": 0},
  "caution": "..."
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
            "recommended_allocation": {}, "caution": "",
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
            "recommended_allocation": {}, "caution": "",
        }
def get_financial_diagnosis(spending_by_category: dict, portfolio_summary: list, savings_total: int, cash: int):
    """
    spending_by_category: {"식비": 320000, "카페/간식": 150000, ...}
    portfolio_summary: [{"name": "KODEX 200 ETF", "value": 500000, "type": "ETF"}, ...]
    """
    client = _client()
    if client is None:
        return {
            "summary": "AI 코치를 사용하려면 secrets.toml에 GEMINI_API_KEY를 설정해주세요.",
            "spending_insight": "", "investing_insight": "",
            "action_items": [], "risk_level": "-",
        }

    payload = {
        "cash": cash,
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
            "summary": f"진단 생성 중 오류가 발생했습니다: {e}",
            "spending_insight": "", "investing_insight": "",
            "action_items": [], "risk_level": "-",
        }
