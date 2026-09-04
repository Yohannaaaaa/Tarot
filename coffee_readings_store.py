#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lectures de marc de cafe generees par IA, en attente d'envoi differe."""
import json
import threading
from datetime import datetime
from pathlib import Path

import db

READINGS_PATH = Path(__file__).resolve().parent / "data" / "pending_readings.json"

_lock = threading.Lock()


def _json_load():
    if not READINGS_PATH.exists():
        return []
    try:
        with open(READINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _json_save(readings):
    READINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(READINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(readings, f, ensure_ascii=False, indent=2)


def add_pending_reading(email, name, lang, reading_text, send_at):
    send_at_iso = send_at.isoformat()
    if not db.has_db():
        with _lock:
            readings = _json_load()
            next_id = (max((r["id"] for r in readings), default=0)) + 1
            readings.append({
                "id": next_id,
                "email": email,
                "name": name,
                "lang": lang,
                "reading_text": reading_text,
                "created_at": datetime.utcnow().isoformat(),
                "send_at": send_at_iso,
                "sent": False,
            })
            _json_save(readings)
        return
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tarot_pending_readings (email, name, lang, reading_text, send_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (email, name, lang, reading_text, send_at_iso),
            )
        conn.commit()
    finally:
        db.put_conn(conn)


def list_due_readings(now):
    now_iso = now.isoformat()
    if not db.has_db():
        return [r for r in _json_load() if not r.get("sent") and r.get("send_at", "") <= now_iso]
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, name, lang, reading_text FROM tarot_pending_readings "
                "WHERE sent = false AND send_at <= %s",
                (now_iso,),
            )
            return [
                {"id": row[0], "email": row[1], "name": row[2], "lang": row[3], "reading_text": row[4]}
                for row in cur.fetchall()
            ]
    finally:
        db.put_conn(conn)


def mark_sent(reading_id):
    if not db.has_db():
        with _lock:
            readings = _json_load()
            for r in readings:
                if r["id"] == reading_id:
                    r["sent"] = True
            _json_save(readings)
        return
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE tarot_pending_readings SET sent = true WHERE id = %s", (reading_id,))
        conn.commit()
    finally:
        db.put_conn(conn)
