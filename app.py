#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import random
import re
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urlencode

import requests
import stripe
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

import accounts_store
import db
import jeton_store

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
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.environ.get("ADMIN_EMAILS", GMAIL_ADDRESS).split(",")
    if e.strip()
}


def is_admin():
    email = session.get("email")
    return bool(email and email.lower() in ADMIN_EMAILS)


WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "")

CRON_SECRET = os.environ.get("CRON_SECRET", "")
ISTANBUL_TZ = timezone(timedelta(hours=3))

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "rituams-tarot-dev-secret-change-me")
app.config["SESSION_COOKIE_SECURE"] = bool(os.environ.get("RENDER"))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
db.init_schema()

limiter = Limiter(get_remote_address, app=app, default_limits=[])


@app.errorhandler(429)
def ratelimit_handler(e):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "rate_limited"}), 429
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


def send_email(to_addr, subject, body):
    if not GMAIL_APP_PASSWORD:
        return False
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_addr
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, [to_addr], msg.as_string())
        return True
    except (smtplib.SMTPException, OSError):
        return False


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
        "home_title": "Rituams Tarot",
        "cta_reading": "Faire un tirage",
        "cta_cards": "Explorer les cartes",
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
        "tab_services": "🔮 Consultations Tarot",
        "tab_rituals": "✨ Rituels",
        "tab_instant": "🤖 Tirage Instantané",
        "tab_packs": "🪙 Packs de Jetons",
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
        "form_title": "✍️ Écris ta question",
        "field_name": "Prénom",
        "field_mother": "Prénom de la mère",
        "field_birthdate": "Date de naissance",
        "field_email": "E-mail",
        "field_response_type": "Comment veux-tu la réponse ?",
        "opt_mail": "Par e-mail",
        "opt_voice": "Rendez-vous vocal",
        "opt_pdf": "Réponse en PDF",
        "field_appointment_date": "Date de rendez-vous souhaitée",
        "field_question": "Écris ta question",
        "form_submit": "Envoyer la demande",
        "form_sending": "Envoi en cours...",
        "form_success": "Merci, ta demande a bien été enregistrée !",
        "form_error": "Erreur lors de l'envoi, réessaie.",
        "form_need_name_email": "Renseigne au moins ton prénom, ton e-mail et ta question.",
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
        "not_found_message": "Cette page n'existe pas ou a été déplacée.",
        "back_to_home": "← Retour à l'accueil",
        "nav_appointment": "Rendez-vous",
        "appointment_title": "Prendre rendez-vous",
        "appointment_subtitle": "Réserve un créneau pour une consultation, on te recontacte pour confirmer.",
        "field_phone": "Numéro de téléphone",
        "field_appointment_datetime": "Date et heure souhaitées",
        "field_note": "Ta note (optionnel)",
        "field_appointment_time": "Heure",
        "appointment_submit": "Envoyer la demande de rendez-vous",
        "error_appointment_missing_fields": "Renseigne au moins ton prénom, ton téléphone et la date souhaitée.",
        "success_appointment_sent": "Ta demande de rendez-vous a été reçue, nous te contacterons bientôt !",
        "appointment_select_date_prompt": "Choisis d'abord une date et une heure dans le calendrier.",
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
        "home_title": "Rituams Tarot",
        "cta_reading": "Açılım yap",
        "cta_cards": "Kartları keşfet",
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
        "tab_services": "🔮 Tarot Bakımları",
        "tab_rituals": "✨ Ritüeller",
        "tab_instant": "🤖 Anında Açılım",
        "tab_packs": "🪙 Jeton Paketleri",
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
        "form_title": "✍️ Sorunu Yaz",
        "field_name": "İsim",
        "field_mother": "Anne adı",
        "field_birthdate": "Doğum tarihi",
        "field_email": "E-posta",
        "field_response_type": "Cevabı nasıl istersin?",
        "opt_mail": "Mail ile",
        "opt_voice": "Sesli randevu",
        "opt_pdf": "PDF cevap",
        "field_appointment_date": "İstenen randevu tarihi",
        "field_question": "Sorunu yaz",
        "form_submit": "Talebi Gönder",
        "form_sending": "Gönderiliyor...",
        "form_success": "Teşekkürler, talebin kaydedildi!",
        "form_error": "Gönderim hatası, tekrar dene.",
        "form_need_name_email": "En azından isim, e-posta ve sorunu doldur.",
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
        "not_found_message": "Bu sayfa mevcut değil ya da taşınmış.",
        "back_to_home": "← Ana sayfaya dön",
        "nav_appointment": "Randevu Al",
        "appointment_title": "Randevu Al",
        "appointment_subtitle": "Bir bakım için randevu talebinde bulun, seninle iletişime geçip onaylayalım.",
        "field_phone": "Telefon Numarası",
        "field_appointment_datetime": "İstenen tarih ve saat",
        "field_note": "Notun (opsiyonel)",
        "field_appointment_time": "Saat",
        "appointment_submit": "Randevu Talebi Gönder",
        "error_appointment_missing_fields": "En azından isim, telefon numarası ve istenen tarihi doldur.",
        "success_appointment_sent": "Randevu talebin alındı, en kısa sürede seninle iletişime geçeceğiz!",
        "appointment_select_date_prompt": "Önce takvimden bir tarih ve saat seç.",
        "calendar_legend_free": "Müsait",
        "calendar_legend_busy": "Dolu",
        "calendar_weekdays": ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"],
    },
}

SERVICES = [
    {"id": "single", "duration": {"fr": "5 min", "tr": "5 dk"}, "cost": 300,
     "name": {"fr": "Consultation à question unique", "tr": "Tek Soru Bakımı"}},
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
    {"id": "confidence", "emoji": "💖", "cost": 800,
     "name": {"fr": "Confiance en soi et Attraction", "tr": "Öz Güven ve Çekim Gücü"}},
    {"id": "luck", "emoji": "🍀", "cost": 800,
     "name": {"fr": "Chance et Abondance", "tr": "Şans ve Bolluk"}},
    {"id": "career", "emoji": "💼", "cost": 800,
     "name": {"fr": "Carrière et Réussite", "tr": "Kariyer ve Başarı"}},
    {"id": "cleanse", "emoji": "🕊️", "cost": 800,
     "name": {"fr": "Purification des Énergies Négatives", "tr": "Negatif Enerjiden Arınma"}},
    {"id": "intention", "emoji": "🌙", "cost": 1500,
     "name": {"fr": "Rituel d'Intention Personnelle", "tr": "Kişisel Niyet Ritüeli"}},
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
    return {
        "lang": lang,
        "other_lang": "tr" if lang == "fr" else "fr",
        "t": ui(lang),
        "logged_in": bool(session.get("email")),
        "current_nickname": session.get("nickname"),
        "whatsapp_link": f"https://wa.me/{WHATSAPP_NUMBER}" if WHATSAPP_NUMBER else None,
        "is_admin": is_admin(),
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
    if not email:
        flash("error_google_not_configured", "error")
        return redirect(url_for("login_page"))

    name = userinfo.get("name") or email.split("@")[0]
    account = accounts_store.upsert_google_account(email, userinfo.get("sub"), name)
    session["email"] = account["email"]
    session["nickname"] = account["nickname"]
    return redirect(url_for("reading_page"))


MAJOR_CARDS = [c for c in CARDS if c["arcana"] == "major"]
MESSAGES_PATH = Path(__file__).resolve().parent / "data" / "messages.json"
APPOINTMENTS_PATH = Path(__file__).resolve().parent / "data" / "appointments.json"
BLOCKED_DATES_PATH = Path(__file__).resolve().parent / "data" / "blocked_dates.json"


def load_appointments():
    try:
        with open(APPOINTMENTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_blocked_dates():
    try:
        with open(BLOCKED_DATES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_blocked_dates(dates):
    BLOCKED_DATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BLOCKED_DATES_PATH, "w", encoding="utf-8") as f:
        json.dump(dates, f, ensure_ascii=False, indent=2)


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


@app.route("/api/mesaj", methods=["POST"])
@limiter.limit("5 per hour")
def api_message():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    question = (data.get("question") or "").strip()
    if not name or not email or not question:
        return jsonify({"ok": False, "error": "missing_fields"}), 400

    entry = {
        "name": name,
        "motherName": (data.get("motherName") or "").strip(),
        "birthDate": (data.get("birthDate") or "").strip(),
        "email": email,
        "responseType": (data.get("responseType") or "mail").strip(),
        "appointmentDate": (data.get("appointmentDate") or "").strip(),
        "question": question,
        "category": (data.get("category") or "").strip(),
        "service": (data.get("service") or "").strip(),
        "cost": data.get("cost"),
        "lang": get_lang(),
        "createdAt": datetime.utcnow().isoformat(),
    }

    MESSAGES_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(MESSAGES_PATH, encoding="utf-8") as f:
            messages = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        messages = []
    messages.append(entry)
    with open(MESSAGES_PATH, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

    send_email(
        GMAIL_ADDRESS,
        f"Nouvelle demande Rituams Tarot - {entry['name']}",
        "\n".join([
            f"Nom : {entry['name']}",
            f"E-mail : {entry['email']}",
            f"Prenom de la mere : {entry['motherName']}",
            f"Date de naissance : {entry['birthDate']}",
            f"Type de reponse souhaite : {entry['responseType']}",
            f"Date de rendez-vous souhaitee : {entry['appointmentDate']}",
            f"Categorie : {entry['category']}",
            f"Service/rituel : {entry['service']}",
            f"Cout : {entry['cost']}",
            f"Langue : {entry['lang']}",
            "",
            "Question :",
            entry["question"],
        ]),
    )

    return jsonify({"ok": True})


@app.route("/randevu-al", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def appointment_page():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        email = (request.form.get("email") or "").strip()
        appointment_date = (request.form.get("appointment_date") or "").strip()
        note = (request.form.get("note") or "").strip()

        if not name or not phone or not appointment_date:
            flash("error_appointment_missing_fields", "error")
        else:
            entry = {
                "name": name,
                "phone": phone,
                "email": email,
                "appointmentDate": appointment_date,
                "note": note,
                "lang": get_lang(),
                "createdAt": datetime.utcnow().isoformat(),
            }
            appointments = load_appointments()
            appointments.append(entry)
            save_appointments(appointments)

            send_email(
                GMAIL_ADDRESS,
                f"Nouvelle demande de rendez-vous - {name}",
                "\n".join([
                    f"Nom : {name}",
                    f"Telephone : {phone}",
                    f"E-mail : {email}",
                    f"Date souhaitee : {appointment_date}",
                    f"Langue : {entry['lang']}",
                    "",
                    "Note :",
                    note,
                ]),
            )
            flash("success_appointment_sent", "success")
            return redirect(url_for("appointment_page"))
    return render_template("appointment.html")


@app.route("/api/randevu/dolu-tarihler")
def api_busy_dates():
    appointments = load_appointments()
    busy_dates = {
        a["appointmentDate"].split("T")[0]
        for a in appointments
        if a.get("appointmentDate")
    }
    busy_dates.update(load_blocked_dates())
    return jsonify({"ok": True, "busy_dates": sorted(busy_dates)})


def save_appointments(appointments):
    APPOINTMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(APPOINTMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(appointments, f, ensure_ascii=False, indent=2)


@app.route("/api/cron/randevu-hatirlat")
def cron_appointment_reminder():
    if not CRON_SECRET or request.args.get("secret") != CRON_SECRET:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    appointments = load_appointments()
    now = datetime.now(ISTANBUL_TZ).replace(tzinfo=None)
    reminded = 0
    changed = False

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
            appt["reminded"] = True
            changed = True
            reminded += 1

    if changed:
        save_appointments(appointments)

    return jsonify({"ok": True, "reminded": reminded})


@app.route("/admin/randevular", methods=["GET", "POST"])
@limiter.limit("30 per hour", methods=["POST"])
def admin_appointments():
    if not is_admin():
        return redirect(url_for("login_page"))

    if request.method == "POST":
        action = request.form.get("action")
        blocked = load_blocked_dates()
        if action == "block":
            date_str = (request.form.get("block_date") or "").strip()
            if date_str and date_str not in blocked:
                blocked.append(date_str)
                save_blocked_dates(sorted(blocked))
        elif action == "unblock":
            date_str = (request.form.get("date") or "").strip()
            if date_str in blocked:
                blocked.remove(date_str)
                save_blocked_dates(blocked)
        return redirect(url_for("admin_appointments"))

    appointments = sorted(load_appointments(), key=lambda a: a.get("appointmentDate", ""))
    blocked_dates = load_blocked_dates()
    return render_template("admin_appointments.html", appointments=appointments, blocked_dates=blocked_dates)


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
        if username and jeton_amount:
            jeton_store.credit(username, int(jeton_amount))

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
