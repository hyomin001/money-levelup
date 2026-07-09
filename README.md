# 💡 머니레벨업 (Money Level-Up)

사회초년생을 위한 AI 소비·투자 코칭 모의 서비스.
K-AI Contents Award 솔루션 부문 제출용.

hyomin-portal(효민 포털)의 검증된 백엔드 패턴(MongoDB atomic 연산, bcrypt 인증, 금액 포맷 유틸)을
재사용하되, 판타지 게임 요소(무기 강화, 가챠, 길드전 등)는 전부 제거하고
현실적인 금액 단위와 실사용 가능한 UI로 새로 구성했습니다.

---

## 1. 로컬 실행

```bash
pip install -r requirements.txt
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# secrets.toml 안의 MONGO_URI, ANTHROPIC_API_KEY 채우기
streamlit run app.py
```

## 2. Streamlit Community Cloud 배포 (제출용 URL 만들기)

1. 이 폴더를 GitHub 레포로 push (public 또는 private + Streamlit 연결)
2. https://share.streamlit.io 에서 New app → 레포 선택 → main file: `app.py`
3. App settings → Secrets 에 `secrets.toml.example` 내용을 채워서 붙여넣기
   - `MONGO_URI`: MongoDB Atlas 무료 클러스터 연결 문자열 (효민 포털에서 쓰던 것과 별도 클러스터/DB 권장)
   - `ANTHROPIC_API_KEY`: console.anthropic.com 에서 발급
4. Deploy → 나온 `https://xxxx.streamlit.app` URL을 공모전 지원서에 제출

---

## 3. 지원서 작성용 초안

### 어떤 불편함을 해결하려 했는가
사회초년생·자취생은 소비 습관과 투자 지식이 미분리된 상태로 "일단 벌고 일단 쓰는" 패턴에
빠지기 쉽습니다. 가계부 앱은 기록만 해주고, 증권 앱은 실전 투자만 다뤄서, 두 데이터를
연결해 "내가 지금 재정적으로 어떤 상태인지" 종합적으로 알려주는 도구가 없습니다.
머니레벨업은 모의투자·가계부·예적금 데이터를 한 곳에 모으고, AI가 이를 종합 진단해
실행 가능한 다음 행동을 제안합니다.

### AI를 어떻게 활용했는가
- 사용자의 최근 소비 내역(카테고리별 합계), 모의투자 포트폴리오(자산군별 평가액),
  저축 현황을 JSON으로 구조화해 Claude API에 전달
- Claude가 이를 분석해 ①소비 패턴 진단 ②포트폴리오 분산 여부 ③비상금 필요성
  ④실행 가능한 행동 3가지를 JSON 스키마로 반환하도록 설계
- 단순 챗봇형 Q&A가 아니라, 정형 데이터 → 구조화된 진단 리포트를 만드는 방식으로
  "숫자 뒤에 숨은 습관"을 사용자가 스스로 읽게 만드는 데 초점

### 핵심 프롬프트 (`utils/ai_coach.py` SYSTEM_PROMPT 발췌)
> 사용자의 최근 소비 내역, 모의투자 포트폴리오, 저축 현황(JSON)을 보고
> 숫자를 근거로 구체적으로 말하고, 비난하지 않고 실행 가능한 다음 행동을 제안하며,
> 특정 자산군에 쏠려 있으면 분산 관점에서 짚어주고, 저축이 없으면 비상금의
> 필요성을 언급하도록 지시. 응답은 반드시 고정 JSON 스키마로 반환.

(전체 프롬프트는 `utils/ai_coach.py` 참고)

---

## 4. 폴더 구조

```
app.py                  메인 앱 (대시보드/모의투자/가계부/예적금/AI코치 탭)
utils/config.py         자산·소비카테고리·예적금 상품 설정 (현실적 금액 단위)
utils/core.py           인증, 금액 포맷, 시세 랜덤워크, 순자산 계산
utils/database.py       MongoDB 연동 (효민 포털의 atomic 캐시 패턴 재사용)
utils/ai_coach.py       Claude API 호출 — AI 진단 생성 (공모전 핵심 기능)
```

## 5. 제출 전 체크리스트

- [ ] Streamlit Cloud 배포 후 URL 접속 테스트 (회원가입 → 모의투자 → 가계부 → AI 진단까지 한 번 실행)
- [ ] MongoDB Atlas 클러스터가 효민 포털과 별도 DB(`money_levelup`)를 쓰는지 확인
- [ ] ANTHROPIC_API_KEY 유효성 확인 (AI 코치 탭에서 실제로 진단이 나오는지)
- [ ] 지원서에 위 3번 섹션 내용 반영
- [ ] 데모 시연용으로 미리 몇 건의 소비/투자 기록을 넣어둔 테스트 계정 하나 준비
      (심사위원이 빈 화면만 보고 판단하지 않도록)
