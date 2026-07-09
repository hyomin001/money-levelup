# utils/database.py
# 로그인 지속성을 위한 최소 DB 연동. 비밀번호 없이 "이름+출생연도"를 키로 사용하는
# 데모용 단순 저장소입니다. (같은 이름+출생연도를 쓰는 사람과 데이터가 겹칠 수 있음 — 데모 목적상 허용)
import logging
import streamlit as st
from pymongo import MongoClient

DB_NAME = "money_levelup"


@st.cache_resource
def get_mongo_client():
    uri = st.secrets.get("MONGO_URI", None)
    if not uri:
        return None
    try:
        return MongoClient(uri, serverSelectionTimeoutMS=5000)
    except Exception as e:
        logging.error(f"[get_mongo_client] 연결 실패: {e}")
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
