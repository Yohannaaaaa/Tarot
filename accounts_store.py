#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comptes utilisateurs : PostgreSQL si DATABASE_URL est definie, sinon fichier JSON."""
import json
import secrets
import threading
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
from werkzeug.security import check_password_hash, generate_password_hash

import db


def _new_referral_code():
    return secrets.token_hex(4)

ACCOUNTS_PATH = Path(__file__).resolve().parent / "data" / "accounts.json"

_lock = threading.Lock()


def _key(email):
    return email.strip().lower()


# ---------- Repli fichier JSON (dev local sans base de donnees) ----------

def _json_load():
    if not ACCOUNTS_PATH.exists():
        return {}
    try:
        with open(ACCOUNTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _json_save(accounts):
    ACCOUNTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ACCOUNTS_PATH, "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)


def _json_get_account(email):
    return _json_load().get(_key(email))


def _json_email_exists(email):
    return _key(email) in _json_load()


def _json_existing_referral_codes(accounts):
    return {a["referral_code"] for a in accounts.values() if a.get("referral_code")}


def _json_create_account(email, password, nickname, referred_by_email=None):
    with _lock:
        accounts = _json_load()
        key = _key(email)
        if key in accounts:
            return None
        existing_codes = _json_existing_referral_codes(accounts)
        code = _new_referral_code()
        while code in existing_codes:
            code = _new_referral_code()
        account = {
            "email": email.strip(),
            "password_hash": generate_password_hash(password),
            "nickname": nickname.strip() or email.split("@")[0],
            "google_id": None,
            "created_at": datetime.utcnow().isoformat(),
            "referral_code": code,
            "referred_by_email": referred_by_email,
        }
        accounts[key] = account
        _json_save(accounts)
        return account


def _json_verify_password(email, password):
    account = _json_load().get(_key(email))
    if not account or not account.get("password_hash"):
        return False
    return check_password_hash(account["password_hash"], password)


def _json_set_password(email, new_password):
    with _lock:
        accounts = _json_load()
        key = _key(email)
        account = accounts.get(key)
        if not account:
            return False
        account["password_hash"] = generate_password_hash(new_password)
        _json_save(accounts)
        return True


def _json_delete_account(email):
    with _lock:
        accounts = _json_load()
        key = _key(email)
        if key not in accounts:
            return False
        del accounts[key]
        _json_save(accounts)
        return True


def _json_upsert_google_account(email, google_id, name):
    with _lock:
        accounts = _json_load()
        key = _key(email)
        account = accounts.get(key)
        if account:
            account["google_id"] = google_id
        else:
            existing_codes = _json_existing_referral_codes(accounts)
            code = _new_referral_code()
            while code in existing_codes:
                code = _new_referral_code()
            account = {
                "email": email.strip(),
                "password_hash": None,
                "nickname": (name or email.split("@")[0]).strip(),
                "google_id": google_id,
                "created_at": datetime.utcnow().isoformat(),
                "referral_code": code,
                "referred_by_email": None,
            }
            accounts[key] = account
        _json_save(accounts)
        return account


def _json_get_account_by_referral_code(code):
    for account in _json_load().values():
        if account.get("referral_code") == code:
            return account
    return None


def _json_ensure_referral_code(email):
    with _lock:
        accounts = _json_load()
        key = _key(email)
        account = accounts.get(key)
        if not account:
            return None
        if account.get("referral_code"):
            return account["referral_code"]
        existing_codes = _json_existing_referral_codes(accounts)
        code = _new_referral_code()
        while code in existing_codes:
            code = _new_referral_code()
        account["referral_code"] = code
        _json_save(accounts)
        return code


def _json_set_referred_by(email, referrer_email):
    with _lock:
        accounts = _json_load()
        key = _key(email)
        account = accounts.get(key)
        if not account or account.get("referred_by_email"):
            return False
        account["referred_by_email"] = referrer_email
        _json_save(accounts)
        return True


def _json_count_referrals(email):
    return sum(1 for a in _json_load().values() if a.get("referred_by_email") == email)


# ---------- Backend PostgreSQL ----------

ACCOUNT_COLUMNS = "email, password_hash, nickname, google_id, created_at, referral_code, referred_by_email"


def _row_to_account(row):
    if not row:
        return None
    email, password_hash, nickname, google_id, created_at, referral_code, referred_by_email = row
    return {
        "email": email,
        "password_hash": password_hash,
        "nickname": nickname,
        "google_id": google_id,
        "created_at": created_at.isoformat() if created_at else None,
        "referral_code": referral_code,
        "referred_by_email": referred_by_email,
    }


def get_account(email):
    if not db.has_db():
        return _json_get_account(email)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {ACCOUNT_COLUMNS} FROM tarot_accounts WHERE email_key=%s",
                (_key(email),),
            )
            return _row_to_account(cur.fetchone())
    finally:
        db.put_conn(conn)


def get_account_by_referral_code(code):
    if not code:
        return None
    if not db.has_db():
        return _json_get_account_by_referral_code(code)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {ACCOUNT_COLUMNS} FROM tarot_accounts WHERE referral_code=%s",
                (code,),
            )
            return _row_to_account(cur.fetchone())
    finally:
        db.put_conn(conn)


def ensure_referral_code(email):
    """Retourne le code de parrainage du compte, en le generant s'il n'existe pas encore."""
    if not db.has_db():
        return _json_ensure_referral_code(email)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT referral_code FROM tarot_accounts WHERE email_key=%s", (_key(email),))
            row = cur.fetchone()
            if not row:
                return None
            if row[0]:
                return row[0]
            for _ in range(5):
                code = _new_referral_code()
                cur.execute(
                    "UPDATE tarot_accounts SET referral_code=%s WHERE email_key=%s AND referral_code IS NULL",
                    (code, _key(email)),
                )
                if cur.rowcount > 0:
                    conn.commit()
                    return code
                conn.rollback()
        return None
    finally:
        db.put_conn(conn)


def set_referred_by(email, referrer_email):
    if not db.has_db():
        return _json_set_referred_by(email, referrer_email)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tarot_accounts SET referred_by_email=%s "
                "WHERE email_key=%s AND referred_by_email IS NULL",
                (referrer_email, _key(email)),
            )
            updated = cur.rowcount > 0
        conn.commit()
        return updated
    finally:
        db.put_conn(conn)


def count_referrals(email):
    if not db.has_db():
        return _json_count_referrals(email)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM tarot_accounts WHERE referred_by_email=%s", (email,))
            return cur.fetchone()[0]
    finally:
        db.put_conn(conn)


def email_exists(email):
    if not db.has_db():
        return _json_email_exists(email)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM tarot_accounts WHERE email_key=%s", (_key(email),))
            return cur.fetchone() is not None
    finally:
        db.put_conn(conn)


def create_account(email, password, nickname, referred_by_email=None):
    """Retourne le compte cree, ou None si l'e-mail existe deja."""
    if not db.has_db():
        return _json_create_account(email, password, nickname, referred_by_email)
    key = _key(email)
    nick = nickname.strip() or email.split("@")[0]
    password_hash = generate_password_hash(password)
    conn = db.get_conn()
    try:
        for _ in range(5):
            code = _new_referral_code()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO tarot_accounts (email_key, email, password_hash, nickname, referral_code, referred_by_email) "
                    "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (email_key) DO NOTHING",
                    (key, email.strip(), password_hash, nick, code, referred_by_email),
                )
                if cur.rowcount == 0:
                    conn.rollback()
                    cur.execute("SELECT 1 FROM tarot_accounts WHERE email_key=%s", (key,))
                    if cur.fetchone():
                        return None
                    continue
            conn.commit()
            return {
                "email": email.strip(), "password_hash": password_hash, "nickname": nick,
                "google_id": None, "referral_code": code, "referred_by_email": referred_by_email,
            }
        return None
    finally:
        db.put_conn(conn)


def verify_password(email, password):
    account = get_account(email)
    if not account or not account.get("password_hash"):
        return False
    return check_password_hash(account["password_hash"], password)


def set_password(email, new_password):
    if not db.has_db():
        return _json_set_password(email, new_password)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tarot_accounts SET password_hash=%s WHERE email_key=%s",
                (generate_password_hash(new_password), _key(email)),
            )
            updated = cur.rowcount > 0
        conn.commit()
        return updated
    finally:
        db.put_conn(conn)


def list_accounts():
    if not db.has_db():
        accounts = list(_json_load().values())
        return sorted(accounts, key=lambda a: a.get("created_at") or "", reverse=True)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {ACCOUNT_COLUMNS} FROM tarot_accounts ORDER BY created_at DESC")
            return [_row_to_account(row) for row in cur.fetchall()]
    finally:
        db.put_conn(conn)


def delete_account(email):
    if not db.has_db():
        return _json_delete_account(email)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tarot_accounts WHERE email_key=%s", (_key(email),))
            deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        db.put_conn(conn)


def count_accounts():
    if not db.has_db():
        return len(_json_load())
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM tarot_accounts")
            return cur.fetchone()[0]
    finally:
        db.put_conn(conn)


def count_registrations_by_day(days=7):
    """Retourne [(date_iso, count), ...] pour les `days` derniers jours (aujourd'hui inclus)."""
    today = datetime.utcnow().date()
    date_range = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    if not db.has_db():
        counts = {}
        for account in _json_load().values():
            created = (account.get("created_at") or "")[:10]
            if created:
                counts[created] = counts.get(created, 0) + 1
    else:
        conn = db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT created_at::date, count(*) FROM tarot_accounts GROUP BY 1")
                counts = {d.isoformat(): c for d, c in cur.fetchall()}
        finally:
            db.put_conn(conn)
    return [(d.isoformat(), counts.get(d.isoformat(), 0)) for d in date_range]


def upsert_google_account(email, google_id, name):
    """Cree le compte s'il n'existe pas, sinon rattache l'identifiant Google."""
    if not db.has_db():
        return _json_upsert_google_account(email, google_id, name)
    key = _key(email)
    nick = (name or email.split("@")[0]).strip()
    conn = db.get_conn()
    try:
        for _ in range(5):
            code = _new_referral_code()
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        "INSERT INTO tarot_accounts (email_key, email, password_hash, nickname, google_id, referral_code) "
                        "VALUES (%s, %s, NULL, %s, %s, %s) "
                        "ON CONFLICT (email_key) DO UPDATE SET google_id = EXCLUDED.google_id",
                        (key, email.strip(), nick, google_id, code),
                    )
                except psycopg2.IntegrityError:
                    conn.rollback()
                    continue
            conn.commit()
            return get_account(email)
        return get_account(email)
    finally:
        db.put_conn(conn)
