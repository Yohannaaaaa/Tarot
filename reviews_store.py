#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Avis clients geres par l'admin : PostgreSQL si DATABASE_URL est definie, sinon fichier JSON."""
import json
import threading
from datetime import datetime
from pathlib import Path

import db

STORE_PATH = Path(__file__).resolve().parent / "data" / "reviews.json"

_lock = threading.Lock()


# ---------- Repli fichier JSON (dev local sans base de donnees) ----------

def _json_load():
    if not STORE_PATH.exists():
        return []
    try:
        with open(STORE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _json_save(reviews):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)


def _json_list_reviews():
    reviews = _json_load()
    return sorted(reviews, key=lambda r: r["createdAt"], reverse=True)


def _json_add_review(name, rating, text, email=None):
    with _lock:
        reviews = _json_load()
        next_id = (max((r["id"] for r in reviews), default=0)) + 1
        reviews.append({
            "id": next_id,
            "name": name,
            "rating": rating,
            "text": text,
            "email": email,
            "createdAt": datetime.utcnow().isoformat(),
        })
        _json_save(reviews)


def _json_delete_review(review_id):
    with _lock:
        reviews = [r for r in _json_load() if r["id"] != review_id]
        _json_save(reviews)


def _json_update_review(review_id, name, rating, text):
    with _lock:
        reviews = _json_load()
        for r in reviews:
            if r["id"] == review_id:
                r["name"] = name
                r["rating"] = rating
                r["text"] = text
        _json_save(reviews)


# ---------- Backend PostgreSQL ----------

def list_reviews():
    if not db.has_db():
        return _json_list_reviews()
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, rating, review_text, created_at, email FROM tarot_reviews ORDER BY created_at DESC")
            return [
                {"id": row[0], "name": row[1], "rating": row[2], "text": row[3], "createdAt": row[4].isoformat(), "email": row[5]}
                for row in cur.fetchall()
            ]
    finally:
        db.put_conn(conn)


def get_review(review_id):
    return next((r for r in list_reviews() if r["id"] == review_id), None)


def add_review(name, rating, text, email=None):
    if not db.has_db():
        return _json_add_review(name, rating, text, email)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tarot_reviews (name, rating, review_text, email) VALUES (%s, %s, %s, %s)",
                (name, rating, text, email),
            )
        conn.commit()
    finally:
        db.put_conn(conn)


def delete_review(review_id):
    if not db.has_db():
        return _json_delete_review(review_id)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tarot_reviews WHERE id=%s", (review_id,))
        conn.commit()
    finally:
        db.put_conn(conn)


def update_review(review_id, name, rating, text):
    if not db.has_db():
        return _json_update_review(review_id, name, rating, text)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tarot_reviews SET name=%s, rating=%s, review_text=%s WHERE id=%s",
                (name, rating, text, review_id),
            )
        conn.commit()
    finally:
        db.put_conn(conn)
