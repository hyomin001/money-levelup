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


# google-genai SDK는 http_options.retry_options를 명시적으로 넘기지 않으면
# "재시도 없음"이 기본값이다 (내부적으로 tenacity.stop_after_attempt(1)).
# 그래서 지금까지는 일시적인 429(rate limit)/5xx/타임아웃 오류가 나면 바로 실패로
# 처리되어 "오류가 발생했습니다" 메시지가 그대로 화면에 떴고, 사용자가 버튼을
# 2~3번 다시 눌러야 그중 한 번이 우연히 성공하는 것처럼 보였던 것.
# 아래처럼 재시도 정책 + 타임아웃을 명시하면 이런 일시적 오류는 SDK가 내부적으로
# 자동 재시도하므로, 사용자가 직접 여러 번 시도할 필요가 없어진다.
_RETRY_OPTIONS = types.HttpRetryOptions(
    attempts=4,            # 최초 요청 포함 최대 4회 시도
    initial_delay=1.0,     # 첫 재시도까지 1초 대기
    max_delay=8.0,         # 재시도 간 대기는 최대 8초
    exp_base=2.0,
    jitter=1.0,
    http_status_codes=[408, 429, 500, 502, 503, 504],
)


@st.cache_resource
def _client():
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        return None
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=30_000,  # ms 단위. 응답이 없을 때 무한정 기다리지 않도록 30초 제한
            retry_options=_RETRY_OPTIONS,
        ),
    )


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


REPORT_PROMPT = """\
당신은 "레벨업 코치"입니다. 사용자의 재무 데이터(가계부, 모의투자, 저축, 재무 건강 점수, 다음 달 지출 예측이 담긴 JSON)를
바탕으로, 인쇄해서 보관할 수 있는 개인 맞춤 재무 리포트를 마크다운으로 작성하세요.

반드시 아래 섹션 구조를 지키고, 각 섹션에 숫자 근거를 인용하며 실행 가능한 조언을 담으세요. 과장된 확신이나 근거 없는
수익 약속은 하지 않습니다. 마크다운 헤더(#, ##)를 사용하고, 표가 유용하면 마크다운 표를 사용해도 됩니다.

# 📑 이번 달 재무 리포트
## 1. 총평
## 2. 재무 건강 점수 해설 (점수 구성 항목별로 왜 그 점수인지 설명)
## 3. 소비 패턴 분석 (카테고리별 비중, 다음 달 지출 예측과 이상 여부 포함)
## 4. 투자 포트폴리오 분석 (분산 정도, 위험도)
## 5. 저축·목표 진행 상황
## 6. 다음 30일 실행 플랜 (체크리스트 형태로 3~5개)

응답은 마크다운 텍스트만 반환하고, JSON이나 코드블록 표시(```) 없이 바로 본문으로 시작하세요.
"""


def _fallback_report(data: dict) -> str:
    """API 키가 없을 때도 항상 동작하는 규칙 기반 리포트 (형식은 AI 버전과 동일하게 유지)."""
    fh = data.get("financial_health", {})
    forecast = data.get("forecast", {})
    lines = [
        "# 📑 이번 달 재무 리포트 (오프라인 요약본)",
        "",
        "> ⚠️ GEMINI_API_KEY가 설정되지 않아 AI 서술형 리포트 대신 규칙 기반 요약을 보여드려요.",
        "",
        "## 1. 총평",
        f"- 재무 건강 점수: **{fh.get('score', '-')}점 ({fh.get('grade', '-')}등급)** — {fh.get('comment', '')}",
        "",
        "## 2. 재무 건강 점수 구성",
    ]
    for b in fh.get("breakdown", []):
        lines.append(f"- {b['key']}: {b['points']}/{b['max']}점 — {b['detail']}")
    lines += ["", "## 3. 다음 달 지출 예측"]
    if forecast:
        lines.append(f"- 예상 지출액: 약 {forecast.get('forecast', 0):,}원"
                      + (" (⚠️ 최근 지출이 평소보다 크게 늘었어요)" if forecast.get("anomaly") else ""))
    else:
        lines.append("- 아직 예측할 만큼의 가계부 기록이 없어요.")
    lines += ["", "## 4. 실행 플랜", "- [ ] 이번 달 지출을 카테고리별로 다시 점검하기",
              "- [ ] 비상금 3개월치 목표를 세우기", "- [ ] 포트폴리오 분산 상태 점검하기"]
    return "\n".join(lines)


def get_full_report(data: dict) -> str:
    """data: {financial_health, forecast, spending_by_category, portfolio, savings_total, real_cash} 등을 담은 dict"""
    client = _client()
    if client is None:
        return _fallback_report(data)
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=json.dumps(data, ensure_ascii=False),
            config=types.GenerateContentConfig(system_instruction=REPORT_PROMPT),
        )
        text = resp.text.strip()
        return text if text else _fallback_report(data)
    except Exception as e:
        return _fallback_report(data) + f"\n\n> (AI 리포트 생성 중 오류가 발생해 요약본으로 대체했어요: {e})"


CHAT_SYSTEM_PROMPT = """\
당신은 "레벨업 코치"입니다. 사용자의 실제 재무 데이터(JSON, 매 턴 제공됨)를 참고 자료로 삼아, 자유로운 질문에
대화형으로 답합니다. 숫자 근거를 들어 구체적으로 답하고, 실행 가능한 제안을 하되 과장된 확신이나 근거 없는 수익
약속은 하지 않습니다. 답변은 3~6문장 내외로 간결하게, 한국어로, 트레이너 콘셉트의 힘 있는 말투를 유지합니다.
사용자의 재무 상황과 무관한 일반 상식 질문에는 짧게만 답하고 다시 재무 주제로 자연스럽게 돌아오세요.
"""


def chat_with_coach(history: list, user_context: dict) -> str:
    """history: [{"role": "user"|"model", "text": ...}, ...] (마지막 항목이 이번 사용자 질문)
    user_context: 가계부/투자/저축 요약 dict — 매 턴 최신 데이터를 함께 전달해 근거 있는 답변을 만든다."""
    client = _client()
    if client is None:
        return "AI 코치를 사용하려면 secrets.toml에 GEMINI_API_KEY를 설정해주세요."
    try:
        contents = [types.Content(role=("user" if h["role"] == "user" else "model"),
                                    parts=[types.Part(text=h["text"])]) for h in history[:-1]]
        last_q = history[-1]["text"]
        contents.append(types.Content(role="user", parts=[types.Part(
            text=f"[참고용 재무 데이터]\n{json.dumps(user_context, ensure_ascii=False)}\n\n[질문]\n{last_q}"
        )]))
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=CHAT_SYSTEM_PROMPT),
        )
        return resp.text.strip()
    except Exception as e:
        return f"답변 생성 중 오류가 발생했어요: {e}"


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
