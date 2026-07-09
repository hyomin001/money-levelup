# utils/database.py
# hyomin-portal-main 의 utils/database.py 패턴을 재사용.
# (atomic 캐시 연산, MongoDB 연결 구조는 기존 검증된 로직 그대로 사용)
import streamlit as st
from pymongo import MongoClient
import logging
import time as _time

DB_NAME = "money_levelup"  # 기존 hyomin_universe 와 분리된 별도 DB


@st.cache_resource
def get_mongo_client():
    uri = st.secrets.get("MONGO_URI", None)
    if uri:
        return MongoClient(uri)
    return None


def _get_col(name: str):
    client = get_mongo_client()
    if client is None:
        return None
    db = client[DB_NAME]
    return db[name]


def load_db(name, default):
    """MongoDB에서 데이터 불러오기 (재시도 1회 포함)"""
    client = get_mongo_client()
    if client is None:
        st.error("❌ DB 연결 실패: MongoDB에 연결할 수 없습니다. secrets.toml의 MONGO_URI를 확인하세요.")
        st.stop()
    for attempt in range(2):
        try:
            col = _get_col(name)
            doc = col.find_one({"_id": "main"})
            if doc:
                doc.pop("_id", None)
                if "_list" in doc and len(doc) == 1:
                    return doc["_list"]
                return doc
            return default
        except Exception as e:
            logging.error(f"[load_db] {name} 로드 실패 (시도 {attempt+1}/2): {e}")
            if attempt == 0:
                _time.sleep(0.5)
                continue
            st.warning(f"⚠️ DB 일시 오류. 일부 데이터가 최신이 아닐 수 있습니다. ({name})")
            return default


def save_db(name, data):
    """MongoDB에 데이터 저장하기"""
    if data is None:
        return
    client = get_mongo_client()
    if client is None:
        logging.error(f"[save_db] MongoDB 연결 없음 - {name} 저장 취소")
        return
    try:
        col = _get_col(name)
        if isinstance(data, list):
            doc_to_save = {"_id": "main", "_list": data}
        else:
            doc_to_save = {"_id": "main", **data}
        col.replace_one({"_id": "main"}, doc_to_save, upsert=True)
    except Exception as e:
        logging.error(f"[save_db] {name} 저장 실패: {e}")


def atomic_deduct_cash(uid: str, amount: int) -> bool:
    """원자적 현금 차감 (Race Condition 방어) — hyomin-portal 로직 그대로 재사용."""
    client = get_mongo_client()
    if client is None:
        return False
    try:
        col = _get_col("users")
        result = col.find_one_and_update(
            {"_id": "main", f"{uid}.cash": {"$gte": amount}},
            {"$inc": {f"{uid}.cash": -amount}},
        )
        return result is not None
    except Exception as e:
        logging.error(f"[atomic_deduct_cash] {uid} 차감 실패: {e}")
        return False


def atomic_add_cash(uid: str, amount: int) -> bool:
    """원자적 현금 지급."""
    client = get_mongo_client()
    if client is None:
        return False
    try:
        col = _get_col("users")
        col.update_one({"_id": "main"}, {"$inc": {f"{uid}.cash": amount}}, upsert=True)
        return True
    except Exception as e:
        logging.error(f"[atomic_add_cash] {uid} 지급 실패: {e}")
        return False


def log_tx(uid: str, tx: dict):
    """거래/소비 내역 로그 (txlog 컬렉션에 append)."""
    client = get_mongo_client()
    if client is None:
        return
    try:
        col = _get_col("txlog")
        tx = {**tx, "uid": uid, "ts": _time.time()}
        col.insert_one(tx)
    except Exception as e:
        logging.error(f"[log_tx] 실패: {e}")


def load_tx(uid: str, limit: int = 200):
    client = get_mongo_client()
    if client is None:
        return []
    try:
        col = _get_col("txlog")
        cur = col.find({"uid": uid}).sort("ts", -1).limit(limit)
        return list(cur)
    except Exception as e:
        logging.error(f"[load_tx] 실패: {e}")
        return []
