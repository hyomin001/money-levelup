# utils/core.py
import hashlib
import time
import random
import os
import bcrypt
import streamlit as st
from utils.config import ASSET_CONFIG, ASSET_BASE_PRICE, STARTING_CASH
from utils.database import load_db, save_db

MARKET_KEY = "market"
USERS_KEY = "users"


# ── 비밀번호 해싱 (hyomin-portal core.py 패턴 재사용) ────────────────────────
def hash_pw_bcrypt(pw: str) -> str:
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')


def verify_pw(pw: str, stored_hash: str) -> bool:
    if not stored_hash or not isinstance(stored_hash, str):
        return False
    try:
        return bcrypt.checkpw(pw.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception:
        return False


# ── 금액 포맷 (hyomin-portal utils/core.py 의 format_korean_money 그대로 재사용) ──
def format_korean_money(num):
    try:
        if num is None or num != num or num == 0:
            return "0원"
    except TypeError:
        return "0원"
    is_neg = num < 0
    num = abs(int(num))
    jo, eok, man, won = num // 10**12, (num % 10**12) // 10**8, (num % 10**8) // 10**4, num % 10**4
    parts = []
    if jo > 0: parts.append(f"{jo:,}조")
    if eok > 0: parts.append(f"{eok:,}억")
    if man > 0: parts.append(f"{man:,}만")
    if won > 0 or not parts: parts.append(f"{won:,}")
    res = " ".join(parts) + "원"
    return f"-{res}" if is_neg else res


# ── 유저 ──────────────────────────────────────────────────────────────────
def default_user(uid):
    return {
        "uid": uid, "created": time.time(),
        "cash": STARTING_CASH,
        "portfolio": {},          # {asset_id: {"qty": int, "avg_price": float}}
        "savings": [],            # [{"product_id":..,"amount":..,"start":..,"maturity":..}]
        "expense_total": 0,
    }


def get_user(uid):
    users = load_db(USERS_KEY, {})
    if uid not in users:
        users[uid] = default_user(uid)
        save_db(USERS_KEY, users)
    return users[uid]


def save_user(uid, user_data):
    users = load_db(USERS_KEY, {})
    users[uid] = user_data
    save_db(USERS_KEY, users)


def signup(uid, pw):
    users = load_db(USERS_KEY, {})
    if uid in users:
        return False, "이미 존재하는 아이디입니다."
    u = default_user(uid)
    u["pw_hash"] = hash_pw_bcrypt(pw)
    users[uid] = u
    save_db(USERS_KEY, users)
    return True, "가입 완료"


def login(uid, pw):
    users = load_db(USERS_KEY, {})
    if uid not in users:
        return False, "존재하지 않는 아이디입니다."
    if not verify_pw(pw, users[uid].get("pw_hash", "")):
        return False, "비밀번호가 일치하지 않습니다."
    return True, "로그인 성공"


# ── 시세 (랜덤워크 시뮬레이션 — 실시간 실제 시세 연동 아님, UI에 고지) ────────────
def get_market():
    m = load_db(MARKET_KEY, {})
    if not m or m.get("version") != 1:
        m = {
            "version": 1,
            "prices": {a["id"]: ASSET_BASE_PRICE[a["id"]] for a in ASSET_CONFIG},
            "history": {a["id"]: [ASSET_BASE_PRICE[a["id"]]] for a in ASSET_CONFIG},
            "last_tick": time.time(),
        }
        save_db(MARKET_KEY, m)
    return m


def tick_market(min_interval_sec=30):
    """일정 주기마다 가격을 소폭 랜덤워크로 갱신."""
    m = get_market()
    if time.time() - m.get("last_tick", 0) < min_interval_sec:
        return m
    for a in ASSET_CONFIG:
        aid, vol = a["id"], a["vol"]
        p = m["prices"][aid]
        change = random.gauss(0, vol)
        new_p = max(100, p * (1 + change))
        m["prices"][aid] = round(new_p, 1)
        m["history"].setdefault(aid, []).append(round(new_p, 1))
        m["history"][aid] = m["history"][aid][-60:]
    m["last_tick"] = time.time()
    save_db(MARKET_KEY, m)
    return m


def get_net_worth(user, market):
    w = user.get("cash", 0)
    for aid, pos in user.get("portfolio", {}).items():
        w += pos.get("qty", 0) * market["prices"].get(aid, 0)
    for s in user.get("savings", []):
        w += s.get("amount", 0)
    return w
