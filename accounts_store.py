#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stockage simple des comptes utilisateurs (fichier JSON + verrou mémoire)."""
import json
import threading
from datetime import datetime
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

ACCOUNTS_PATH = Path(__file__).resolve().parent / "data" / "accounts.json"

_lock = threading.Lock()


def _load():
    if not ACCOUNTS_PATH.exists():
        return {}
    try:
        with open(ACCOUNTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(accounts):
    ACCOUNTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ACCOUNTS_PATH, "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)


def _key(email):
    return email.strip().lower()


def get_account(email):
    return _load().get(_key(email))


def email_exists(email):
    return _key(email) in _load()


def create_account(email, password, nickname):
    """Retourne le compte créé, ou None si l'e-mail existe déjà."""
    with _lock:
        accounts = _load()
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
        _save(accounts)
        return account


def verify_password(email, password):
    account = _load().get(_key(email))
    if not account or not account.get("password_hash"):
        return False
    return check_password_hash(account["password_hash"], password)


def set_password(email, new_password):
    with _lock:
        accounts = _load()
        key = _key(email)
        account = accounts.get(key)
        if not account:
            return False
        account["password_hash"] = generate_password_hash(new_password)
        _save(accounts)
        return True


def upsert_google_account(email, google_id, name):
    """Crée le compte s'il n'existe pas, sinon rattache l'identifiant Google."""
    with _lock:
        accounts = _load()
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
        _save(accounts)
        return account
