#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Calcul du signe ascendant a partir de la date, l'heure et le lieu de
naissance. Formule astronomique standard (temps sideral de Greenwich +
formule de l'ascendant), sans aucun service externe ni cle API."""
import math
from datetime import datetime
from zoneinfo import ZoneInfo

CITIES = [
    {"id": "istanbul", "name": {"fr": "Istanbul", "tr": "İstanbul"}, "lat": 41.0082, "lon": 28.9784, "tz": "Europe/Istanbul"},
    {"id": "ankara", "name": {"fr": "Ankara", "tr": "Ankara"}, "lat": 39.9334, "lon": 32.8597, "tz": "Europe/Istanbul"},
    {"id": "izmir", "name": {"fr": "Izmir", "tr": "İzmir"}, "lat": 38.4237, "lon": 27.1428, "tz": "Europe/Istanbul"},
    {"id": "bursa", "name": {"fr": "Bursa", "tr": "Bursa"}, "lat": 40.1885, "lon": 29.0610, "tz": "Europe/Istanbul"},
    {"id": "antalya", "name": {"fr": "Antalya", "tr": "Antalya"}, "lat": 36.8969, "lon": 30.7133, "tz": "Europe/Istanbul"},
    {"id": "adana", "name": {"fr": "Adana", "tr": "Adana"}, "lat": 37.0000, "lon": 35.3213, "tz": "Europe/Istanbul"},
    {"id": "gaziantep", "name": {"fr": "Gaziantep", "tr": "Gaziantep"}, "lat": 37.0662, "lon": 37.3833, "tz": "Europe/Istanbul"},
    {"id": "paris", "name": {"fr": "Paris", "tr": "Paris"}, "lat": 48.8566, "lon": 2.3522, "tz": "Europe/Paris"},
    {"id": "marseille", "name": {"fr": "Marseille", "tr": "Marsilya"}, "lat": 43.2965, "lon": 5.3698, "tz": "Europe/Paris"},
    {"id": "lyon", "name": {"fr": "Lyon", "tr": "Lyon"}, "lat": 45.7640, "lon": 4.8357, "tz": "Europe/Paris"},
    {"id": "toulouse", "name": {"fr": "Toulouse", "tr": "Toulouse"}, "lat": 43.6047, "lon": 1.4442, "tz": "Europe/Paris"},
    {"id": "nice", "name": {"fr": "Nice", "tr": "Nice"}, "lat": 43.7102, "lon": 7.2620, "tz": "Europe/Paris"},
    {"id": "strasbourg", "name": {"fr": "Strasbourg", "tr": "Strazburg"}, "lat": 48.5734, "lon": 7.7521, "tz": "Europe/Paris"},
]

_OBLIQUITY_DEG = 23.4392911


def find_city(city_id):
    return next((c for c in CITIES if c["id"] == city_id), None)


def _julian_day(dt_utc):
    year, month = dt_utc.year, dt_utc.month
    day_frac = dt_utc.day + (dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600) / 24
    if month <= 2:
        year -= 1
        month += 12
    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    return math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day_frac + b - 1524.5


def _gmst_degrees(jd):
    t = (jd - 2451545.0) / 36525.0
    gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t ** 2 - (t ** 3) / 38710000.0
    return gmst % 360.0


def ascendant_sign_index(birth_date, birth_time, city):
    """birth_date: datetime.date, birth_time: datetime.time (heure locale de naissance)."""
    tz = ZoneInfo(city["tz"])
    local_dt = datetime(
        birth_date.year, birth_date.month, birth_date.day,
        birth_time.hour, birth_time.minute, tzinfo=tz,
    )
    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
    jd = _julian_day(utc_dt)
    ramc = (_gmst_degrees(jd) + city["lon"]) % 360.0

    eps = math.radians(_OBLIQUITY_DEG)
    ramc_rad = math.radians(ramc)
    phi_rad = math.radians(city["lat"])

    y = math.cos(ramc_rad)
    x = -(math.sin(ramc_rad) * math.cos(eps) + math.tan(phi_rad) * math.sin(eps))
    asc_deg = math.degrees(math.atan2(y, x)) % 360.0

    return int(asc_deg // 30) % 12, asc_deg
