#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demandes de rendez-vous et jours bloques : PostgreSQL si DATABASE_URL est
definie, sinon fichier JSON. Auparavant stockees uniquement dans un fichier
JSON local, ce qui les faisait disparaitre a chaque redeploiement sur Render
(disque non persistant) -- migre vers la base pour une conservation durable."""
import json
import threading
from pathlib import Path

import db

APPOINTMENTS_PATH = Path(__file__).resolve().parent / "data" / "appointments.json"
BLOCKED_DATES_PATH = Path(__file__).resolve().parent / "data" / "blocked_dates.json"

_lock = threading.Lock()


# ---------- Repli fichier JSON (dev local sans base de donnees) ----------

def _json_load_appointments():
    try:
        with open(APPOINTMENTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _json_save_appointments(appointments):
    APPOINTMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(APPOINTMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(appointments, f, ensure_ascii=False, indent=2)


def _json_add_appointment(entry):
    with _lock:
        appointments = _json_load_appointments()
        entry = dict(entry)
        entry["id"] = max((a.get("id", 0) for a in appointments), default=0) + 1
        appointments.append(entry)
        _json_save_appointments(appointments)
        return entry


def _json_mark_reminded(appointment_id):
    with _lock:
        appointments = _json_load_appointments()
        for a in appointments:
            if a.get("id") == appointment_id:
                a["reminded"] = True
        _json_save_appointments(appointments)


def _json_load_blocked_dates():
    try:
        with open(BLOCKED_DATES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _json_save_blocked_dates(dates):
    BLOCKED_DATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BLOCKED_DATES_PATH, "w", encoding="utf-8") as f:
        json.dump(dates, f, ensure_ascii=False, indent=2)


# ---------- Backend PostgreSQL ----------

def list_appointments():
    if not db.has_db():
        return _json_load_appointments()
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, data FROM tarot_appointments ORDER BY id")
            rows = cur.fetchall()
        result = []
        for row_id, data in rows:
            entry = dict(data)
            entry["id"] = row_id
            result.append(entry)
        return result
    finally:
        db.put_conn(conn)


def add_appointment(entry):
    if not db.has_db():
        return _json_add_appointment(entry)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tarot_appointments (data) VALUES (%s::jsonb) RETURNING id",
                (json.dumps(entry),),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        result = dict(entry)
        result["id"] = new_id
        return result
    finally:
        db.put_conn(conn)


def mark_reminded(appointment_id):
    if not db.has_db():
        return _json_mark_reminded(appointment_id)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tarot_appointments SET data = jsonb_set(data, '{reminded}', 'true'::jsonb) WHERE id = %s",
                (appointment_id,),
            )
        conn.commit()
    finally:
        db.put_conn(conn)


def list_blocked_dates():
    if not db.has_db():
        return _json_load_blocked_dates()
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT date_str FROM tarot_blocked_dates ORDER BY date_str")
            return [row[0] for row in cur.fetchall()]
    finally:
        db.put_conn(conn)


def add_blocked_date(date_str):
    if not db.has_db():
        dates = _json_load_blocked_dates()
        if date_str not in dates:
            dates.append(date_str)
            _json_save_blocked_dates(sorted(dates))
        return
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tarot_blocked_dates (date_str) VALUES (%s) ON CONFLICT DO NOTHING",
                (date_str,),
            )
        conn.commit()
    finally:
        db.put_conn(conn)


def remove_blocked_date(date_str):
    if not db.has_db():
        dates = _json_load_blocked_dates()
        if date_str in dates:
            dates.remove(date_str)
            _json_save_blocked_dates(dates)
        return
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tarot_blocked_dates WHERE date_str = %s", (date_str,))
        conn.commit()
    finally:
        db.put_conn(conn)
