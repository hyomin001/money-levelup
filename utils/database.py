# utils/database.py
# 로그인 지속성을 위한 최소 DB 연동. 비밀번호 없이 "이름+출생연도"를 키로 사용하는
# 데모용 단순 저장소입니다. (같은 이름+출생연도를 쓰는 사람과 데이터가 겹칠 수 있음 — 데모 목적상 허용)
# secrets에 MONGO_URI가 없으면 DB 없이도 앱은 정상 동작하고, 이 경우 세션이 끝나면 데이터가 초기화됩니다.
import logging
import time
import streamlit as st
from pymongo import MongoClient

DB_NAME = "money_levelup"


@st.cache_resource
def _connect_mongo(uri: str):
    """연결에 성공했을 때만 캐싱한다. (실패를 캐싱하면 그 뒤로는 재시도 없이 계속 실패 취급된다)"""
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")  # 연결 즉시 확인
    return client


def get_mongo_client():
    """일시적인 네트워크 문제로 첫 연결이 실패해도, 이후 요청에서 다시 시도할 수 있도록 한다.
    (기존에는 @st.cache_resource가 실패(None)까지 영구 캐싱해서, 앱이 켜져 있는 동안 한 번이라도
    연결에 실패하면 그 뒤 모든 사용자의 데이터가 계속 세션에만 저장되는 문제가 있었다.)"""
    uri = st.secrets.get("MONGO_URI", None)
    if not uri:
        return None
    cache = st.session_state.setdefault("_mongo_retry", {"failed_at": 0})
    if cache["failed_at"] and time.time() - cache["failed_at"] < 30:
        return None
    try:
        return _connect_mongo(uri)
    except Exception as e:
        logging.error(f"[get_mongo_client] 연결 실패: {e}")
        cache["failed_at"] = time.time()
        return None


def _col(name: str):
    client = get_mongo_client()
    if client is None:
        return None
    return client[DB_NAME][name]


def load_doc(collection: str, key: str, default):
    col = _col(collection)
    if col is None:
        return default
    try:
        doc = col.find_one({"_id": key})
        if doc:
            doc.pop("_id", None)
            return doc
        return default
    except Exception as e:
        logging.error(f"[load_doc] {collection}/{key} 로드 실패: {e}")
        return default


def save_doc(collection: str, key: str, data: dict):
    col = _col(collection)
    if col is None:
        return False
    try:
        col.replace_one({"_id": key}, {"_id": key, **data}, upsert=True)
        return True
    except Exception as e:
        logging.error(f"[save_doc] {collection}/{key} 저장 실패: {e}")
        return False


def db_available() -> bool:
    return get_mongo_client() is not None
