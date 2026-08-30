#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comptes utilisateurs : PostgreSQL si DATABASE_URL est definie, sinon fichier JSON."""
import json
import threading
from datetime import datetime
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

import db

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


def _json_create_account(email, password, nickname):
    with _lock:
        accounts = _json_load()
        key = _key(email)
        if key in accounts:
            return None
        account = {
            "email": email.strip(),
            "password_hash": generate_password_hash(password),
            "nickname": nickname.strip() or email.split("@")[0],
            "google_id": None,
            "created_at": datetime.utcnow().isoformat(),
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


def _json_upsert_google_account(email, google_id, name):
    with _lock:
        accounts = _json_load()
        key = _key(email)
        account = accounts.get(key)
        if account:
            account["google_id"] = google_id
        else:
            account = {
                "email": email.strip(),
                "password_hash": None,
                "nickname": (name or email.split("@")[0]).strip(),
                "google_id": google_id,
                "created_at": datetime.utcnow().isoformat(),
            }
            accounts[key] = account
        _json_save(accounts)
        return account


# ---------- Backend PostgreSQL ----------

def _row_to_account(row):
    if not row:
        return None
    email, password_hash, nickname, google_id, created_at = row
    return {
        "email": email,
        "password_hash": password_hash,
        "nickname": nickname,
        "google_id": google_id,
        "created_at": created_at.isoformat() if created_at else None,
    }


def get_account(email):
    if not db.has_db():
        return _json_get_account(email)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email, password_hash, nickname, google_id, created_at "
                "FROM accounts WHERE email_key=%s",
                (_key(email),),
            )
            return _row_to_account(cur.fetchone())
    finally:
        db.put_conn(conn)


def email_exists(email):
    if not db.has_db():
        return _json_email_exists(email)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM accounts WHERE email_key=%s", (_key(email),))
            return cur.fetchone() is not None
    finally:
        db.put_conn(conn)


def create_account(email, password, nickname):
    """Retourne le compte cree, ou None si l'e-mail existe deja."""
    if not db.has_db():
        return _json_create_account(email, password, nickname)
    key = _key(email)
    nick = nickname.strip() or email.split("@")[0]
    password_hash = generate_password_hash(password)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (email_key, email, password_hash, nickname) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (email_key) DO NOTHING",
                (key, email.strip(), password_hash, nick),
            )
            if cur.rowcount == 0:
                conn.rollback()
                return None
        conn.commit()
        return {"email": email.strip(), "password_hash": password_hash, "nickname": nick, "google_id": None}
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
                "UPDATE accounts SET password_hash=%s WHERE email_key=%s",
                (generate_password_hash(new_password), _key(email)),
            )
            updated = cur.rowcount > 0
        conn.commit()
        return updated
    finally:
        db.put_conn(conn)


def upsert_google_account(email, google_id, name):
    """Cree le compte s'il n'existe pas, sinon rattache l'identifiant Google."""
    if not db.has_db():
        return _json_upsert_google_account(email, google_id, name)
    key = _key(email)
    nick = (name or email.split("@")[0]).strip()
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (email_key, email, password_hash, nickname, google_id) "
                "VALUES (%s, %s, NULL, %s, %s) "
                "ON CONFLICT (email_key) DO UPDATE SET google_id = EXCLUDED.google_id",
                (key, email.strip(), nick, google_id),
            )
        conn.commit()
        return get_account(email)
    finally:
        db.put_conn(conn)
