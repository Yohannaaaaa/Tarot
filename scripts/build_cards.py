#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Construit data/cards.json (78 cartes, bilingue FR/TR) a partir de :
- data/source_tr_base.json   : base turque d'origine (arcanes majeurs + mineurs)
- data/source_fr_majors.py   : traductions francaises des 22 arcanes majeurs
- generation ci-dessous       : contenu des 56 arcanes mineurs (FR + TR)
"""
import json
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# ---------------------------------------------------------------------------
# Chargement des sources
# ---------------------------------------------------------------------------

with open(DATA / "source_tr_base.json", encoding="utf-8") as f:
    TR_BASE = json.load(f)

spec = importlib.util.spec_from_file_location("source_fr_majors", DATA / "source_fr_majors.py")
_fr_majors_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_fr_majors_mod)
FR_MAJORS = _fr_majors_mod.CARD_CONTENT_TRANSLATIONS_FR

MAJOR_NAME_FR = {
    'JOKER (Deli)': 'Le Fou',
    'BÜYÜCÜ': 'Le Magicien',
    'AZİZE': 'La Prêtresse',
    'İMPARATORİÇE': "L'Impératrice",
    'İMPARATOR': "L'Empereur",
    'AZİZ': 'Le Pape',
    'AŞIKLAR': 'Les Amoureux',
    'SAVAŞ ARABASI': 'Le Chariot',
    'GÜÇ': 'La Force',
    'ERMİŞ': "L'Ermite",
    'KADER ÇARKI': 'La Roue de Fortune',
    'ADALET': 'La Justice',
    'ASILAN ADAM': 'Le Pendu',
    'ÖLÜM': 'La Mort',
    'DENGE': 'Tempérance',
    'ŞEYTAN': 'Le Diable',
    'KULE': 'La Tour',
    'YILDIZ': "L'Étoile",
    'AY': 'La Lune',
    'GÜNEŞ': 'Le Soleil',
    'MAHKEME (Yargı)': 'Le Jugement',
    'DÜNYA': 'Le Monde',
}

LIFE_AREA_KEYS_TR = {
    'i̇lişki': 'love', 'ilişki': 'love',
    'kariyer': 'career',
    'para': 'money',
    'sağlık': 'health',
    'aile': 'family',
}
LIFE_AREA_KEYS_FR = {
    'Relation': 'love',
    'Carrière': 'career',
    'Finances': 'money',
    'Santé': 'health',
    'Famille': 'family',
}


def normalize_life_areas(raw, key_map):
    out = {}
    for k, v in (raw or {}).items():
        out[key_map.get(k, k)] = v
    return out


def field_block(intro, love, career, money, health, family, symbols, questions, weekly, hidden):
    return {
        'intro': intro, 'love': love, 'career': career, 'money': money,
        'health': health, 'family': family, 'symbols': symbols,
        'questions': questions, 'weekly': weekly, 'hidden': hidden,
    }


def from_positions_tr(pos):
    la = normalize_life_areas(pos.get('life_areas'), LIFE_AREA_KEYS_TR)
    return field_block(
        pos.get('intro', ''), la.get('love', ''), la.get('career', ''),
        la.get('money', ''), la.get('health', ''), la.get('family', ''),
        pos.get('symbols', ''), pos.get('questions', ''),
        pos.get('weekly', ''), pos.get('hidden', ''),
    )


def from_positions_fr(pos):
    la = normalize_life_areas(pos.get('life_areas'), LIFE_AREA_KEYS_FR)
    return field_block(
        pos.get('intro', ''), la.get('love', ''), la.get('career', ''),
        la.get('money', ''), la.get('health', ''), la.get('family', ''),
        pos.get('symbols', ''), pos.get('questions', ''),
        pos.get('weekly', ''), pos.get('hidden', ''),
    )


# ---------------------------------------------------------------------------
# Arcanes majeurs
# ---------------------------------------------------------------------------

KNOWN_MAJOR_IMAGE_FIXES = {
    'MAHKEME (Yargı)': '20_yargi.webp',
}


def roman_to_int(s):
    if s == '0':
        return 0
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
    total = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        if i + 1 < len(s) and vals[s[i + 1]] > v:
            total -= v
        else:
            total += v
    return total


def build_majors():
    cards = []
    for c in TR_BASE:
        if c.get('type') != 'major':
            continue
        name_tr = c['name']
        number = roman_to_int(c['number'])
        fr_positions = FR_MAJORS.get(name_tr, {})
        image = c.get('image') or KNOWN_MAJOR_IMAGE_FIXES.get(name_tr)
        cards.append({
            'id': image.replace('.webp', '') if image else f"major_{number}",
            'number': number,
            'arcana': 'major',
            'suit': None,
            'rank': None,
            'image': image,
            'name': {'tr': name_tr, 'fr': MAJOR_NAME_FR.get(name_tr, name_tr)},
            'upright': {
                'tr': from_positions_tr(c['positions'].get('Düz', {})),
                'fr': from_positions_fr(fr_positions.get('Düz', {})),
            },
            'reversed': {
                'tr': from_positions_tr(c['positions'].get('Ters', {})),
                'fr': from_positions_fr(fr_positions.get('Ters', {})),
            },
        })
    cards.sort(key=lambda c: c['number'])
    return cards


# ---------------------------------------------------------------------------
# Arcanes mineurs : generation du contenu FR + TR
# ---------------------------------------------------------------------------

SUITS = [
    {
        'tr': 'Kase', 'fr': 'Coupes', 'key': 'cups', 'emoji': '💧',
        'domain_tr': 'duygular, aşk ve ilişkiler', 'domain_fr': "les émotions, l'amour et les relations",
        'element_tr': 'Su', 'element_fr': 'Eau',
    },
    {
        'tr': 'Değnekler', 'fr': 'Bâtons', 'key': 'wands', 'emoji': '🔥',
        'domain_tr': 'eylem, tutku ve yaratıcılık', 'domain_fr': "l'action, la passion et la créativité",
        'element_tr': 'Ateş', 'element_fr': 'Feu',
    },
    {
        'tr': 'Kılıçlar', 'fr': 'Épées', 'key': 'swords', 'emoji': '⚔️',
        'domain_tr': 'düşünce, çatışma ve iletişim', 'domain_fr': 'la pensée, le conflit et la communication',
        'element_tr': 'Hava', 'element_fr': 'Air',
    },
    {
        'tr': 'Paralar', 'fr': 'Deniers', 'key': 'pentacles', 'emoji': '🪙',
        'domain_tr': 'maddi konular, iş ve beden', 'domain_fr': 'le matériel, le travail et le corps',
        'element_tr': 'Toprak', 'element_fr': 'Terre',
    },
]

RANKS = [
    ('As', 'As', 'ace'),
    ('2', '2', '2'), ('3', '3', '3'), ('4', '4', '4'), ('5', '5', '5'),
    ('6', '6', '6'), ('7', '7', '7'), ('8', '8', '8'), ('9', '9', '9'), ('10', '10', '10'),
    ('Vale', 'Valet', 'page'),
    ('Şövalye', 'Cavalier', 'knight'),
    ('Kraliçe', 'Reine', 'queen'),
    ('Kral', 'Roi', 'king'),
]

# meaning_fr, meaning_tr par suit (dans l'ordre des RANKS)
MEANINGS = {
    'cups': [
        ('un nouveau départ émotionnel', 'yeni bir duygusal başlangıç'),
        ('harmonie émotionnelle et équilibre', 'duygusal uyum ve denge'),
        ('célébration et joie partagée', 'kutlama ve paylaşılan sevinç'),
        ('apathie émotionnelle ou réflexion', 'duygusal ilgisizlik ya da içe dönüş'),
        ('perte émotionnelle et chagrin', 'duygusal kayıp ve hüzün'),
        ('nostalgie et souvenirs du passé', 'nostalji ve geçmişin anıları'),
        ('choix et illusions émotionnelles', 'seçimler ve duygusal yanılsamalar'),
        ('un pas en arrière vers de nouveaux horizons', 'yeni ufuklar için bir adım geri çekilme'),
        ('satisfaction émotionnelle et contentement', 'duygusal doyum ve memnuniyet'),
        ('harmonie familiale et joie complète', 'ailevi uyum ve tam bir mutluluk'),
        ('un message affectif ou un jeune cœur romantique', 'duygusal bir mesaj ya da genç bir romantik ruh'),
        ("l'arrivée d'une nouvelle émotion ou personne", 'yeni bir duygunun ya da kişinin gelişi'),
        ('intuition et sagesse émotionnelle', 'sezgi ve duygusal bilgelik'),
        ('maturité émotionnelle et maîtrise du cœur', 'duygusal olgunluk ve kalbin hakimiyeti'),
    ],
    'wands': [
        ('une étincelle créative et un nouvel élan', 'yaratıcı bir kıvılcım ve yeni bir atılım'),
        ("planification et vision d'avenir", 'planlama ve geleceğe dair vizyon'),
        ('expansion et croissance des projets', 'projelerin büyümesi ve genişlemesi'),
        ('célébration et accomplissement', 'kutlama ve başarıya ulaşma'),
        ('compétition et conflit', 'rekabet ve çatışma'),
        ('reconnaissance et succès', 'tanınma ve başarı'),
        ('défense et persévérance', 'savunma ve azim'),
        ('rapidité et mouvement soudain', 'hız ve ani hareket'),
        ('vigilance et dernière ligne de défense', 'tetikte olma ve son savunma hattı'),
        ('une charge lourde et un fardeau', 'ağır bir yük ve sorumluluk'),
        ("un message d'action ou un jeune entrepreneur", 'eyleme dair bir mesaj ya da genç bir girişimci'),
        ("l'arrivée rapide d'une énergie ou d'une nouvelle", 'hızlı gelen bir enerji ya da haber'),
        ('passion créative et confiance en soi', 'yaratıcı tutku ve özgüven'),
        ('leadership charismatique et autorité', 'karizmatik liderlik ve otorite'),
    ],
    'swords': [
        ('une clarté mentale nouvelle et une vérité qui émerge', 'yeni bir zihinsel netlik ve ortaya çıkan bir gerçek'),
        ('indécision et équilibre précaire', 'kararsızlık ve hassas bir denge'),
        ('douleur mentale et séparation', 'zihinsel acı ve ayrılık'),
        ('repos mental et pause réflexive', 'zihinsel dinlenme ve düşünce molası'),
        ('conflit et défaite', 'çatışma ve yenilgi'),
        ("transition et voyage vers l'apaisement", 'geçiş ve huzura doğru yolculuk'),
        ('stratégie et tromperie', 'strateji ve aldatma'),
        ('un blocage mental et une restriction', 'zihinsel bir tıkanıklık ve kısıtlanma'),
        ('anxiété et pensées négatives', 'kaygı ve olumsuz düşünceler'),
        ('une fin douloureuse mais définitive', 'acı verici ama kesin bir son'),
        ("un message intellectuel ou un jeune esprit critique", 'zihinsel bir mesaj ya da eleştirel genç bir zihin'),
        ("l'arrivée de vérités ou de communications directes", 'gerçeklerin ya da doğrudan bir haberin gelişi'),
        ('sagesse et clarté mentale', 'bilgelik ve zihinsel netlik'),
        ('autorité intellectuelle et sens de la justice', 'zihinsel otorite ve adalet anlayışı'),
    ],
    'pentacles': [
        ('une nouvelle opportunité matérielle', 'yeni bir maddi fırsat'),
        ('équilibre financier et jonglage entre priorités', 'mali denge ve önceliklerle jonglörlük'),
        ('travail d\'équipe et savoir-faire', 'takım çalışması ve ustalık'),
        ('sécurité financière et attachement matériel', 'mali güvenlik ve maddi bağlılık'),
        ('difficultés matérielles et sentiment de manque', 'maddi zorluklar ve eksiklik hissi'),
        ('générosité et partage équitable', 'cömertlik ve adil paylaşım'),
        ("patience et évaluation du travail accompli", 'sabır ve yapılan işin değerlendirilmesi'),
        ("apprentissage et perfectionnement d'un savoir-faire", 'öğrenme ve bir becerinin geliştirilmesi'),
        ('abondance et indépendance matérielle', 'bolluk ve maddi bağımsızlık'),
        ('héritage et sécurité familiale durable', 'miras ve kalıcı ailevi güvenlik'),
        ('un message financier ou un jeune apprenti sérieux', 'mali bir mesaj ya da ciddi genç bir çırak'),
        ("l'arrivée de nouvelles matérielles concrètes", 'somut maddi haberlerin gelişi'),
        ('prospérité et ancrage terrien', 'bolluk ve toprakla köklenme'),
        ('abondance et autorité matérielle', 'bolluk ve maddi otorite'),
    ],
}


def starts_vowel_sound(s):
    return s[:1].lower() in "aeiouyàâéèêëîïôùûh"


def de_(s):
    """'de' with elision: de_('Épées') -> \"d'Épées\"."""
    return ("d'" + s) if starts_vowel_sound(s) else ("de " + s)


def du_(s):
    """'du' with elision/gender: du_('As') -> \"de l'As\", du_('Reine') -> \"de la Reine\"."""
    if starts_vowel_sound(s):
        return "de l'" + s
    if s in FEMININE_RANKS_FR:
        return "de la " + s
    return "du " + s


FEMININE_RANKS_FR = {"Reine"}


def le_(s, cap=False):
    if starts_vowel_sound(s):
        return ("L'" if cap else "l'") + s
    article = "La " if s in FEMININE_RANKS_FR else "Le "
    return (article if cap else article.lower()) + s


def gen_fr_upright(suit, rank_fr, meaning_fr):
    rank_suit = f"{rank_fr} {de_(suit['fr'])}"
    return field_block(
        intro=f"{le_(rank_fr, cap=True)} {de_(suit['fr'])} porte le thème {de_(meaning_fr)}. Cette carte touche {suit['domain_fr']} et apporte une énergie constructive.",
        love=f"En amour, cette carte apporte {meaning_fr} dans vos liens affectifs.",
        career=f"Sur le plan professionnel, le thème {de_(meaning_fr)} se manifeste dans votre parcours.",
        money=f"Financièrement, l'énergie {de_(meaning_fr)} influence vos ressources.",
        health=f"Pour la santé, {meaning_fr} agit positivement sur votre équilibre général.",
        family=f"En famille, {meaning_fr} colore harmonieusement les liens du foyer.",
        symbols=f"- {suit['emoji']} {rank_suit} : {meaning_fr}\n- L'élément {suit['element_fr']} : {suit['domain_fr']}.",
        questions=f"- « Comment {meaning_fr} se manifeste-t-il dans ma vie en ce moment ? »\n- « Que puis-je apprendre de cette énergie ? »\n- « Comment puis-je pleinement l'accueillir ? »",
        weekly=f"Cette semaine, {meaning_fr} occupe une place centrale. Accueillez cette énergie en confiance.",
        hidden=f"« L'essence {du_(rank_fr)} {de_(suit['fr'])} est {meaning_fr}. »",
    )


def inv_(rank_fr, cap=False):
    word = "inversée" if rank_fr in FEMININE_RANKS_FR else "inversé"
    return word.capitalize() if cap else word


def gen_fr_reversed(suit, rank_fr, meaning_fr):
    rank_suit = f"{rank_fr} {de_(suit['fr'])}"
    return field_block(
        intro=f"{inv_(rank_fr, cap=True)}, {le_(rank_fr)} {de_(suit['fr'])} révèle un blocage autour {de_(meaning_fr)}. L'énergie devient stagnante ou mal dirigée.",
        love=f"En amour, l'absence {de_(meaning_fr)} peut créer de la distance.",
        career=f"Au travail, le blocage {de_(meaning_fr)} freine votre progression.",
        money=f"Financièrement, le manque {de_(meaning_fr)} peut créer des difficultés.",
        health=f"Pour la santé, le blocage {de_(meaning_fr)} se traduit par un déséquilibre.",
        family=f"En famille, des tensions autour {de_(meaning_fr)} peuvent apparaître.",
        symbols=f"- {rank_suit} {inv_(rank_fr)} : énergie bloquée.\n- Le manque : {meaning_fr} entravé.",
        questions=f"- « Qu'est-ce qui bloque {meaning_fr} ? »\n- « Comment puis-je libérer cette énergie ? »\n- « Qu'est-ce que je refuse d'accepter ? »",
        weekly=f"Cette semaine, vous pouvez ressentir le manque {de_(meaning_fr)}. Cherchez à restaurer l'équilibre.",
        hidden=f"« {le_(rank_fr, cap=True)} {inv_(rank_fr)} invite à transformer le blocage en flux. »",
    )


def gen_tr_upright(suit, rank_tr, meaning_tr):
    return field_block(
        intro=f"{suit['tr']} {rank_tr}, {meaning_tr} temasını taşır. Bu kart {suit['domain_tr']} alanıyla ilişkilidir ve yapıcı bir enerji sunar.",
        love=f"Aşkta bu kart, duygusal bağlarınıza {meaning_tr} enerjisini getirir.",
        career=f"Kariyerinizde {meaning_tr} teması ön plana çıkar.",
        money=f"Maddi konularda {meaning_tr} enerjisi kaynaklarınızı etkiler.",
        health=f"Sağlık açısından {meaning_tr} teması genel dengenizi olumlu etkiler.",
        family=f"Aile içinde {meaning_tr} enerjisi ilişkileri uyumlu şekilde renklendirir.",
        symbols=f"- {suit['emoji']} {suit['tr']} {rank_tr}: {meaning_tr}\n- {suit['element_tr']} elementi: {suit['domain_tr']}.",
        questions=f"- \"{meaning_tr.capitalize()} şu anda hayatımda nasıl kendini gösteriyor?\"\n- \"Bu enerjiden ne öğrenebilirim?\"\n- \"Bunu tam olarak nasıl karşılayabilirim?\"",
        weekly=f"Bu hafta {meaning_tr} teması merkezde. Bu enerjiyi güvenle karşılayın.",
        hidden=f"\"Bu kartın özü: {meaning_tr}.\"",
    )


def gen_tr_reversed(suit, rank_tr, meaning_tr):
    return field_block(
        intro=f"Ters {suit['tr']} {rank_tr}, {meaning_tr} konusunda bir tıkanıklığa işaret eder. Enerji durgunlaşmış ya da yanlış yönlenmiş olabilir.",
        love=f"Aşkta {meaning_tr} eksikliği mesafe yaratabilir.",
        career=f"Kariyerde {meaning_tr} teması engellenmiş olabilir, ilerleme yavaşlayabilir.",
        money=f"Maddi konularda {meaning_tr} ile ilgili zorluklar ortaya çıkabilir.",
        health=f"Sağlıkta {meaning_tr} eksikliği dengesizlik olarak hissedilebilir.",
        family=f"Ailede {meaning_tr} etrafındaki gerilimler baş gösterebilir.",
        symbols=f"- Ters {rank_tr}: enerji tıkanmış.\n- Eksiklik: {meaning_tr} konusunda yetersizlik.",
        questions=f"- \"{meaning_tr.capitalize()} konusunda beni engelleyen ne?\"\n- \"Bu enerjiyi nasıl serbest bırakabilirim?\"\n- \"Neyi kabul etmekten kaçınıyorum?\"",
        weekly=f"Bu hafta {meaning_tr} eksikliğini hissedebilirsiniz. Dengeyi yeniden kurmaya odaklanın.",
        hidden=f"\"Ters {suit['tr']} {rank_tr}, tıkanıklığı akışa dönüştürmeye davet eder.\"",
    )


# Cartes mineures TR (pour recuperer number/image dans l'ordre d'origine)
TR_MINORS = [c for c in TR_BASE if c.get('type') == 'minor']


def build_minors():
    cards = []
    idx = 0
    for suit in SUITS:
        meanings = MEANINGS[suit['key']]
        for (rank_tr, rank_fr, rank_key), (meaning_fr, meaning_tr) in zip(RANKS, meanings):
            tr_source = TR_MINORS[idx]
            idx += 1
            name_tr = f"{suit['tr']} ({rank_tr})"
            name_fr = f"{rank_fr} {de_(suit['fr'])}"
            cards.append({
                'id': tr_source['image'].replace('.webp', '') if tr_source.get('image') else f"{suit['key']}_{rank_key}",
                'number': int(tr_source['number']),
                'arcana': 'minor',
                'suit': suit['key'],
                'rank': rank_key,
                'image': tr_source.get('image'),
                'name': {'tr': name_tr, 'fr': name_fr},
                'upright': {
                    'tr': gen_tr_upright(suit, rank_tr, meaning_tr),
                    'fr': gen_fr_upright(suit, rank_fr, meaning_fr),
                },
                'reversed': {
                    'tr': gen_tr_reversed(suit, rank_tr, meaning_tr),
                    'fr': gen_fr_reversed(suit, rank_fr, meaning_fr),
                },
            })
    return cards


def main():
    majors = build_majors()
    minors = build_minors()
    all_cards = majors + minors
    assert len(all_cards) == 78, f"expected 78 cards, got {len(all_cards)}"

    out_path = DATA / "cards.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_cards, f, ensure_ascii=False, indent=2)

    print(f"OK: {len(majors)} majeurs + {len(minors)} mineurs -> {out_path}")


if __name__ == "__main__":
    main()
