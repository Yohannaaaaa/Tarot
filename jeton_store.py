#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stockage simple des soldes de jetons (fichier JSON + verrou mémoire)."""
import json
import threading
from datetime import date, datetime
from pathlib import Path

STORE_PATH = Path(__file__).resolve().parent / "data" / "users.json"

STARTING_BALANCE = 1000
SPREAD_COST = 200
DAILY_BONUS = 300

_lock = threading.Lock()


def _load():
    if not STORE_PATH.exists():
        return {}
    try:
        with open(STORE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(users):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _key(username):
    return username.strip().lower()


def get_balance(username):
    with _lock:
        users = _load()
        user = users.get(_key(username))
        return user["balance"] if user else STARTING_BALANCE


def bonus_available(username):
    with _lock:
        users = _load()
        user = users.get(_key(username))
        if not user:
            return True
        return user.get("last_bonus") != date.today().isoformat()


def deduct(username, amount=SPREAD_COST):
    """Retourne (ok, nouveau_solde)."""
    with _lock:
        users = _load()
        key = _key(username)
        user = users.setdefault(key, {"display": username, "balance": STARTING_BALANCE, "last_bonus": None})
        if user["balance"] < amount:
            return False, user["balance"]
        user["balance"] -= amount
        user["display"] = username
        user["updated_at"] = datetime.utcnow().isoformat()
        _save(users)
        return True, user["balance"]


def claim_bonus(username, amount=DAILY_BONUS):
    """Retourne (ok, nouveau_solde). ok=False si le bonus du jour a deja ete pris."""
    with _lock:
        users = _load()
        key = _key(username)
        today = date.today().isoformat()
        user = users.setdefault(key, {"display": username, "balance": STARTING_BALANCE, "last_bonus": None})
        if user.get("last_bonus") == today:
            return False, user["balance"]
        user["balance"] += amount
        user["last_bonus"] = today
        user["display"] = username
        user["updated_at"] = datetime.utcnow().isoformat()
        _save(users)
        return True, user["balance"]
