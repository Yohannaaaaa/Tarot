#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import random
from datetime import datetime
from pathlib import Path

import stripe
from flask import Flask, jsonify, redirect, render_template, request, url_for

import jeton_store

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

app = Flask(__name__)

DATA_PATH = Path(__file__).resolve().parent / "data" / "cards.json"
with open(DATA_PATH, encoding="utf-8") as f:
    CARDS = json.load(f)

CARDS_BY_ID = {c["id"]: c for c in CARDS}

LANGS = ("fr", "tr")
DEFAULT_LANG = "fr"

UI = {
    "fr": {
        "site_title": "Rituams Tarot",
        "nav_home": "Accueil",
        "nav_cards": "Les Cartes",
        "nav_reading": "Tirage",
        "home_title": "Rituams Tarot",
        "home_subtitle": "Un tirage gratuit, un langage des cartes en français et en turc",
        "home_lead": "Découvrez la sagesse du tarot à travers les 78 cartes du Rider-Waite. Explorez la bibliothèque des arcanes ou laissez les cartes répondre à votre question.",
        "cta_reading": "Faire un tirage",
        "cta_cards": "Explorer les cartes",
        "feature_1_title": "78 cartes détaillées",
        "feature_1_text": "Arcanes majeurs et mineurs, avec leur sens à l'endroit et à l'envers.",
        "feature_2_title": "Tirages variés",
        "feature_2_text": "3 cartes, 7 cartes, oui/non, amour, carrière ou tirage général.",
        "feature_3_title": "Français & Türkçe",
        "feature_3_text": "Toute l'interface et les interprétations sont disponibles dans les deux langues.",
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
        "instant_free": "Gratuit",
        "instant_button": "🃏 Tirer une carte",
        "spread_section_title": "🎴 Choisis un tirage",
        "packs_note": "Paiement sécurisé par Stripe.",
        "buy_pack": "Acheter",
        "buy_pack_error": "Erreur lors de la création du paiement, réessaie.",
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
        "username_label": "Ton pseudo (pour tes jetons)",
        "username_placeholder": "Choisis un pseudo...",
        "jeton_balance": "Solde",
        "jeton_unit": "jetons",
        "jeton_bonus_button": "🎁 Bonus quotidien",
        "jeton_bonus_claimed": "Bonus déjà réclamé aujourd'hui",
        "jeton_bonus_success": "Bonus reçu !",
        "jeton_insufficient": "Jetons insuffisants",
        "jeton_cost_label": "jetons",
        "username_required": "Choisis d'abord un pseudo pour utiliser tes jetons.",
    },
    "tr": {
        "site_title": "Rituams Tarot",
        "nav_home": "Ana Sayfa",
        "nav_cards": "Kartlar",
        "nav_reading": "Açılım",
        "home_title": "Rituams Tarot",
        "home_subtitle": "Ücretsiz açılım, Fransızca ve Türkçe kart yorumları",
        "home_lead": "Rider-Waite tarot destesinin 78 kartıyla tarotun bilgeliğini keşfedin. Kart kütüphanesine göz atın ya da kartların sorunuza cevap vermesine izin verin.",
        "cta_reading": "Açılım yap",
        "cta_cards": "Kartları keşfet",
        "feature_1_title": "78 detaylı kart",
        "feature_1_text": "Majör ve minör arkanalar, düz ve ters anlamlarıyla birlikte.",
        "feature_2_title": "Farklı açılımlar",
        "feature_2_text": "3 kart, 7 kart, evet/hayır, aşk, kariyer veya genel açılım.",
        "feature_3_title": "Türkçe & Français",
        "feature_3_text": "Tüm arayüz ve yorumlar iki dilde de mevcuttur.",
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
        "instant_free": "Ücretsiz",
        "instant_button": "🃏 Kart Çek",
        "spread_section_title": "🎴 Açılım Seç",
        "packs_note": "Ödemeler Stripe ile güvenli şekilde yapılır.",
        "buy_pack": "Satın Al",
        "buy_pack_error": "Ödeme oluşturulurken hata oluştu, tekrar dene.",
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
        "username_label": "Rumuzun (jetonların için)",
        "username_placeholder": "Bir rumuz seç...",
        "jeton_balance": "Bakiye",
        "jeton_unit": "jeton",
        "jeton_bonus_button": "🎁 Günlük bonus",
        "jeton_bonus_claimed": "Bugünkü bonus zaten alındı",
        "jeton_bonus_success": "Bonus alındı!",
        "jeton_insufficient": "Yetersiz jeton",
        "jeton_cost_label": "jeton",
        "username_required": "Jetonlarını kullanmak için önce bir rumuz seç.",
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
    {"amount": 200, "price": "£4.99", "stripe_price_id": "price_1U9od2LYpYxtFvCYCu69apgZ"},
    {"amount": 500, "price": "£9.99", "stripe_price_id": "price_1U9odELYpYxtFvCYeOxxxDac"},
    {"amount": 1200, "price": "£19.99", "stripe_price_id": "price_1U9odGLYpYxtFvCYK1tnGZup"},
    {"amount": 3000, "price": "£39.99", "stripe_price_id": "price_1U9odJLYpYxtFvCY1Qlbgtoo"},
    {"amount": 8000, "price": "£89.99", "stripe_price_id": "price_1U9odLLYpYxtFvCY4YjrF4VE"},
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
    return {"lang": lang, "other_lang": "tr" if lang == "fr" else "fr", "t": ui(lang)}


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


MAJOR_CARDS = [c for c in CARDS if c["arcana"] == "major"]
MESSAGES_PATH = Path(__file__).resolve().parent / "data" / "messages.json"


@app.route("/tirage")
def reading_page():
    lang = get_lang()
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
        daily_bonus=jeton_store.DAILY_BONUS,
    )


@app.route("/api/tirage/<spread_key>", methods=["POST"])
def api_reading(spread_key):
    if spread_key not in SPREADS:
        return jsonify({"ok": False, "error": "unknown spread"}), 404
    lang = get_lang()
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    username = (data.get("username") or "").strip()

    if not username:
        return jsonify({"ok": False, "error": "username_required"}), 400

    ok, balance = jeton_store.deduct(username, jeton_store.SPREAD_COST)
    if not ok:
        return jsonify({"ok": False, "error": "insufficient_funds", "balance": balance, "cost": jeton_store.SPREAD_COST}), 402

    result = draw_spread(spread_key, lang)
    result["ok"] = True
    result["question"] = question
    result["remaining_jeton"] = balance
    return jsonify(result)


@app.route("/api/anlik")
def api_instant_card():
    lang = get_lang()
    card = random.choice(MAJOR_CARDS)
    return jsonify({"ok": True, "card": card_side(card, "upright", lang)})


@app.route("/api/jeton")
def api_jeton_balance():
    username = (request.args.get("username") or "").strip()
    if not username:
        return jsonify({"ok": False, "error": "username_required"}), 400
    return jsonify({
        "ok": True,
        "balance": jeton_store.get_balance(username),
        "bonus_available": jeton_store.bonus_available(username),
    })


@app.route("/api/jeton/bonus", methods=["POST"])
def api_jeton_bonus():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    if not username:
        return jsonify({"ok": False, "error": "username_required"}), 400
    ok, balance = jeton_store.claim_bonus(username)
    if not ok:
        return jsonify({"ok": False, "error": "already_claimed", "balance": balance}), 400
    return jsonify({"ok": True, "balance": balance})


@app.route("/api/mesaj", methods=["POST"])
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

    return jsonify({"ok": True})


@app.route("/api/jeton/checkout", methods=["POST"])
def api_jeton_checkout():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    amount = data.get("amount")

    if not username:
        return jsonify({"ok": False, "error": "username_required"}), 400

    pack = JETON_PACKS_BY_AMOUNT.get(amount)
    if not pack:
        return jsonify({"ok": False, "error": "unknown_pack"}), 404

    if not stripe.api_key:
        return jsonify({"ok": False, "error": "stripe_not_configured"}), 503

    base_url = request.url_root.rstrip("/")
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": pack["stripe_price_id"], "quantity": 1}],
        client_reference_id=username,
        metadata={"username": username, "jeton_amount": str(pack["amount"])},
        success_url=f"{base_url}/tirage?checkout=success",
        cancel_url=f"{base_url}/tirage?checkout=cancel",
    )
    return jsonify({"ok": True, "url": session.url})


@app.route("/api/stripe/webhook", methods=["POST"])
def api_stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return jsonify({"ok": False, "error": "invalid_signature"}), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        username = (session.get("client_reference_id") or session.get("metadata", {}).get("username") or "").strip()
        jeton_amount = session.get("metadata", {}).get("jeton_amount")
        if username and jeton_amount:
            jeton_store.credit(username, int(jeton_amount))

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
