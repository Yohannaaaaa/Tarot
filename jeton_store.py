#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Soldes de jetons : PostgreSQL si DATABASE_URL est definie, sinon fichier JSON."""
import json
import random
import threading
from datetime import date, datetime
from pathlib import Path

import db

STORE_PATH = Path(__file__).resolve().parent / "data" / "users.json"
PROCESSED_PAYMENTS_PATH = Path(__file__).resolve().parent / "data" / "processed_payments.json"

STARTING_BALANCE = 1000
SPREAD_COST = 200
INSTANT_COST = 50

# Ordre des cases de la roue quotidienne (doit correspondre a l'ordre affiche en JS).
DAILY_WHEEL_SEGMENTS = [20, 100, 50, 300, 30, 200]
DAILY_WHEEL_WEIGHTS = [30, 15, 20, 3, 25, 7]


def _pick_daily_bonus():
    index = random.choices(range(len(DAILY_WHEEL_SEGMENTS)), weights=DAILY_WHEEL_WEIGHTS, k=1)[0]
    return index, DAILY_WHEEL_SEGMENTS[index]

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


def _json_deduct(username, amount):
    with _lock:
        users = _json_load()
        key = _key(username)
        user = users.setdefault(key, {"display": username, "balance": STARTING_BALANCE})
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
        user = users.setdefault(key, {"display": username, "balance": STARTING_BALANCE})
        user["balance"] += amount
        user["display"] = username
        user["updated_at"] = datetime.utcnow().isoformat()
        _json_save(users)
        return user["balance"]


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
    """Ajoute des jetons (achat Stripe/PayPal). Retourne le nouveau solde."""
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


def _json_grant_bonus_to_all(amount):
    with _lock:
        users = _json_load()
        for user in users.values():
            user["balance"] = user.get("balance", STARTING_BALANCE) + amount
            user["updated_at"] = datetime.utcnow().isoformat()
        _json_save(users)
        return len(users)


def grant_bonus_to_all(amount):
    """Ajoute un bonus ponctuel a tous les comptes ayant deja un solde enregistre.
    Retourne le nombre de comptes credites."""
    if not db.has_db():
        return _json_grant_bonus_to_all(amount)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE tarot_jetons SET balance = balance + %s, updated_at = now()", (amount,))
            count = cur.rowcount
        conn.commit()
        return count
    finally:
        db.put_conn(conn)


def _json_daily_bonus_available(username):
    with _lock:
        users = _json_load()
        user = users.get(_key(username))
        if not user or not user.get("daily_bonus_date"):
            return True
        return user["daily_bonus_date"] != date.today().isoformat()


def _json_claim_daily_bonus(username):
    with _lock:
        users = _json_load()
        key = _key(username)
        user = users.setdefault(key, {"display": username, "balance": STARTING_BALANCE})
        today = date.today().isoformat()
        if user.get("daily_bonus_date") == today:
            return False, None, None, user["balance"]
        index, amount = _pick_daily_bonus()
        user["balance"] += amount
        user["daily_bonus_date"] = today
        user["display"] = username
        user["updated_at"] = datetime.utcnow().isoformat()
        _json_save(users)
        return True, amount, index, user["balance"]


def daily_bonus_available(username):
    """Indique si l'utilisateur peut encore tourner la roue aujourd'hui."""
    if not db.has_db():
        return _json_daily_bonus_available(username)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT last_bonus FROM tarot_jetons WHERE username=%s", (_key(username),))
            row = cur.fetchone()
            if not row or row[0] is None:
                return True
            return row[0] != date.today()
    finally:
        db.put_conn(conn)


def claim_daily_bonus(username):
    """Fait tourner la roue une fois par jour et par compte.
    Retourne (gagne, montant, index_case, nouveau_solde)."""
    if not db.has_db():
        return _json_claim_daily_bonus(username)
    key = _key(username)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            _ensure_row(cur, key)
            cur.execute(
                "UPDATE tarot_jetons SET last_bonus = CURRENT_DATE, updated_at = now() "
                "WHERE username = %s AND (last_bonus IS NULL OR last_bonus <> CURRENT_DATE) "
                "RETURNING balance",
                (key,),
            )
            row = cur.fetchone()
            if row is None:
                cur.execute("SELECT balance FROM tarot_jetons WHERE username=%s", (key,))
                balance = cur.fetchone()[0]
                conn.commit()
                return False, None, None, balance
            index, amount = _pick_daily_bonus()
            balance = row[0] + amount
            cur.execute("UPDATE tarot_jetons SET balance=%s WHERE username=%s", (balance, key))
        conn.commit()
        return True, amount, index, balance
    finally:
        db.put_conn(conn)


def total_balance():
    """Somme des jetons actuellement en circulation sur tous les comptes."""
    if not db.has_db():
        users = _json_load()
        return sum(u.get("balance", STARTING_BALANCE) for u in users.values())
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(sum(balance), 0) FROM tarot_jetons")
            return cur.fetchone()[0]
    finally:
        db.put_conn(conn)


def count_processed_payments():
    if not db.has_db():
        try:
            with open(PROCESSED_PAYMENTS_PATH, encoding="utf-8") as f:
                return len(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            return 0
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM tarot_processed_payments")
            return cur.fetchone()[0]
    finally:
        db.put_conn(conn)


def _json_mark_payment_processed(ref):
    with _lock:
        try:
            with open(PROCESSED_PAYMENTS_PATH, encoding="utf-8") as f:
                refs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            refs = []
        if ref in refs:
            return False
        refs.append(ref)
        PROCESSED_PAYMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PROCESSED_PAYMENTS_PATH, "w", encoding="utf-8") as f:
            json.dump(refs, f, ensure_ascii=False, indent=2)
        return True


def mark_payment_processed(ref):
    """Enregistre une reference de paiement (Stripe/PayPal). Retourne False si deja traitee (paiement rejoue)."""
    if not db.has_db():
        return _json_mark_payment_processed(ref)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO tarot_processed_payments (ref) VALUES (%s) ON CONFLICT DO NOTHING", (ref,))
            processed = cur.rowcount > 0
        conn.commit()
        return processed
    finally:
        db.put_conn(conn)
