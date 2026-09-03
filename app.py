#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import hmac
import json
import os
import random
import re
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests
import stripe
from flask import Flask, Response, flash, jsonify, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

import accounts_store
import appointments_store
import ascendant
import db
import horoscope
import jeton_store
import reviews_store

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
PAYPAL_MODE = os.environ.get("PAYPAL_MODE", "sandbox")
PAYPAL_API_BASE = "https://api-m.paypal.com" if PAYPAL_MODE == "live" else "https://api-m.sandbox.paypal.com"


def get_paypal_access_token():
    resp = requests.post(
        f"{PAYPAL_API_BASE}/v1/oauth2/token",
        auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

GMAIL_ADDRESS = "tarot.clairvoyance.rituels@gmail.com"
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.environ.get("ADMIN_EMAILS", GMAIL_ADDRESS).split(",")
    if e.strip()
}


def is_admin():
    email = session.get("email")
    return bool(email and email.lower() in ADMIN_EMAILS)


WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "")
INSTAGRAM_URL = "https://www.instagram.com/rituams.tarot/"
TIKTOK_URL = "https://www.tiktok.com/@svetlanaquinn"

CRON_SECRET = os.environ.get("CRON_SECRET", "")
ADMIN_API_SECRET = os.environ.get("ADMIN_API_SECRET", "")
ISTANBUL_TZ = timezone(timedelta(hours=3))
APPOINTMENT_TIME_SLOTS = ["00:00", "00:30", "01:00", "01:30", "02:00", "02:30", "03:00", "03:30", "04:00"]


def _booked_times_by_day(appointments):
    times_by_day = {}
    for a in appointments:
        appt_date = a.get("appointmentDate")
        if not appt_date or "T" not in appt_date:
            continue
        day, time_str = appt_date.split("T")
        times_by_day.setdefault(day, set()).add(time_str)
    return times_by_day

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.secret_key = os.environ.get("SECRET_KEY", "rituams-tarot-dev-secret-change-me")
app.config["SESSION_COOKIE_SECURE"] = bool(os.environ.get("RENDER"))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
db.init_schema()

limiter = Limiter(get_remote_address, app=app, default_limits=[])


@app.errorhandler(429)
def ratelimit_handler(e):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "rate_limited"}), 429
    flash("error_rate_limited", "error")
    return redirect(request.referrer or url_for("index"))


@app.errorhandler(413)
def request_too_large_handler(e):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "too_large"}), 413
    flash("error_rate_limited", "error")
    return redirect(request.referrer or url_for("index"))


@app.errorhandler(404)
def not_found_handler(e):
    return render_template("404.html"), 404


@app.template_filter("wa_number")
def wa_number_filter(phone):
    return re.sub(r"\D", "", phone or "")


def external_url(endpoint, **values):
    url = url_for(endpoint, _external=True, **values)
    if not (request.host.startswith("localhost") or request.host.startswith("127.0.0.1")):
        url = url.replace("http://", "https://", 1)
    return url


def get_serializer():
    return URLSafeTimedSerializer(app.secret_key)


def _send_brevo(payload, to_addr, subject):
    """Render bloque les ports SMTP sortants (25/465/587) sur le plan gratuit ;
    on envoie donc via l'API HTTP de Brevo (port 443) a la place de smtplib."""
    try:
        resp = requests.post(
            BREVO_API_URL,
            json=payload,
            headers={
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=15,
        )
        if resp.status_code >= 300:
            print(f"[send_email] FAILED to {to_addr!r} subject={subject!r}: {resp.status_code} {resp.text}", flush=True)
            return False
        print(f"[send_email] OK to {to_addr!r} subject={subject!r}", flush=True)
        return True
    except Exception as exc:
        print(f"[send_email] FAILED to {to_addr!r} subject={subject!r}: {exc!r}", flush=True)
        return False


def send_email(to_addr, subject, body):
    if not BREVO_API_KEY:
        print("[send_email] SKIPPED: BREVO_API_KEY is not set", flush=True)
        return False
    subject = subject.replace("\r", " ").replace("\n", " ")
    payload = {
        "sender": {"name": "Rituams Tarot", "email": GMAIL_ADDRESS},
        "to": [{"email": to_addr}],
        "subject": subject,
        "textContent": body,
    }
    return _send_brevo(payload, to_addr, subject)


def send_email_async(to_addr, subject, body):
    threading.Thread(target=send_email, args=(to_addr, subject, body), daemon=True).start()


def send_email_with_attachment(to_addr, subject, body, attachment_bytes, attachment_filename, attachment_content_type):
    if not BREVO_API_KEY:
        print("[send_email] SKIPPED: BREVO_API_KEY is not set", flush=True)
        return False
    subject = subject.replace("\r", " ").replace("\n", " ")
    payload = {
        "sender": {"name": "Rituams Tarot", "email": GMAIL_ADDRESS},
        "to": [{"email": to_addr}],
        "subject": subject,
        "textContent": body,
        "attachment": [
            {
                "content": base64.b64encode(attachment_bytes).decode("ascii"),
                "name": secure_filename(attachment_filename) or "photo.jpg",
            }
        ],
    }
    return _send_brevo(payload, to_addr, subject)


def send_email_with_attachment_async(to_addr, subject, body, attachment_bytes, attachment_filename, attachment_content_type):
    threading.Thread(
        target=send_email_with_attachment,
        args=(to_addr, subject, body, attachment_bytes, attachment_filename, attachment_content_type),
        daemon=True,
    ).start()


DATA_PATH = Path(__file__).resolve().parent / "data" / "cards.json"
with open(DATA_PATH, encoding="utf-8") as f:
    CARDS = json.load(f)

CARDS_BY_ID = {c["id"]: c for c in CARDS}

LANGS = ("fr", "tr")
DEFAULT_LANG = "fr"

UI = {
    "fr": {
        "site_title": "Rituams Tarot",
        "meta_description": "Tirages de tarot gratuits et consultations en français et en turc : 78 cartes détaillées, tirages variés, rituels et guidance personnalisée.",
        "nav_home": "Accueil",
        "nav_cards": "Les Cartes",
        "nav_reading": "Tirage",
        "nav_about": "À propos",
        "home_title": "Rituams Tarot – Tarot en Ligne, Rituels & Voyance",
        "cta_reading": "Faire un tirage",
        "cta_cards": "Explorer les cartes",
        "home_about_teaser_title": "Qui suis-je ?",
        "home_about_teaser_text": "Svetlana, 18 ans d'expérience en tarot, spécialisée en amour et rituels.",
        "home_about_teaser_link": "En savoir plus →",
        "about_title": "À propos de moi",
        "about_name": "Svetlana",
        "about_years": "18 ans d'expérience en lecture de tarot",
        "about_specialties_label": "Spécialités :",
        "about_specialties": "Amour · Rituels",
        "about_bio_1": "Bonjour, je suis Svetlana. Je pratique le tarot depuis 18 ans, en me spécialisant dans les tirages autour de l'amour et les rituels de guidance.",
        "about_bio_2": "Je combine mon intuition avec le langage des cartes pour t'offrir des réponses claires, honnêtes et sincères. Chaque consultation est personnalisée : j'écoute ta situation avant de tirer les cartes.",
        "about_bio_3": "En plus de l'amour et des rituels, je fais aussi des tirages sur le travail, l'argent et des sujets plus généraux — quel que soit le domaine où tu as besoin de guidance, je peux t'aider.",
        "about_bio_4": "Si tu traverses une période de doute, un questionnement ou que tu cherches simplement à y voir plus clair, je suis là pour t'accompagner avec bienveillance.",
        "about_cta": "Prendre rendez-vous",
        "search_placeholder": "Rechercher une carte...",
        "filter_all": "Toutes",
        "filter_major": "Arcanes majeurs",
        "filter_cups": "Coupes",
        "filter_wands": "Bâtons",
        "filter_swords": "Épées",
        "filter_pentacles": "Deniers",
        "cards_title": "Les 78 Cartes du Tarot",
        "back_to_cards": "← Retour aux cartes",
        "upright": "À l'endroit",
        "reversed": "À l'envers",
        "section_intro": "Signification",
        "section_love": "Amour",
        "section_career": "Carrière",
        "section_money": "Finances",
        "section_health": "Santé",
        "section_family": "Famille",
        "section_symbols": "Symboles",
        "section_questions": "Questions à se poser",
        "section_weekly": "Message de la semaine",
        "section_hidden": "Message caché",
        "reading_title": "Tirage de Tarot",
        "reading_subtitle": "Que veulent te dire les cartes ?",
        "question_placeholder": "Écris ta question... (optionnel)",
        "spread_3": "3 Cartes",
        "spread_7": "7 Cartes",
        "spread_yesno": "Oui / Non",
        "spread_love": "Amour",
        "spread_work": "Carrière",
        "spread_general": "Général",
        "draw_again": "Tirer à nouveau",
        "loading": "Les cartes se mélangent...",
        "footer_note": "Le tarot est un outil de réflexion et d'inspiration, pas une prédiction scientifique.",
        "footer_privacy": "Confidentialité",
        "footer_terms": "Conditions d'utilisation",
        "footer_faq": "FAQ",
        "footer_reviews": "Avis",
        "reviews_title": "Avis de nos clients",
        "reviews_subtitle": "Ce que nos clients disent de leurs consultations.",
        "reviews_empty": "Pas encore d'avis, reviens bientôt !",
        "reviews_avg_label": "Note moyenne :",
        "faq_title": "Questions fréquentes",
        "faq_q1": "Comment ça marche ?",
        "faq_a1": "Tu crées un compte, tu reçois 1000 jetons gratuits, et tu peux faire des tirages instantanés ou prendre rendez-vous pour une consultation en direct. Chaque tirage ou rendez-vous coûte un nombre de jetons fixe, affiché avant de valider.",
        "faq_q2": "Les paiements sont-ils sécurisés ?",
        "faq_a2": "Oui. Les achats de jetons passent par Stripe ou PayPal, deux plateformes de paiement reconnues. Nous ne stockons jamais tes coordonnées bancaires.",
        "faq_q3": "Comment annuler ou changer mon rendez-vous ?",
        "faq_a3": "Contacte-nous directement via le bouton WhatsApp (en bas à droite du site) en indiquant la date de ton rendez-vous, et nous trouverons un nouveau créneau ensemble.",
        "faq_q4": "Mes informations sont-elles confidentielles ?",
        "faq_a4": "Oui, toutes tes informations (nom, question, date de naissance) restent strictement confidentielles et ne sont utilisées que pour ta consultation. Voir notre page Confidentialité pour plus de détails.",
        "faq_q5": "En combien de temps j'ai une réponse ?",
        "faq_a5": "Les tirages instantanés sont immédiats. Pour une demande de rendez-vous, nous te recontactons généralement sous 24 à 48h pour confirmer le créneau.",
        "faq_q6": "Qu'est-ce qu'un jeton et comment en acheter ?",
        "faq_a6": "Le jeton est la monnaie du site : il sert à payer les tirages et les rendez-vous. Tu peux en acheter sur la page Tirage, onglet \"Packs\", par carte (Stripe) ou PayPal.",
        "tab_services": "🔮 Consultations Tarot",
        "tab_rituals": "✨ Rituels",
        "tab_instant": "🤖 Tirage Instantané",
        "tab_packs": "🪙 Packs de Jetons",
        "buy_jeton_shortcut": "Acheter des jetons",
        "online_status_line": "en attente",
        "daily_wheel_title": "Roue quotidienne",
        "daily_wheel_spin": "Tourner !",
        "daily_wheel_come_back": "Reviens demain",
        "trust_title": "Système de confiance :",
        "trust_desc": "ta demande est enregistrée et sera étudiée personnellement. Une réponse te sera envoyée par le moyen que tu choisis.",
        "th_service": "Service",
        "th_duration": "Durée",
        "th_price": "Prix",
        "th_ritual": "Rituel",
        "select_send": "Choisir & Envoyer",
        "instant_title": "🔮 Carte du moment",
        "instant_button": "🃏 Tirer une carte",
        "spread_section_title": "🎴 Choisis un tirage",
        "packs_note": "Paiement sécurisé par Stripe.",
        "buy_pack": "Acheter",
        "buy_pack_error": "Erreur lors de la création du paiement, réessaie.",
        "checkout_success": "Paiement réussi ! Tes jetons ont été ajoutés à ton compte.",
        "checkout_cancelled": "Paiement annulé, aucun jeton n'a été débité.",
        "field_name": "Prénom",
        "field_mother": "Prénom de la mère",
        "field_birthdate": "Date de naissance",
        "field_email": "E-mail",
        "field_response_type": "Comment veux-tu la réponse ?",
        "opt_mail": "Par e-mail",
        "opt_voice": "Rendez-vous vocal",
        "opt_pdf": "Réponse en PDF",
        "field_photo": "📷 Ajouter une photo (ex. tasse de café pour une lecture de marc)",
        "jeton_balance": "Solde",
        "jeton_unit": "jetons",
        "jeton_insufficient": "Jetons insuffisants",
        "jeton_cost_label": "jetons",
        "nav_login": "Connexion",
        "nav_register": "Inscription",
        "nav_logout": "Déconnexion",
        "login_title": "Connexion",
        "login_subtitle": "Connecte-toi pour accéder à tes jetons et tes tirages.",
        "register_title": "Créer un compte",
        "register_subtitle": "Inscris-toi pour recevoir tes jetons de bienvenue.",
        "field_password": "Mot de passe",
        "field_password_confirm": "Confirmer le mot de passe",
        "field_nickname": "Pseudo (optionnel)",
        "login_submit": "Se connecter",
        "register_submit": "S'inscrire",
        "no_account_yet": "Pas encore de compte ?",
        "have_account_already": "Déjà inscrit(e) ?",
        "or_divider": "ou",
        "google_login_button": "Continuer avec Google",
        "forgot_password_link": "Mot de passe oublié ?",
        "forgot_password_title": "Mot de passe oublié",
        "forgot_password_desc": "Indique ton e-mail, on t'enverra un lien de réinitialisation.",
        "forgot_password_submit": "Envoyer le lien",
        "reset_password_title": "Nouveau mot de passe",
        "reset_password_desc": "Choisis un nouveau mot de passe.",
        "field_new_password": "Nouveau mot de passe",
        "field_new_password_confirm": "Confirmer le nouveau mot de passe",
        "reset_password_submit": "Réinitialiser le mot de passe",
        "back_to_login": "← Retour à la connexion",
        "login_required_reading": "Connecte-toi pour utiliser tes jetons.",
        "error_email_required": "Indique une adresse e-mail valide.",
        "error_password_short": "Le mot de passe doit contenir au moins 6 caractères.",
        "error_passwords_mismatch": "Les mots de passe ne correspondent pas.",
        "error_email_taken": "Cet e-mail est déjà utilisé.",
        "error_invalid_credentials": "E-mail ou mot de passe incorrect.",
        "error_reset_link_invalid": "Ce lien de réinitialisation est invalide ou expiré.",
        "error_email_not_configured": "L'envoi d'e-mails n'est pas encore configuré, réessaie plus tard.",
        "error_google_not_configured": "La connexion Google n'est pas encore configurée.",
        "success_reset_email_sent": "Si ce compte existe, un e-mail de réinitialisation a été envoyé.",
        "success_password_reset": "Mot de passe modifié, tu peux te connecter.",
        "error_rate_limited": "Trop de tentatives, réessaie dans quelques minutes.",
        "nav_account": "Mon compte",
        "account_title": "Mon compte",
        "account_email_label": "E-mail",
        "account_nickname_label": "Pseudo",
        "account_balance_label": "Solde de jetons",
        "account_login_method_label": "Méthode de connexion",
        "login_method_password": "E-mail et mot de passe",
        "login_method_google": "Compte Google lié",
        "change_password_title": "Changer le mot de passe",
        "account_no_password_note": "Tu t'es connecté(e) avec Google et n'as pas encore de mot de passe. Tu peux en définir un ci-dessous.",
        "field_current_password": "Mot de passe actuel",
        "change_password_submit": "Mettre à jour le mot de passe",
        "delete_account_title": "Supprimer mon compte",
        "delete_account_warning": "Cette action est définitive : ton adresse e-mail, ton pseudo et ton mot de passe seront supprimés. Ton solde de jetons sera perdu. L'historique de tes rendez-vous et avis peut être conservé de façon anonymisée à des fins comptables et légales.",
        "delete_account_confirm_checkbox": "Je comprends que cette action est irréversible.",
        "delete_account_submit": "Supprimer définitivement mon compte",
        "delete_account_confirm_js": "Ton compte va être supprimé définitivement. Continuer ?",
        "error_delete_account_confirm": "Merci de cocher la case de confirmation.",
        "success_account_deleted": "Ton compte a été supprimé.",
        "account_deletion_page_title": "Suppression de compte - Rituams Tarot",
        "account_deletion_intro": "Rituams Tarot te permet de supprimer ton compte et tes données personnelles à tout moment.",
        "account_deletion_steps_title": "Comment supprimer ton compte",
        "account_deletion_step1": "Connecte-toi sur ton compte Rituams Tarot.",
        "account_deletion_step2": "Va dans « Mon compte ».",
        "account_deletion_step3": "Clique sur « Supprimer définitivement mon compte » en bas de page et confirme.",
        "account_deletion_data_title": "Données supprimées",
        "account_deletion_data_text": "Ton adresse e-mail, ton pseudo, ton mot de passe (ou lien Google) et ton solde de jetons sont supprimés immédiatement et définitivement.",
        "account_deletion_retained_title": "Données conservées",
        "account_deletion_retained_text": "Pour des raisons légales et comptables, l'historique des paiements et des rendez-vous déjà effectués peut être conservé de façon anonymisée (sans lien avec ton identité) pendant la durée requise par la loi.",
        "account_deletion_no_login_title": "Tu ne peux plus te connecter ?",
        "account_deletion_no_login_text": "Écris-nous à l'adresse ci-dessous depuis l'e-mail de ton compte, en précisant que tu souhaites supprimer ton compte Rituams Tarot.",
        "account_deletion_login_link": "Se connecter pour supprimer mon compte",
        "not_found_message": "Cette page n'existe pas ou a été déplacée.",
        "back_to_home": "← Retour à l'accueil",
        "nav_horoscope": "Astrologie",
        "zodiac_hub_title": "Astrologie",
        "zodiac_hub_subtitle": "Choisis ce que tu veux découvrir.",
        "zodiac_hub_horoscope": "Horoscope du jour",
        "zodiac_hub_horoscope_desc": "Amour, travail et général pour les 12 signes, mis à jour chaque jour.",
        "zodiac_hub_character": "Caractère du signe",
        "zodiac_hub_character_desc": "Élément, planète, forces et faiblesses de chaque signe.",
        "zodiac_hub_ascendant": "Signe ascendant",
        "zodiac_hub_ascendant_desc": "Calcule ton ascendant à partir de ta date, heure et ville de naissance.",
        "horoscope_title": "Horoscope du jour",
        "horoscope_subtitle": "Mis à jour chaque jour pour les 12 signes.",
        "horoscope_love": "💕 Amour",
        "horoscope_work": "💼 Travail & Argent",
        "horoscope_general": "✨ Général",
        "zodiac_character_title": "Caractère des signes",
        "zodiac_character_subtitle": "Élément, planète et traits de personnalité des 12 signes.",
        "zodiac_element_label": "Élément",
        "zodiac_quality_label": "Qualité",
        "zodiac_planet_label": "Planète maîtresse",
        "zodiac_strengths_label": "Forces",
        "zodiac_weaknesses_label": "Faiblesses",
        "zodiac_compatible_label": "Bonne entente avec",
        "ascendant_title": "Calcule ton ascendant",
        "ascendant_subtitle": "Entre ta date, ton heure et ta ville de naissance.",
        "ascendant_field_date": "Date de naissance",
        "ascendant_field_time": "Heure de naissance",
        "ascendant_field_city": "Ville de naissance",
        "ascendant_city_placeholder": "Choisis une ville",
        "ascendant_submit": "Calculer mon ascendant",
        "ascendant_result_label": "Ton ascendant est :",
        "ascendant_error": "Merci de vérifier la date, l'heure et la ville renseignées.",
        "ascendant_disclaimer": "Calcul astronomique approximatif, à visée de réflexion et de divertissement.",
        "nav_appointment": "Rendez-vous",
        "appointment_title": "Prendre rendez-vous",
        "appointment_subtitle": "Réserve un créneau pour une consultation, on te recontacte pour confirmer.",
        "appointment_calendar_hint": "Choisis d'abord une date ci-dessous",
        "field_phone": "Numéro de téléphone",
        "field_appointment_datetime": "Date et heure souhaitées",
        "field_note": "Ta note (optionnel)",
        "field_appointment_time": "Heure",
        "appointment_submit": "Envoyer la demande de rendez-vous",
        "error_appointment_missing_fields": "Renseigne au moins ton prénom, ton téléphone, la date souhaitée et le type de consultation.",
        "error_appointment_insufficient_funds": "Tu n'as pas assez de jetons pour ce type de consultation. Achète des jetons sur la page Tirage.",
        "error_appointment_date_taken": "Cette date vient d'être réservée par quelqu'un d'autre. Choisis-en une autre.",
        "error_appointment_past": "Cette date est déjà passée. Choisis une date future.",
        "error_photo_invalid_type": "Le fichier joint doit être une image.",
        "error_photo_too_large": "La photo est trop lourde (5 Mo maximum).",
        "success_appointment_sent": "Ta demande de rendez-vous a été reçue, nous te contacterons bientôt !",
        "success_review_sent": "Merci pour ton avis !",
        "success_review_updated": "Ton avis a été mis à jour.",
        "success_review_deleted": "Ton avis a été supprimé.",
        "error_review_not_found": "Avis introuvable ou tu n'es pas l'auteur de cet avis.",
        "reviews_write_title": "Laisse ton avis",
        "reviews_login_to_write": "Connecte-toi pour laisser un avis.",
        "reviews_submit": "Envoyer",
        "reviews_update_own": "Mettre à jour",
        "reviews_delete_own": "Supprimer mon avis",
        "reviews_delete_confirm": "Supprimer ton avis ?",
        "appointment_select_date_prompt": "Choisis d'abord une date et une heure dans le calendrier.",
        "field_appointment_category": "Type de consultation",
        "appointment_category_placeholder": "Choisis un service ou un rituel",
        "appointment_balance_label": "Ton solde : {balance} jetons",
        "calendar_legend_free": "Disponible",
        "calendar_legend_busy": "Déjà réservé",
        "calendar_weekdays": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
    },
    "tr": {
        "site_title": "Rituams Tarot",
        "meta_description": "Fransızca ve Türkçe ücretsiz tarot açılımları ve bakımlar: 78 detaylı kart, farklı açılımlar, ritüeller ve kişisel rehberlik.",
        "nav_home": "Ana Sayfa",
        "nav_cards": "Kartlar",
        "nav_reading": "Açılım",
        "nav_about": "Hakkımda",
        "home_title": "Rituams Tarot – Online Tarot, Ritüel ve Kahve Falı",
        "cta_reading": "Açılım yap",
        "cta_cards": "Kartları keşfet",
        "home_about_teaser_title": "Ben kimim?",
        "home_about_teaser_text": "Svetlana, 18 yıllık tarot deneyimi, aşk ve ritüeller konusunda uzman.",
        "home_about_teaser_link": "Devamını oku →",
        "about_title": "Hakkımda",
        "about_name": "Svetlana",
        "about_years": "18 yıllık tarot okuma deneyimi",
        "about_specialties_label": "Uzmanlık alanlarım:",
        "about_specialties": "Aşk · Ritüeller",
        "about_bio_1": "Merhaba, ben Svetlana. 18 yıldır tarot kartlarıyla insanlara rehberlik ediyorum; özellikle aşk açılımları ve ritüeller konusunda derinlemesine çalışıyorum.",
        "about_bio_2": "Sezgilerimi kartların diliyle birleştirerek sana net, dürüst ve içten yanıtlar sunmaya çalışıyorum. Her danışanımı tek tek dinler, senin özel durumuna göre bir okuma yaparım.",
        "about_bio_3": "Aşk ve ritüellerin yanı sıra iş, para ve genel konularda da tarot bakımı yapıyorum — hangi konuda rehberliğe ihtiyacın olursa olsun sana yardımcı olabilirim.",
        "about_bio_4": "Bir kararsızlık, bir soru işareti ya da sadece biraz netlik arıyorsan, sana içtenlikle eşlik etmek için buradayım.",
        "about_cta": "Randevu Al",
        "search_placeholder": "Bir kart ara...",
        "filter_all": "Tümü",
        "filter_major": "Majör Arkana",
        "filter_cups": "Kase",
        "filter_wands": "Değnekler",
        "filter_swords": "Kılıçlar",
        "filter_pentacles": "Paralar",
        "cards_title": "Tarotun 78 Kartı",
        "back_to_cards": "← Kartlara dön",
        "upright": "Düz",
        "reversed": "Ters",
        "section_intro": "Anlamı",
        "section_love": "Aşk",
        "section_career": "Kariyer",
        "section_money": "Para",
        "section_health": "Sağlık",
        "section_family": "Aile",
        "section_symbols": "Semboller",
        "section_questions": "Kendine Sorman Gereken Sorular",
        "section_weekly": "Haftanın Mesajı",
        "section_hidden": "Gizli Mesaj",
        "reading_title": "Tarot Açılımı",
        "reading_subtitle": "Kartlar sana ne söylemek istiyor?",
        "question_placeholder": "Sorunuzu yazın... (opsiyonel)",
        "spread_3": "3 Kart",
        "spread_7": "7 Kart",
        "spread_yesno": "Evet / Hayır",
        "spread_love": "Aşk",
        "spread_work": "Kariyer",
        "spread_general": "Genel",
        "draw_again": "Tekrar çek",
        "loading": "Kartlar karılıyor...",
        "footer_note": "Tarot bir yansıma ve ilham aracıdır, bilimsel bir kehanet değildir.",
        "footer_privacy": "Gizlilik",
        "footer_terms": "Kullanım Şartları",
        "footer_faq": "SSS",
        "footer_reviews": "Yorumlar",
        "reviews_title": "Müşteri Yorumları",
        "reviews_subtitle": "Danışanlarımızın bakımlarımız hakkındaki yorumları.",
        "reviews_empty": "Henüz yorum yok, yakında burada olacak!",
        "reviews_avg_label": "Ortalama puan:",
        "faq_title": "Sık Sorulan Sorular",
        "faq_q1": "Sistem nasıl çalışıyor?",
        "faq_a1": "Hesap oluşturursun, 1000 jeton hediye edilir; anlık kart açılımı yapabilir ya da canlı bir bakım için randevu alabilirsin. Her açılım/randevu sabit bir jeton miktarına mal olur, onaylamadan önce sana gösterilir.",
        "faq_q2": "Ödemeler güvenli mi?",
        "faq_a2": "Evet. Jeton satın alımları Stripe veya PayPal üzerinden yapılır, ikisi de tanınmış ödeme platformlarıdır. Kart bilgilerini asla saklamayız.",
        "faq_q3": "Randevumu nasıl iptal ederim / değiştiririm?",
        "faq_a3": "Sitenin sağ altındaki WhatsApp butonuyla bize doğrudan ulaş, randevu tarihini belirt, birlikte yeni bir zaman ayarlayalım.",
        "faq_q4": "Bilgilerim gizli tutuluyor mu?",
        "faq_a4": "Evet, tüm bilgilerin (isim, sorun, doğum tarihi) kesinlikle gizli tutulur ve sadece senin bakımın için kullanılır. Detaylar için Gizlilik sayfamıza bakabilirsin.",
        "faq_q5": "Yanıtı ne kadar sürede alırım?",
        "faq_a5": "Anlık kart açılımları hemen sonuç verir. Randevu taleplerinde genellikle 24-48 saat içinde seninle iletişime geçip randevunu onaylarız.",
        "faq_q6": "Jeton nedir, nasıl satın alırım?",
        "faq_a6": "Jeton, sitenin para birimidir: açılım ve randevu ödemelerinde kullanılır. Açılım sayfasındaki \"Paketler\" sekmesinden kart (Stripe) veya PayPal ile satın alabilirsin.",
        "tab_services": "🔮 Tarot Bakımları",
        "tab_rituals": "✨ Ritüeller",
        "tab_instant": "🤖 Anında Açılım",
        "tab_packs": "🪙 Jeton Paketleri",
        "buy_jeton_shortcut": "Jeton Al",
        "online_status_line": "bekleniyor",
        "daily_wheel_title": "Günlük Çark",
        "daily_wheel_spin": "Çevir!",
        "daily_wheel_come_back": "Yarın tekrar gel",
        "trust_title": "Güven sistemi:",
        "trust_desc": "talebin kaydedilir ve kişisel olarak incelenir. Seçtiğin yöntemle sana geri dönüş yapılır.",
        "th_service": "Hizmet",
        "th_duration": "Süre",
        "th_price": "Fiyat",
        "th_ritual": "Ritüel",
        "select_send": "Seç & Gönder",
        "instant_title": "🔮 Anlık Kart",
        "instant_button": "🃏 Kart Çek",
        "spread_section_title": "🎴 Açılım Seç",
        "packs_note": "Ödemeler Stripe ile güvenli şekilde yapılır.",
        "buy_pack": "Satın Al",
        "buy_pack_error": "Ödeme oluşturulurken hata oluştu, tekrar dene.",
        "checkout_success": "Ödeme başarılı! Jetonların hesabına eklendi.",
        "checkout_cancelled": "Ödeme iptal edildi, jeton düşülmedi.",
        "field_name": "İsim",
        "field_mother": "Anne adı",
        "field_birthdate": "Doğum tarihi",
        "field_email": "E-posta",
        "field_response_type": "Cevabı nasıl istersin?",
        "opt_mail": "Mail ile",
        "opt_voice": "Sesli randevu",
        "opt_pdf": "PDF cevap",
        "field_photo": "📷 Fotoğraf ekle (ör. kahve falı için fincan fotoğrafı)",
        "jeton_balance": "Bakiye",
        "jeton_unit": "jeton",
        "jeton_insufficient": "Yetersiz jeton",
        "jeton_cost_label": "jeton",
        "nav_login": "Giriş Yap",
        "nav_register": "Kayıt Ol",
        "nav_logout": "Çıkış Yap",
        "login_title": "Giriş Yap",
        "login_subtitle": "Jetonlarına ve açılımlarına erişmek için giriş yap.",
        "register_title": "Hesap Oluştur",
        "register_subtitle": "Kayıt ol ve hoş geldin jetonlarını al.",
        "field_password": "Şifre",
        "field_password_confirm": "Şifreyi onayla",
        "field_nickname": "Rumuz (opsiyonel)",
        "login_submit": "Giriş Yap",
        "register_submit": "Kayıt Ol",
        "no_account_yet": "Hesabın yok mu?",
        "have_account_already": "Zaten hesabın var mı?",
        "or_divider": "veya",
        "google_login_button": "Google ile devam et",
        "forgot_password_link": "Şifreni mi unuttun?",
        "forgot_password_title": "Şifremi Unuttum",
        "forgot_password_desc": "E-posta adresini yaz, sana bir sıfırlama bağlantısı gönderelim.",
        "forgot_password_submit": "Bağlantıyı Gönder",
        "reset_password_title": "Yeni Şifre",
        "reset_password_desc": "Yeni bir şifre seç.",
        "field_new_password": "Yeni şifre",
        "field_new_password_confirm": "Yeni şifreyi onayla",
        "reset_password_submit": "Şifreyi Sıfırla",
        "back_to_login": "← Girişe dön",
        "login_required_reading": "Jetonlarını kullanmak için giriş yap.",
        "error_email_required": "Geçerli bir e-posta adresi gir.",
        "error_password_short": "Şifre en az 6 karakter olmalı.",
        "error_passwords_mismatch": "Şifreler eşleşmiyor.",
        "error_email_taken": "Bu e-posta zaten kullanılıyor.",
        "error_invalid_credentials": "E-posta veya şifre hatalı.",
        "error_reset_link_invalid": "Bu sıfırlama bağlantısı geçersiz veya süresi dolmuş.",
        "error_email_not_configured": "E-posta gönderimi henüz yapılandırılmadı, daha sonra tekrar dene.",
        "error_google_not_configured": "Google ile giriş henüz yapılandırılmadı.",
        "success_reset_email_sent": "Bu hesap varsa, bir sıfırlama e-postası gönderildi.",
        "success_password_reset": "Şifre değiştirildi, giriş yapabilirsin.",
        "error_rate_limited": "Çok fazla deneme yaptın, birkaç dakika sonra tekrar dene.",
        "nav_account": "Hesabım",
        "account_title": "Hesabım",
        "account_email_label": "E-posta",
        "account_nickname_label": "Rumuz",
        "account_balance_label": "Jeton Bakiyesi",
        "account_login_method_label": "Giriş yöntemi",
        "login_method_password": "E-posta ve şifre",
        "login_method_google": "Google hesabı bağlı",
        "change_password_title": "Şifre Değiştir",
        "account_no_password_note": "Google ile giriş yaptın ve henüz bir şifren yok. Aşağıdan bir şifre belirleyebilirsin.",
        "field_current_password": "Mevcut şifre",
        "change_password_submit": "Şifreyi Güncelle",
        "delete_account_title": "Hesabımı Sil",
        "delete_account_warning": "Bu işlem kalıcıdır: e-posta adresin, kullanıcı adın ve şifren silinir. Jeton bakiyen kaybolur. Randevu ve yorum geçmişin, muhasebe ve yasal zorunluluklar gereği anonim şekilde saklanabilir.",
        "delete_account_confirm_checkbox": "Bu işlemin geri alınamayacağını anlıyorum.",
        "delete_account_submit": "Hesabımı Kalıcı Olarak Sil",
        "delete_account_confirm_js": "Hesabın kalıcı olarak silinecek. Devam edilsin mi?",
        "error_delete_account_confirm": "Lütfen onay kutusunu işaretle.",
        "success_account_deleted": "Hesabın silindi.",
        "account_deletion_page_title": "Hesap Silme - Rituams Tarot",
        "account_deletion_intro": "Rituams Tarot, hesabını ve kişisel verilerini istediğin zaman silmene olanak tanır.",
        "account_deletion_steps_title": "Hesabını nasıl silersin",
        "account_deletion_step1": "Rituams Tarot hesabına giriş yap.",
        "account_deletion_step2": "\"Hesabım\" sayfasına git.",
        "account_deletion_step3": "Sayfanın altındaki \"Hesabımı Kalıcı Olarak Sil\" butonuna tıkla ve onayla.",
        "account_deletion_data_title": "Silinen veriler",
        "account_deletion_data_text": "E-posta adresin, kullanıcı adın, şifren (veya Google bağlantın) ve jeton bakiyen hemen ve kalıcı olarak silinir.",
        "account_deletion_retained_title": "Saklanan veriler",
        "account_deletion_retained_text": "Yasal ve muhasebe zorunlulukları nedeniyle, daha önce yapılmış ödeme ve randevu kayıtları kimliğinden arındırılmış (anonim) şekilde, yasanın gerektirdiği süre boyunca saklanabilir.",
        "account_deletion_no_login_title": "Artık giriş yapamıyor musun?",
        "account_deletion_no_login_text": "Hesabındaki e-posta adresinden bize yazarak Rituams Tarot hesabını silmek istediğini belirt.",
        "account_deletion_login_link": "Hesabımı silmek için giriş yap",
        "not_found_message": "Bu sayfa mevcut değil ya da taşınmış.",
        "back_to_home": "← Ana sayfaya dön",
        "nav_horoscope": "Burçlar",
        "zodiac_hub_title": "Burçlar",
        "zodiac_hub_subtitle": "Ne öğrenmek istersin?",
        "zodiac_hub_horoscope": "Günlük Burç Yorumu",
        "zodiac_hub_horoscope_desc": "12 burç için aşk, iş-para ve genel yorumlar, her gün otomatik güncellenir.",
        "zodiac_hub_character": "Burç Karakteri",
        "zodiac_hub_character_desc": "Her burcun elementi, gezegeni, güçlü ve zayıf yönleri.",
        "zodiac_hub_ascendant": "Yükselen Burç",
        "zodiac_hub_ascendant_desc": "Doğum tarihin, saatin ve yerinden yükselen burcunu hesapla.",
        "horoscope_title": "Günlük Burç Yorumu",
        "horoscope_subtitle": "12 burç için her gün otomatik güncellenir.",
        "horoscope_love": "💕 Aşk",
        "horoscope_work": "💼 İş & Para",
        "horoscope_general": "✨ Genel",
        "zodiac_character_title": "Burç Karakterleri",
        "zodiac_character_subtitle": "12 burcun elementi, gezegeni ve kişilik özellikleri.",
        "zodiac_element_label": "Element",
        "zodiac_quality_label": "Nitelik",
        "zodiac_planet_label": "Yönetici Gezegen",
        "zodiac_strengths_label": "Güçlü Yönler",
        "zodiac_weaknesses_label": "Zayıf Yönler",
        "zodiac_compatible_label": "Uyumlu Olduğu Burçlar",
        "ascendant_title": "Yükselen Burcunu Hesapla",
        "ascendant_subtitle": "Doğum tarihini, saatini ve yerini gir.",
        "ascendant_field_date": "Doğum Tarihi",
        "ascendant_field_time": "Doğum Saati",
        "ascendant_field_city": "Doğum Yeri",
        "ascendant_city_placeholder": "Bir şehir seç",
        "ascendant_submit": "Yükselen Burcumu Hesapla",
        "ascendant_result_label": "Yükselen burcun:",
        "ascendant_error": "Girdiğin tarih, saat ve şehri kontrol eder misin.",
        "ascendant_disclaimer": "Yaklaşık bir astronomik hesaplamadır, yansıma ve eğlence amaçlıdır.",
        "nav_appointment": "Randevu Al",
        "appointment_title": "Randevu Al",
        "appointment_subtitle": "Bir bakım için randevu talebinde bulun, seninle iletişime geçip onaylayalım.",
        "appointment_calendar_hint": "Önce aşağıdan bir tarih seç",
        "field_phone": "Telefon Numarası",
        "field_appointment_datetime": "İstenen tarih ve saat",
        "field_note": "Notun (opsiyonel)",
        "field_appointment_time": "Saat",
        "appointment_submit": "Randevu Talebi Gönder",
        "error_appointment_missing_fields": "En azından isim, telefon numarası, istenen tarih ve açılım türünü doldur.",
        "error_appointment_insufficient_funds": "Bu açılım için yeterli jetonun yok. Kartlar sayfasından jeton satın alabilirsin.",
        "error_appointment_date_taken": "Bu tarih az önce başkası tarafından alındı. Başka bir tarih seç.",
        "error_appointment_past": "Bu tarih geçmişte kalmış. İleri bir tarih seç.",
        "error_photo_invalid_type": "Eklenen dosya bir resim olmalı.",
        "error_photo_too_large": "Fotoğraf çok büyük (en fazla 5 MB).",
        "success_appointment_sent": "Randevu talebin alındı, en kısa sürede seninle iletişime geçeceğiz!",
        "success_review_sent": "Yorumun için teşekkürler!",
        "success_review_updated": "Yorumun güncellendi.",
        "success_review_deleted": "Yorumun silindi.",
        "error_review_not_found": "Yorum bulunamadı ya da bu yorumun sahibi değilsin.",
        "reviews_write_title": "Yorumunu yaz",
        "reviews_login_to_write": "Yorum yazmak için giriş yap.",
        "reviews_submit": "Gönder",
        "reviews_update_own": "Güncelle",
        "reviews_delete_own": "Yorumumu Sil",
        "reviews_delete_confirm": "Yorumunu silmek istediğine emin misin?",
        "appointment_select_date_prompt": "Önce takvimden bir tarih ve saat seç.",
        "field_appointment_category": "Açılım Türü",
        "appointment_category_placeholder": "Bir hizmet ya da ritüel seç",
        "appointment_balance_label": "Bakiyen: {balance} jeton",
        "calendar_legend_free": "Müsait",
        "calendar_legend_busy": "Dolu",
        "calendar_weekdays": ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"],
    },
}

SERVICES = [
    {"id": "single", "duration": {"fr": "5 min", "tr": "5 dk"}, "cost": 300,
     "name": {"fr": "Consultation à question unique", "tr": "Tek Soru Bakımı"}},
    {"id": "coffee", "duration": {"fr": "15 min", "tr": "15 dk"}, "cost": 500,
     "name": {"fr": "Lecture de Marc de Café", "tr": "Kahve Falı"}},
    {"id": "triple", "duration": {"fr": "10 min", "tr": "10 dk"}, "cost": 700,
     "name": {"fr": "Consultation à 3 questions", "tr": "3 Soru Bakımı"}},
    {"id": "love", "duration": {"fr": "20 min", "tr": "20 dk"}, "cost": 1000,
     "name": {"fr": "Consultation Amour", "tr": "Aşk Açılımı"}},
    {"id": "general", "duration": {"fr": "30 min", "tr": "30 dk"}, "cost": 1500,
     "name": {"fr": "Consultation Générale", "tr": "Genel Bakım"}},
]

RITUALS = [
    {"id": "love", "emoji": "❤️", "cost": 800,
     "name": {"fr": "Amour et Relation", "tr": "Aşk ve İlişki"}},
    {"id": "self_attraction", "emoji": "💘", "cost": 800,
     "name": {"fr": "Attraction et Séduction", "tr": "Kendini Sevdirme"}},
    {"id": "social", "emoji": "🌟", "cost": 800,
     "name": {"fr": "Popularité et Reconnaissance Sociale", "tr": "Toplumda Sevilme"}},
    {"id": "confidence", "emoji": "💖", "cost": 800,
     "name": {"fr": "Confiance en soi et Attraction", "tr": "Öz Güven ve Çekim Gücü"}},
    {"id": "career", "emoji": "💼", "cost": 800,
     "name": {"fr": "Carrière et Réussite", "tr": "İş ve Kariyer"}},
    {"id": "family", "emoji": "🏡", "cost": 800,
     "name": {"fr": "Harmonie Familiale", "tr": "Aile Huzuru"}},
    {"id": "reunite", "emoji": "🔄", "cost": 800,
     "name": {"fr": "Retour de l'Être Aimé", "tr": "Geri Getirme"}},
    {"id": "binding", "emoji": "🔗", "cost": 800,
     "name": {"fr": "Rituel de Liaison (Bağlama)", "tr": "Bağlama Ritüeli"}},
    {"id": "luck", "emoji": "🍀", "cost": 800,
     "name": {"fr": "Chance et Abondance", "tr": "Şans ve Bolluk"}},
    {"id": "cleanse", "emoji": "🕊️", "cost": 800,
     "name": {"fr": "Purification des Énergies Négatives", "tr": "Negatif Enerjiden Arınma"}},
    {"id": "intention", "emoji": "🌙", "cost": 1500,
     "name": {"fr": "Rituel d'Intention Personnelle", "tr": "Kişisel Niyet Ritüeli"}},
]

REQUEST_CATEGORIES = (
    [{"id": f"service:{s['id']}", "group": "service", "cost": s["cost"], "name": s["name"]} for s in SERVICES]
    + [{"id": f"ritual:{r['id']}", "group": "ritual", "cost": r["cost"], "name": r["name"]} for r in RITUALS]
)
REQUEST_CATEGORY_COST = {c["id"]: c["cost"] for c in REQUEST_CATEGORIES}
REQUEST_CATEGORY_NAME = {c["id"]: c["name"] for c in REQUEST_CATEGORIES}


def localized_request_categories():
    lang = get_lang()
    return [
        {"id": c["id"], "group": c["group"], "cost": c["cost"], "name": c["name"][lang]}
        for c in REQUEST_CATEGORIES
    ]

JETON_PACKS = [
    {"amount": 200, "price": "£4.99", "price_value": 4.99, "stripe_price_id": "price_1U9od2LYpYxtFvCYCu69apgZ"},
    {"amount": 500, "price": "£9.99", "price_value": 9.99, "stripe_price_id": "price_1U9odELYpYxtFvCYeOxxxDac"},
    {"amount": 1200, "price": "£19.99", "price_value": 19.99, "stripe_price_id": "price_1U9odGLYpYxtFvCYK1tnGZup"},
    {"amount": 3000, "price": "£39.99", "price_value": 39.99, "stripe_price_id": "price_1U9odJLYpYxtFvCY1Qlbgtoo"},
    {"amount": 8000, "price": "£89.99", "price_value": 89.99, "stripe_price_id": "price_1U9odLLYpYxtFvCY4YjrF4VE"},
]
JETON_PACKS_BY_AMOUNT = {p["amount"]: p for p in JETON_PACKS}

SPREADS = {
    "3-card": {
        "count": 3,
        "positions": {
            "fr": ["Passé", "Présent", "Avenir"],
            "tr": ["Geçmiş", "Şimdiki", "Gelecek"],
        },
        "name": {"fr": "Tirage en 3 Cartes", "tr": "3 Kart Açılımı"},
    },
    "7-card": {
        "count": 7,
        "positions": {
            "fr": ["Situation", "Défi", "Soutien", "Futur proche", "Futur lointain", "Conseil", "Résultat"],
            "tr": ["Durum", "Zorluk", "Destek", "Yakın Gelecek", "Uzak Gelecek", "Tavsiye", "Sonuç"],
        },
        "name": {"fr": "Tirage en 7 Cartes", "tr": "7 Kart Açılımı"},
    },
    "yes-no": {
        "count": 1,
        "positions": {"fr": ["Réponse"], "tr": ["Cevap"]},
        "name": {"fr": "Tirage Oui / Non", "tr": "Evet / Hayır Açılımı"},
    },
    "love": {
        "count": 5,
        "positions": {
            "fr": ["État actuel", "Votre partenaire", "Vos sentiments", "Direction de la relation", "Conseil"],
            "tr": ["Mevcut Durum", "Partneriniz", "Hissettikleriniz", "İlişkinin Yönü", "Tavsiye"],
        },
        "name": {"fr": "Tirage Amour", "tr": "Aşk Açılımı"},
    },
    "work": {
        "count": 5,
        "positions": {
            "fr": ["Carrière actuelle", "Défis", "Opportunités", "Futur proche", "Conseil"],
            "tr": ["Mevcut Kariyer", "Zorluklar", "Fırsatlar", "Yakın Gelecek", "Tavsiye"],
        },
        "name": {"fr": "Tirage Carrière", "tr": "İş Açılımı"},
    },
    "general": {
        "count": 6,
        "positions": {
            "fr": ["Passé", "Présent", "Futur proche", "Conseil", "Facteurs externes", "Résultat"],
            "tr": ["Geçmiş", "Şimdiki", "Yakın Gelecek", "Tavsiye", "Dış Etkenler", "Sonuç"],
        },
        "name": {"fr": "Tirage Général", "tr": "Genel Okuyuş"},
    },
}

POSITIVE_MAJOR_IDS = {
    "00_joker", "01_sihirbaz", "03_imparatorice", "04_imparator", "06_asiklar",
    "07_savas_arabasi", "08_guc", "10_kader_carki", "11_adalet", "17_yildiz",
    "19_gunes", "21_dunya",
}
NEGATIVE_MAJOR_IDS = {"13_olum", "15_iblis", "16_kule", "18_ay"}


def get_lang():
    lang = request.args.get("lang") or request.cookies.get("lang") or DEFAULT_LANG
    return lang if lang in LANGS else DEFAULT_LANG


def ui(lang):
    return UI[lang]


@app.context_processor
def inject_globals():
    lang = get_lang()
    canonical_url = hreflang_fr = hreflang_tr = None
    if request.endpoint and request.method == "GET":
        try:
            view_args = request.view_args or {}
            canonical_url = external_url(request.endpoint, **view_args)
            hreflang_fr = external_url(request.endpoint, lang="fr", **view_args)
            hreflang_tr = external_url(request.endpoint, lang="tr", **view_args)
        except Exception:
            pass
    return {
        "lang": lang,
        "other_lang": "tr" if lang == "fr" else "fr",
        "t": ui(lang),
        "logged_in": bool(session.get("email")),
        "current_nickname": session.get("nickname"),
        "whatsapp_link": f"https://wa.me/{WHATSAPP_NUMBER}" if WHATSAPP_NUMBER else None,
        "instagram_url": INSTAGRAM_URL,
        "tiktok_url": TIKTOK_URL,
        "is_admin": is_admin(),
        "canonical_url": canonical_url,
        "hreflang_fr": hreflang_fr,
        "hreflang_tr": hreflang_tr,
    }


@app.after_request
def remember_lang(resp):
    resp.set_cookie("lang", get_lang(), max_age=60 * 60 * 24 * 365)
    return resp


def card_public(card, lang):
    return {
        "id": card["id"],
        "number": card["number"],
        "arcana": card["arcana"],
        "suit": card["suit"],
        "name": card["name"][lang],
        "image": url_for("static", filename=f"img/cards/{card['image']}"),
    }


def card_side(card, orientation, lang):
    content = card[orientation][lang]
    return {
        "id": card["id"],
        "number": card["number"],
        "arcana": card["arcana"],
        "suit": card["suit"],
        "name": card["name"][lang],
        "image": url_for("static", filename=f"img/cards/{card['image']}"),
        "orientation": orientation,
        "intro": content["intro"],
        "love": content["love"],
        "career": content["career"],
        "money": content["money"],
        "health": content["health"],
        "family": content["family"],
        "symbols": content["symbols"],
        "questions": content["questions"],
        "weekly": content["weekly"],
        "hidden": content["hidden"],
    }


def draw_spread(spread_key, lang):
    spread = SPREADS[spread_key]
    count = spread["count"]
    cards = random.sample(CARDS, count)
    positions = spread["positions"][lang]

    result_cards = []
    for card in cards:
        orientation = random.choice(["upright", "reversed"])
        result_cards.append(card_side(card, orientation, lang))

    payload = {
        "type": spread_key,
        "name": spread["name"][lang],
        "spread": [
            {"position": positions[i], "card": result_cards[i]}
            for i in range(count)
        ],
    }

    if spread_key == "yes-no":
        card = cards[0]
        c = result_cards[0]
        is_upright = c["orientation"] == "upright"
        is_positive = card["id"] in POSITIVE_MAJOR_IDS
        is_negative = card["id"] in NEGATIVE_MAJOR_IDS
        if is_negative and not is_upright:
            yes = False
        elif is_positive or not is_negative:
            yes = is_upright
        else:
            yes = not is_upright
        answer_key = "yes" if yes else "no"
        answers = {
            "fr": {"yes": "Oui ✨", "no": "Non ❌"},
            "tr": {"yes": "Evet ✨", "no": "Hayır ❌"},
        }
        payload["answer"] = answers[lang][answer_key]

    return payload


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/robots.txt")
def robots_txt():
    lines = [
        "User-agent: *",
        "Disallow: /api/",
        "Disallow: /admin/",
        "Disallow: /hesabim",
        "Disallow: /randevu-al",
        "Disallow: /connexion",
        "Disallow: /inscription",
        "Disallow: /mot-de-passe-oublie",
        "Disallow: /reinitialiser/",
        "Disallow: /auth/",
        f"Sitemap: {external_url('sitemap_xml')}",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@app.route("/.well-known/assetlinks.json")
def asset_links():
    return jsonify([{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": "com.rituams.tarot",
            "sha256_cert_fingerprints": [
                "B0:5D:9B:F0:C2:9C:0A:9F:8E:E4:47:B9:7C:9C:41:7B:66:E4:86:42:79:7E:EF:F3:62:64:1F:72:57:FD:8A:99"
            ]
        }
    }])


SITEMAP_ENDPOINTS = ["index", "about_page", "faq_page", "reviews_page", "privacy_page", "terms_page", "cards_page", "reading_page", "zodiac_hub", "horoscope_page", "zodiac_character_page", "ascendant_page", "account_deletion_info_page"]


@app.route("/sitemap.xml")
def sitemap_xml():
    urls = [external_url(endpoint) for endpoint in SITEMAP_ENDPOINTS]
    urls += [external_url("card_detail", card_id=card["id"]) for card in CARDS]

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for url in urls:
        sep = "&" if "?" in url else "?"
        parts.append(
            f"<url><loc>{url}</loc>"
            f'<xhtml:link rel="alternate" hreflang="fr" href="{url}{sep}lang=fr"/>'
            f'<xhtml:link rel="alternate" hreflang="tr" href="{url}{sep}lang=tr"/>'
            f"</url>"
        )
    parts.append("</urlset>")
    return Response("\n".join(parts), mimetype="application/xml")


@app.route("/hakkimda")
def about_page():
    return render_template("about.html")


@app.route("/sss")
def faq_page():
    return render_template("faq.html")


@app.route("/gizlilik-politikasi")
def privacy_page():
    return render_template("privacy.html")


@app.route("/kullanim-sartlari")
def terms_page():
    return render_template("terms.html")


@app.route("/cartes")
def cards_page():
    lang = get_lang()
    cards = [card_public(c, lang) for c in CARDS]
    return render_template("cards.html", cards=cards)


@app.route("/cartes/<card_id>")
def card_detail(card_id):
    lang = get_lang()
    card = CARDS_BY_ID.get(card_id)
    if not card:
        return redirect(url_for("cards_page"))
    return render_template(
        "card_detail.html",
        card=card,
        upright=card_side(card, "upright", lang),
        reversed=card_side(card, "reversed", lang),
    )


@app.route("/inscription", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def register_page():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""
        nickname = (request.form.get("nickname") or "").strip()

        if not email or "@" not in email:
            flash("error_email_required", "error")
        elif len(password) < 6:
            flash("error_password_short", "error")
        elif password != password2:
            flash("error_passwords_mismatch", "error")
        elif accounts_store.email_exists(email):
            flash("error_email_taken", "error")
        else:
            account = accounts_store.create_account(email, password, nickname)
            if not account:
                flash("error_email_taken", "error")
            else:
                send_email_async(
                    GMAIL_ADDRESS,
                    "Yeni üye kaydı - Rituams Tarot",
                    f"Yeni bir kullanıcı kayıt oldu.\n\nRumuz: {account['nickname']}\nE-posta: {account['email']}",
                )
                session["email"] = account["email"]
                session["nickname"] = account["nickname"]
                return redirect(url_for("reading_page"))
    return render_template("register.html")


@app.route("/connexion", methods=["GET", "POST"])
@limiter.limit("15 per minute", methods=["POST"])
def login_page():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        if accounts_store.verify_password(email, password):
            account = accounts_store.get_account(email)
            session["email"] = account["email"]
            session["nickname"] = account["nickname"]
            return redirect(url_for("reading_page"))
        flash("error_invalid_credentials", "error")
    return render_template("login.html")


@app.route("/deconnexion")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/hesabim", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def account_page():
    email = session.get("email")
    if not email:
        return redirect(url_for("login_page"))
    account = accounts_store.get_account(email)

    if request.method == "POST":
        action = request.form.get("action") or "change_password"
        if action == "delete_account":
            current_password = request.form.get("delete_current_password") or ""
            confirm = request.form.get("confirm_delete")
            if account.get("password_hash") and not accounts_store.verify_password(email, current_password):
                flash("error_invalid_credentials", "error")
            elif not confirm:
                flash("error_delete_account_confirm", "error")
            else:
                accounts_store.delete_account(email)
                session.clear()
                flash("success_account_deleted", "success")
                return redirect(url_for("index"))
        else:
            current_password = request.form.get("current_password") or ""
            new_password = request.form.get("new_password") or ""
            new_password2 = request.form.get("new_password2") or ""
            if account.get("password_hash") and not accounts_store.verify_password(email, current_password):
                flash("error_invalid_credentials", "error")
            elif len(new_password) < 6:
                flash("error_password_short", "error")
            elif new_password != new_password2:
                flash("error_passwords_mismatch", "error")
            else:
                accounts_store.set_password(email, new_password)
                flash("success_password_reset", "success")
                account = accounts_store.get_account(email)

    balance = "∞" if is_admin() else jeton_store.get_balance(email)
    return render_template("account.html", account=account, balance=balance)


@app.route("/hesap-silme")
def account_deletion_info_page():
    return render_template("account_deletion.html", contact_email=GMAIL_ADDRESS)


@app.route("/mot-de-passe-oublie", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def forgot_password_page():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if accounts_store.email_exists(email):
            token = get_serializer().dumps(email, salt="password-reset")
            reset_url = external_url("reset_password_page", token=token)
            lang = get_lang()
            if lang == "fr":
                subject = "Réinitialisation de mot de passe - Rituams Tarot"
                body = (
                    "Bonjour,\n\n"
                    "Clique sur ce lien pour réinitialiser ton mot de passe "
                    f"(valable 1 heure) :\n{reset_url}\n\n"
                    "Si tu n'es pas à l'origine de cette demande, ignore ce message."
                )
            else:
                subject = "Şifre Sıfırlama - Rituams Tarot"
                body = (
                    "Merhaba,\n\n"
                    "Şifreni sıfırlamak için bu bağlantıya tıkla "
                    f"(1 saat geçerlidir):\n{reset_url}\n\n"
                    "Bu talebi sen yapmadıysan bu e-postayı yok sayabilirsin."
                )
            if send_email(email, subject, body):
                flash("success_reset_email_sent", "success")
            else:
                flash("error_email_not_configured", "error")
        else:
            flash("success_reset_email_sent", "success")
    return render_template("forgot_password.html")


@app.route("/reinitialiser/<token>", methods=["GET", "POST"])
def reset_password_page(token):
    try:
        email = get_serializer().loads(token, salt="password-reset", max_age=3600)
    except (BadSignature, SignatureExpired):
        flash("error_reset_link_invalid", "error")
        return redirect(url_for("forgot_password_page"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""
        if len(password) < 6:
            flash("error_password_short", "error")
        elif password != password2:
            flash("error_passwords_mismatch", "error")
        else:
            accounts_store.set_password(email, password)
            flash("success_password_reset", "success")
            return redirect(url_for("login_page"))
    return render_template("reset_password.html", token=token)


@app.route("/auth/google/login")
def google_login():
    if not GOOGLE_CLIENT_ID:
        flash("error_google_not_configured", "error")
        return redirect(url_for("login_page"))
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": external_url("google_callback"),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return redirect(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@app.route("/auth/google/callback")
def google_callback():
    state = request.args.get("state")
    code = request.args.get("code")
    if not code or not state or state != session.pop("oauth_state", None):
        flash("error_google_not_configured", "error")
        return redirect(url_for("login_page"))

    try:
        token_resp = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": external_url("google_callback"),
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise ValueError("no access token")
        userinfo = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        ).json()
    except (requests.RequestException, ValueError):
        flash("error_google_not_configured", "error")
        return redirect(url_for("login_page"))

    email = (userinfo.get("email") or "").strip().lower()
    if not email or not userinfo.get("email_verified"):
        flash("error_google_not_configured", "error")
        return redirect(url_for("login_page"))

    name = userinfo.get("name") or email.split("@")[0]
    is_new_account = not accounts_store.email_exists(email)
    account = accounts_store.upsert_google_account(email, userinfo.get("sub"), name)
    if is_new_account:
        send_email_async(
            GMAIL_ADDRESS,
            "Yeni üye kaydı - Rituams Tarot",
            f"Yeni bir kullanıcı Google ile kayıt oldu.\n\nRumuz: {account['nickname']}\nE-posta: {account['email']}",
        )
    session["email"] = account["email"]
    session["nickname"] = account["nickname"]
    return redirect(url_for("reading_page"))


MAJOR_CARDS = [c for c in CARDS if c["arcana"] == "major"]


@app.route("/tirage")
def reading_page():
    lang = get_lang()
    checkout_status = request.args.get("checkout")
    if checkout_status == "success":
        flash("checkout_success", "success")
    elif checkout_status == "cancel":
        flash("checkout_cancelled", "error")
    services = [
        {"id": s["id"], "name": s["name"][lang], "duration": s["duration"][lang], "cost": s["cost"]}
        for s in SERVICES
    ]
    rituals = [
        {"id": r["id"], "name": r["name"][lang], "emoji": r["emoji"], "cost": r["cost"]}
        for r in RITUALS
    ]
    return render_template(
        "reading.html",
        spreads=SPREADS,
        services=services,
        rituals=rituals,
        packs=JETON_PACKS,
        spread_cost=jeton_store.SPREAD_COST,
        instant_cost=jeton_store.INSTANT_COST,
        paypal_client_id=PAYPAL_CLIENT_ID,
    )


@app.route("/api/tirage/<spread_key>", methods=["POST"])
def api_reading(spread_key):
    if spread_key not in SPREADS:
        return jsonify({"ok": False, "error": "unknown spread"}), 404
    lang = get_lang()
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    email = session.get("email")

    if not email:
        return jsonify({"ok": False, "error": "login_required"}), 401

    if is_admin():
        balance = "∞"
    else:
        ok, balance = jeton_store.deduct(email, jeton_store.SPREAD_COST)
        if not ok:
            return jsonify({"ok": False, "error": "insufficient_funds", "balance": balance, "cost": jeton_store.SPREAD_COST}), 402

    result = draw_spread(spread_key, lang)
    result["ok"] = True
    result["question"] = question
    result["remaining_jeton"] = balance
    return jsonify(result)


@app.route("/api/anlik", methods=["POST"])
def api_instant_card():
    email = session.get("email")
    if not email:
        return jsonify({"ok": False, "error": "login_required"}), 401

    if is_admin():
        balance = "∞"
    else:
        ok, balance = jeton_store.deduct(email, jeton_store.INSTANT_COST)
        if not ok:
            return jsonify({"ok": False, "error": "insufficient_funds", "balance": balance, "cost": jeton_store.INSTANT_COST}), 402

    lang = get_lang()
    card = random.choice(MAJOR_CARDS)
    return jsonify({"ok": True, "card": card_side(card, "upright", lang), "remaining_jeton": balance})


@app.route("/api/jeton")
def api_jeton_balance():
    email = session.get("email")
    if not email:
        return jsonify({"ok": False, "error": "login_required"}), 401
    if is_admin():
        return jsonify({
            "ok": True,
            "balance": "∞",
            "nickname": session.get("nickname"),
        })
    return jsonify({
        "ok": True,
        "balance": jeton_store.get_balance(email),
        "nickname": session.get("nickname"),
    })


@app.route("/api/gunluk-carki/durum")
def api_daily_wheel_status():
    email = session.get("email")
    if not email:
        return jsonify({"ok": False, "error": "login_required"}), 401
    return jsonify({"ok": True, "can_spin": jeton_store.daily_bonus_available(email)})


@app.route("/api/gunluk-carki/cevir", methods=["POST"])
@limiter.limit("20 per hour")
def api_daily_wheel_spin():
    email = session.get("email")
    if not email:
        return jsonify({"ok": False, "error": "login_required"}), 401
    won, amount, index, balance = jeton_store.claim_daily_bonus(email)
    if not won:
        return jsonify({"ok": False, "error": "already_spun", "balance": "∞" if is_admin() else balance}), 409
    return jsonify({
        "ok": True,
        "amount": amount,
        "index": index,
        "balance": "∞" if is_admin() else balance,
    })


MAX_PHOTO_SIZE = 5 * 1024 * 1024


def extract_photo_from_request():
    """Retourne (photo_filestorage, photo_bytes, error_flash_key). photo est None si aucune photo fournie."""
    photo = request.files.get("photo")
    if not photo or not photo.filename:
        return None, None, None
    if not (photo.mimetype or "").startswith("image/"):
        return None, None, "error_photo_invalid_type"
    photo_bytes = photo.read(MAX_PHOTO_SIZE + 1)
    if len(photo_bytes) > MAX_PHOTO_SIZE:
        return None, None, "error_photo_too_large"
    return photo, photo_bytes, None


@app.route("/randevu-al", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def appointment_page():
    user_email = session.get("email")
    if not user_email:
        flash("login_required_reading", "error")
        return redirect(url_for("login_page"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        contact_email = (request.form.get("email") or "").strip()
        mother_name = (request.form.get("motherName") or "").strip()
        birth_date = (request.form.get("birthDate") or "").strip()
        response_type = (request.form.get("responseType") or "mail").strip()
        appointment_date = (request.form.get("appointment_date") or "").strip()
        note = (request.form.get("note") or "").strip()
        category = (request.form.get("category") or "").strip()
        cost = REQUEST_CATEGORY_COST.get(category)
        requested_day = appointment_date.split("T")[0]
        existing_appointments = appointments_store.list_appointments()
        times_by_day = _booked_times_by_day(existing_appointments)
        blocked_days = set(appointments_store.list_blocked_dates())
        day_fully_booked = requested_day in blocked_days or len(times_by_day.get(requested_day, ())) >= len(APPOINTMENT_TIME_SLOTS)
        slot_taken = appointment_date in {a["appointmentDate"] for a in existing_appointments if a.get("appointmentDate")}
        try:
            appt_dt = datetime.fromisoformat(appointment_date) if appointment_date else None
        except ValueError:
            appt_dt = None
        photo, photo_bytes, photo_error = extract_photo_from_request()

        if not name or not phone or not appointment_date or not cost or appt_dt is None:
            flash("error_appointment_missing_fields", "error")
        elif photo_error:
            flash(photo_error, "error")
        elif appt_dt < datetime.now(ISTANBUL_TZ).replace(tzinfo=None):
            flash("error_appointment_past", "error")
        elif day_fully_booked or slot_taken:
            flash("error_appointment_date_taken", "error")
        elif not is_admin() and not jeton_store.deduct(user_email, cost)[0]:
            flash("error_appointment_insufficient_funds", "error")
        else:
            lang = get_lang()
            category_name = REQUEST_CATEGORY_NAME.get(category, {}).get(lang, category)
            entry = {
                "name": name,
                "phone": phone,
                "email": contact_email,
                "motherName": mother_name,
                "birthDate": birth_date,
                "responseType": response_type,
                "appointmentDate": appointment_date,
                "note": note,
                "category": category,
                "categoryLabel": category_name,
                "categoryCost": cost,
                "hasPhoto": bool(photo_bytes),
                "lang": lang,
                "createdAt": datetime.utcnow().isoformat(),
            }
            appointments_store.add_appointment(entry)

            body = "\n".join([
                f"Nom : {name}",
                f"Telephone : {phone}",
                f"E-mail : {contact_email}",
                f"Prenom de la mere : {mother_name}",
                f"Date de naissance : {birth_date}",
                f"Type de reponse souhaite : {response_type}",
                f"Date souhaitee : {appointment_date}",
                f"Type de consultation : {category_name} ({cost} jetons)",
                f"Langue : {lang}",
                "",
                "Note :",
                note,
            ])
            subject = f"Nouvelle demande de rendez-vous - {name}"
            if photo_bytes:
                send_email_with_attachment_async(GMAIL_ADDRESS, subject, body, photo_bytes, photo.filename, photo.mimetype)
            else:
                send_email_async(GMAIL_ADDRESS, subject, body)
            flash("success_appointment_sent", "success")
            return redirect(url_for("appointment_page"))

    balance = "∞" if is_admin() else jeton_store.get_balance(user_email)
    return render_template(
        "appointment.html",
        balance=balance,
        categories=localized_request_categories(),
        preselected_category=request.args.get("category", ""),
        time_slots=APPOINTMENT_TIME_SLOTS,
    )


@app.route("/api/randevu/dolu-tarihler")
def api_busy_dates():
    appointments = appointments_store.list_appointments()
    times_by_day = _booked_times_by_day(appointments)
    blocked_days = set(appointments_store.list_blocked_dates())

    busy_dates = {day for day, times in times_by_day.items() if len(times) >= len(APPOINTMENT_TIME_SLOTS)}
    busy_dates.update(blocked_days)

    busy_slots = {day: sorted(times) for day, times in times_by_day.items() if day not in blocked_days}

    return jsonify({"ok": True, "busy_dates": sorted(busy_dates), "busy_slots": busy_slots})


@app.route("/api/cron/randevu-hatirlat")
def cron_appointment_reminder():
    if not CRON_SECRET or not hmac.compare_digest(request.args.get("secret", ""), CRON_SECRET):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    appointments = appointments_store.list_appointments()
    now = datetime.now(ISTANBUL_TZ).replace(tzinfo=None)
    reminded = 0

    for appt in appointments:
        if appt.get("reminded"):
            continue
        try:
            appt_dt = datetime.fromisoformat(appt["appointmentDate"])
        except (KeyError, ValueError):
            continue
        seconds_until = (appt_dt - now).total_seconds()
        if 0 <= seconds_until <= 900:
            wa_link = f"https://wa.me/{wa_number_filter(appt.get('phone'))}"
            body_lines = [
                "Randevu zamanı yaklaşıyor!",
                "",
                f"İsim: {appt.get('name', '')}",
                f"Telefon: {appt.get('phone', '')}",
                f"Tarih: {appt.get('appointmentDate', '')}",
                f"Not: {appt.get('note', '')}",
                "",
                f"WhatsApp'tan yaz: {wa_link}",
            ]
            send_email(GMAIL_ADDRESS, f"Randevu hatırlatma - {appt.get('name', '')}", "\n".join(body_lines))
            appointments_store.mark_reminded(appt["id"])
            reminded += 1

    return jsonify({"ok": True, "reminded": reminded})


@app.route("/api/admin/jeton-ekle", methods=["POST"])
def api_admin_add_jeton():
    if not ADMIN_API_SECRET or not hmac.compare_digest(request.args.get("secret", ""), ADMIN_API_SECRET):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    email = (request.form.get("email") or "").strip().lower()
    try:
        amount = int(request.form.get("amount", "0"))
    except ValueError:
        amount = 0
    if not email or amount <= 0 or not accounts_store.email_exists(email):
        return jsonify({"ok": False, "error": "invalid"}), 400
    balance = jeton_store.credit(email, amount)
    return jsonify({"ok": True, "balance": balance})


@app.route("/admin/randevular", methods=["GET", "POST"])
@limiter.limit("30 per hour", methods=["POST"])
def admin_appointments():
    if not is_admin():
        return redirect(url_for("login_page"))

    if request.method == "POST":
        action = request.form.get("action")
        if action == "block":
            date_str = (request.form.get("block_date") or "").strip()
            if date_str:
                appointments_store.add_blocked_date(date_str)
        elif action == "unblock":
            date_str = (request.form.get("date") or "").strip()
            appointments_store.remove_blocked_date(date_str)
        elif action == "grant_bonus":
            count = jeton_store.grant_bonus_to_all(500)
            flash(f"{count} hesaba +500 jeton eklendi.")
        elif action == "grant_user":
            target_email = (request.form.get("target_email") or "").strip().lower()
            try:
                amount = int(request.form.get("amount", "0"))
            except ValueError:
                amount = 0
            if not target_email or not accounts_store.email_exists(target_email):
                flash("Bu e-posta ile kayıtlı kullanıcı bulunamadı.", "error")
            elif amount <= 0:
                flash("Geçerli bir jeton miktarı gir.", "error")
            else:
                new_balance = jeton_store.credit(target_email, amount)
                flash(f"{target_email} hesabına {amount} jeton eklendi (yeni bakiye: {new_balance}).")
        return redirect(url_for("admin_appointments"))

    appointments = sorted(appointments_store.list_appointments(), key=lambda a: a.get("appointmentDate", ""))
    blocked_dates = appointments_store.list_blocked_dates()
    return render_template("admin_appointments.html", appointments=appointments, blocked_dates=blocked_dates)


@app.route("/admin/istatistikler")
def admin_stats():
    if not is_admin():
        return redirect(url_for("login_page"))

    appointments = appointments_store.list_appointments()
    reviews = reviews_store.list_reviews()

    category_counts = {}
    for appt in appointments:
        label = appt.get("categoryLabel") or appt.get("category") or "?"
        category_counts[label] = category_counts.get(label, 0) + 1
    top_categories = sorted(category_counts.items(), key=lambda kv: kv[1], reverse=True)[:8]

    signups_by_day = accounts_store.count_registrations_by_day(7)
    max_signups = max((c for _, c in signups_by_day), default=0) or 1

    stats = {
        "total_users": accounts_store.count_accounts(),
        "total_jetons": jeton_store.total_balance(),
        "total_payments": jeton_store.count_processed_payments(),
        "total_appointments": len(appointments),
        "jetons_spent_on_requests": sum(a.get("categoryCost", 0) or 0 for a in appointments),
        "total_reviews": len(reviews),
        "avg_rating": round(sum(r["rating"] for r in reviews) / len(reviews), 1) if reviews else None,
        "signups_by_day": signups_by_day,
        "max_signups": max_signups,
        "top_categories": top_categories,
    }
    return render_template("admin_stats.html", stats=stats)


REVIEWS_PER_PAGE = 9


def paginate(items, page_param="page", per_page=REVIEWS_PER_PAGE):
    try:
        page = int(request.args.get(page_param, 1))
    except ValueError:
        page = 1
    total_pages = max((len(items) + per_page - 1) // per_page, 1)
    page = min(max(page, 1), total_pages)
    start = (page - 1) * per_page
    return items[start:start + per_page], page, total_pages


@app.route("/yorumlar", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def reviews_page():
    if request.method == "POST":
        email = session.get("email")
        if not email:
            return redirect(url_for("login_page"))
        action = request.form.get("action", "add")

        if action == "add":
            name = session.get("nickname") or email.split("@")[0]
            text = (request.form.get("text") or "").strip()
            try:
                rating = int(request.form.get("rating", 0))
            except ValueError:
                rating = 0
            if text and 1 <= rating <= 5:
                reviews_store.add_review(name, rating, text, email=email)
                flash("success_review_sent", "success")
        elif action in ("edit_own", "delete_own"):
            try:
                review_id = int(request.form.get("review_id", ""))
            except ValueError:
                review_id = None
            review = reviews_store.get_review(review_id) if review_id else None
            if review and review.get("email") == email:
                if action == "delete_own":
                    reviews_store.delete_review(review_id)
                    flash("success_review_deleted", "success")
                else:
                    text = (request.form.get("text") or "").strip()
                    try:
                        rating = int(request.form.get("rating", 0))
                    except ValueError:
                        rating = 0
                    if text and 1 <= rating <= 5:
                        reviews_store.update_review(review_id, review["name"], rating, text)
                        flash("success_review_updated", "success")
            else:
                flash("error_review_not_found", "error")
        return redirect(url_for("reviews_page"))

    reviews = reviews_store.list_reviews()
    avg_rating = round(sum(r["rating"] for r in reviews) / len(reviews), 1) if reviews else None
    page_reviews, page, total_pages = paginate(reviews)
    return render_template(
        "reviews.html",
        reviews=page_reviews,
        all_reviews=reviews,
        avg_rating=avg_rating,
        total_reviews=len(reviews),
        page=page,
        total_pages=total_pages,
        current_email=session.get("email"),
    )


@app.route("/burclar")
def zodiac_hub():
    return render_template("zodiac_hub.html")


@app.route("/burc-yorumu")
def horoscope_page():
    lang = get_lang()
    signs = horoscope.daily_horoscopes(lang)
    return render_template("horoscope.html", signs=signs, today=datetime.now().strftime("%d/%m/%Y"))


@app.route("/burc-karakteri")
def zodiac_character_page():
    lang = get_lang()
    profiles = horoscope.zodiac_profiles(lang)
    return render_template("zodiac_character.html", profiles=profiles)


@app.route("/yukselen-burc", methods=["GET", "POST"])
@limiter.limit("20 per hour", methods=["POST"])
def ascendant_page():
    lang = get_lang()
    result = None
    error = False
    form_values = {"birth_date": "", "birth_time": "", "city": ""}
    if request.method == "POST":
        form_values["birth_date"] = request.form.get("birth_date", "")
        form_values["birth_time"] = request.form.get("birth_time", "")
        form_values["city"] = request.form.get("city", "")
        city = ascendant.find_city(form_values["city"])
        try:
            if not city:
                raise ValueError("invalid city")
            birth_date = datetime.strptime(form_values["birth_date"], "%Y-%m-%d").date()
            birth_time = datetime.strptime(form_values["birth_time"], "%H:%M").time()
            index, _ = ascendant.ascendant_sign_index(birth_date, birth_time, city)
            sign = horoscope.ZODIAC_SIGNS[index]
            result = {
                "symbol": sign["symbol"],
                "name": sign["name"][lang],
                "meaning": horoscope.ascendant_meaning(sign["id"], lang),
            }
        except (ValueError, KeyError):
            error = True
    cities = [{"id": c["id"], "name": c["name"][lang]} for c in ascendant.CITIES]
    return render_template(
        "ascendant.html", cities=cities, result=result, error=error, form_values=form_values
    )


@app.route("/admin/yorumlar", methods=["GET", "POST"])
@limiter.limit("30 per hour", methods=["POST"])
def admin_reviews():
    if not is_admin():
        return redirect(url_for("login_page"))

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            name = (request.form.get("name") or "").strip()
            text = (request.form.get("text") or "").strip()
            try:
                rating = int(request.form.get("rating", 0))
            except ValueError:
                rating = 0
            if name and text and 1 <= rating <= 5:
                reviews_store.add_review(name, rating, text)
                flash("Yorum eklendi.")
            else:
                flash("İsim, puan ve yorum metni gerekli.", "error")
        elif action == "delete":
            try:
                reviews_store.delete_review(int(request.form.get("review_id", "")))
                flash("Yorum silindi.")
            except ValueError:
                pass
        elif action == "edit":
            name = (request.form.get("name") or "").strip()
            text = (request.form.get("text") or "").strip()
            try:
                rating = int(request.form.get("rating", 0))
                review_id = int(request.form.get("review_id", ""))
            except ValueError:
                rating = 0
                review_id = None
            if review_id and name and text and 1 <= rating <= 5:
                reviews_store.update_review(review_id, name, rating, text)
                flash("Yorum güncellendi.")
            else:
                flash("Güncelleme başarısız: isim, puan ve metin gerekli.", "error")
        return redirect(url_for("admin_reviews", page=request.args.get("page", 1)))

    all_reviews = reviews_store.list_reviews()
    page_reviews, page, total_pages = paginate(all_reviews)
    return render_template(
        "admin_reviews.html",
        reviews=page_reviews,
        total_reviews=len(all_reviews),
        page=page,
        total_pages=total_pages,
    )


@app.route("/api/jeton/checkout", methods=["POST"])
@limiter.limit("20 per hour")
def api_jeton_checkout():
    email = session.get("email")
    if not email:
        return jsonify({"ok": False, "error": "login_required"}), 401

    data = request.get_json(silent=True) or {}
    amount = data.get("amount")

    pack = JETON_PACKS_BY_AMOUNT.get(amount)
    if not pack:
        return jsonify({"ok": False, "error": "unknown_pack"}), 404

    if not stripe.api_key:
        return jsonify({"ok": False, "error": "stripe_not_configured"}), 503

    base_url = request.url_root.rstrip("/")
    checkout_session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": pack["stripe_price_id"], "quantity": 1}],
        client_reference_id=email,
        metadata={"username": email, "jeton_amount": str(pack["amount"])},
        success_url=f"{base_url}/tirage?checkout=success",
        cancel_url=f"{base_url}/tirage?checkout=cancel",
    )
    return jsonify({"ok": True, "url": checkout_session.url})


@app.route("/api/paypal/create-order", methods=["POST"])
@limiter.limit("20 per hour")
def api_paypal_create_order():
    email = session.get("email")
    if not email:
        return jsonify({"ok": False, "error": "login_required"}), 401

    if not (PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET):
        return jsonify({"ok": False, "error": "paypal_not_configured"}), 503

    data = request.get_json(silent=True) or {}
    amount = data.get("amount")
    pack = JETON_PACKS_BY_AMOUNT.get(amount)
    if not pack:
        return jsonify({"ok": False, "error": "unknown_pack"}), 404

    try:
        token = get_paypal_access_token()
        resp = requests.post(
            f"{PAYPAL_API_BASE}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {"currency_code": "GBP", "value": f"{pack['price_value']:.2f}"},
                    "custom_id": f"{email}:{pack['amount']}",
                }],
            },
            timeout=10,
        )
        resp.raise_for_status()
        order = resp.json()
    except requests.RequestException:
        return jsonify({"ok": False, "error": "paypal_error"}), 502

    return jsonify({"ok": True, "order_id": order["id"]})


@app.route("/api/paypal/capture-order", methods=["POST"])
@limiter.limit("20 per hour")
def api_paypal_capture_order():
    email = session.get("email")
    if not email:
        return jsonify({"ok": False, "error": "login_required"}), 401

    data = request.get_json(silent=True) or {}
    order_id = (data.get("order_id") or "").strip()
    if not order_id:
        return jsonify({"ok": False, "error": "missing_order_id"}), 400

    try:
        token = get_paypal_access_token()
        resp = requests.post(
            f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        capture = resp.json()
    except requests.RequestException:
        return jsonify({"ok": False, "error": "paypal_error"}), 502

    if capture.get("status") != "COMPLETED":
        return jsonify({"ok": False, "error": "not_completed"}), 400

    try:
        custom_id = capture["purchase_units"][0]["payments"]["captures"][0].get("custom_id", "")
        paid_email, _, amount_str = custom_id.partition(":")
        amount = int(amount_str)
    except (KeyError, IndexError, ValueError):
        return jsonify({"ok": False, "error": "bad_capture"}), 400

    if paid_email != email or amount not in JETON_PACKS_BY_AMOUNT:
        return jsonify({"ok": False, "error": "mismatch"}), 400

    if not jeton_store.mark_payment_processed(f"paypal:{order_id}"):
        return jsonify({"ok": True, "balance": jeton_store.get_balance(email)})

    balance = jeton_store.credit(email, amount)
    return jsonify({"ok": True, "balance": balance})


@app.route("/api/stripe/webhook", methods=["POST"])
def api_stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return jsonify({"ok": False, "error": "invalid_signature"}), 400

    if event["type"] == "checkout.session.completed":
        checkout_session = event["data"]["object"]
        username = (checkout_session.get("client_reference_id") or checkout_session.get("metadata", {}).get("username") or "").strip()
        jeton_amount = checkout_session.get("metadata", {}).get("jeton_amount")
        if username and jeton_amount and jeton_store.mark_payment_processed(f"stripe:{checkout_session['id']}"):
            jeton_store.credit(username, int(jeton_amount))

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
