#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Soldes de jetons : PostgreSQL si DATABASE_URL est definie, sinon fichier JSON."""
import json
import threading
from datetime import date, datetime
from pathlib import Path

import db

STORE_PATH = Path(__file__).resolve().parent / "data" / "users.json"

STARTING_BALANCE = 1000
SPREAD_COST = 200
INSTANT_COST = 50
DAILY_BONUS = 300

_lock = threading.Lock()


def _key(username):
    return username.strip().lower()


# ---------- Repli fichier JSON (dev local sans base de donnees) ----------

def _json_load():
    if not STORE_PATH.exists():
        return {}
    try:
        with open(STORE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _json_save(users):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _json_get_balance(username):
    with _lock:
        users = _json_load()
        user = users.get(_key(username))
        return user["balance"] if user else STARTING_BALANCE


def _json_bonus_available(username):
    with _lock:
        users = _json_load()
        user = users.get(_key(username))
        if not user:
            return True
        return user.get("last_bonus") != date.today().isoformat()


def _json_deduct(username, amount):
    with _lock:
        users = _json_load()
        key = _key(username)
        user = users.setdefault(key, {"display": username, "balance": STARTING_BALANCE, "last_bonus": None})
        if user["balance"] < amount:
            return False, user["balance"]
        user["balance"] -= amount
        user["display"] = username
        user["updated_at"] = datetime.utcnow().isoformat()
        _json_save(users)
        return True, user["balance"]


def _json_credit(username, amount):
    with _lock:
        users = _json_load()
        key = _key(username)
        user = users.setdefault(key, {"display": username, "balance": STARTING_BALANCE, "last_bonus": None})
        user["balance"] += amount
        user["display"] = username
        user["updated_at"] = datetime.utcnow().isoformat()
        _json_save(users)
        return user["balance"]


def _json_claim_bonus(username, amount):
    with _lock:
        users = _json_load()
        key = _key(username)
        today = date.today().isoformat()
        user = users.setdefault(key, {"display": username, "balance": STARTING_BALANCE, "last_bonus": None})
        if user.get("last_bonus") == today:
            return False, user["balance"]
        user["balance"] += amount
        user["last_bonus"] = today
        user["display"] = username
        user["updated_at"] = datetime.utcnow().isoformat()
        _json_save(users)
        return True, user["balance"]


# ---------- Backend PostgreSQL ----------

def _ensure_row(cur, key):
    cur.execute(
        "INSERT INTO tarot_jetons (username, balance, updated_at) VALUES (%s, %s, now()) "
        "ON CONFLICT (username) DO NOTHING",
        (key, STARTING_BALANCE),
    )


def get_balance(username):
    if not db.has_db():
        return _json_get_balance(username)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT balance FROM tarot_jetons WHERE username=%s", (_key(username),))
            row = cur.fetchone()
            return row[0] if row else STARTING_BALANCE
    finally:
        db.put_conn(conn)


def bonus_available(username):
    if not db.has_db():
        return _json_bonus_available(username)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT last_bonus FROM tarot_jetons WHERE username=%s", (_key(username),))
            row = cur.fetchone()
            if not row:
                return True
            return row[0] != date.today()
    finally:
        db.put_conn(conn)


def deduct(username, amount=SPREAD_COST):
    """Retourne (ok, nouveau_solde)."""
    if not db.has_db():
        return _json_deduct(username, amount)
    key = _key(username)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            _ensure_row(cur, key)
            cur.execute("SELECT balance FROM tarot_jetons WHERE username=%s FOR UPDATE", (key,))
            balance = cur.fetchone()[0]
            if balance < amount:
                conn.commit()
                return False, balance
            balance -= amount
            cur.execute("UPDATE tarot_jetons SET balance=%s, updated_at=now() WHERE username=%s", (balance, key))
        conn.commit()
        return True, balance
    finally:
        db.put_conn(conn)


def credit(username, amount):
    """Ajoute des jetons (achat Stripe). Retourne le nouveau solde."""
    if not db.has_db():
        return _json_credit(username, amount)
    key = _key(username)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            _ensure_row(cur, key)
            cur.execute("SELECT balance FROM tarot_jetons WHERE username=%s FOR UPDATE", (key,))
            balance = cur.fetchone()[0] + amount
            cur.execute("UPDATE tarot_jetons SET balance=%s, updated_at=now() WHERE username=%s", (balance, key))
        conn.commit()
        return balance
    finally:
        db.put_conn(conn)


def claim_bonus(username, amount=DAILY_BONUS):
    """Retourne (ok, nouveau_solde). ok=False si le bonus du jour a deja ete pris."""
    if not db.has_db():
        return _json_claim_bonus(username, amount)
    key = _key(username)
    today = date.today()
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            _ensure_row(cur, key)
            cur.execute("SELECT balance, last_bonus FROM tarot_jetons WHERE username=%s FOR UPDATE", (key,))
            balance, last_bonus = cur.fetchone()
            if last_bonus == today:
                conn.commit()
                return False, balance
            balance += amount
            cur.execute(
                "UPDATE tarot_jetons SET balance=%s, last_bonus=%s, updated_at=now() WHERE username=%s",
                (balance, today, key),
            )
        conn.commit()
        return True, balance
    finally:
        db.put_conn(conn)
