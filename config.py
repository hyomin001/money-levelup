# Streamlit Cloud > App settings > Secrets 에 아래 내용을 붙여넣고 값 채우기

# Gemini API 키 (https://aistudio.google.com/apikey 에서 무료 발급)
GEMINI_API_KEY = "여기에 실제 발급받은 키를 붙여넣으세요"

# 로그인 지속성을 위한 MongoDB 연결 문자열.
# 효민 포털에서 쓰던 MongoDB Atlas 연결 문자열을 그대로 복사해서 붙여넣으면 됩니다.
# (DB 이름은 코드에서 "money_levelup"으로 이미 분리되어 있어 데이터가 섞이지 않아요)
# 이 값을 비워두거나 아예 빼도 앱은 정상 작동하며, 이 경우 새로고침 시 데이터가 초기화됩니다.
MONGO_URI = "여기에 실제 mongodb+srv://... 연결 문자열을 붙여넣으세요"
