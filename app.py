#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import random
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

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
    },
}

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


@app.route("/tirage")
def reading_page():
    return render_template("reading.html", spreads=SPREADS)


@app.route("/api/tirage/<spread_key>", methods=["POST"])
def api_reading(spread_key):
    if spread_key not in SPREADS:
        return jsonify({"ok": False, "error": "unknown spread"}), 404
    lang = get_lang()
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    result = draw_spread(spread_key, lang)
    result["ok"] = True
    result["question"] = question
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
