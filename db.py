#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Connexion PostgreSQL partagee (comptes + jetons), avec pool de connexions.

Si DATABASE_URL n'est pas definie (dev local), les stores retombent sur
un stockage fichier JSON ephemere.
"""
import os

import psycopg2
import psycopg2.pool

DATABASE_URL = os.environ.get("DATABASE_URL", "")

_pool = None
if DATABASE_URL:
    _is_local = "localhost" in DATABASE_URL or "127.0.0.1" in DATABASE_URL
    _sslmode = "prefer" if _is_local else "require"
    _pool = psycopg2.pool.SimpleConnectionPool(1, 5, DATABASE_URL, sslmode=_sslmode)


def has_db():
    return _pool is not None


def get_conn():
    return _pool.getconn()


def put_conn(conn):
    _pool.putconn(conn)


def init_schema():
    if not has_db():
        return
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Prefixees "tarot_" : cette base peut etre partagee avec d'autres projets.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tarot_accounts (
                    email_key TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    password_hash TEXT,
                    nickname TEXT NOT NULL,
                    google_id TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tarot_jetons (
                    username TEXT PRIMARY KEY,
                    balance INTEGER NOT NULL,
                    last_bonus DATE,
                    updated_at TIMESTAMPTZ
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tarot_processed_payments (
                    ref TEXT PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
        conn.commit()
    finally:
        put_conn(conn)
