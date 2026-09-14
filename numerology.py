#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Numerologie du chemin de vie : calcul deterministe (reduction numerique
de la date de naissance) + texte pioche dans des pools ecrits a la main.
Gratuit, stable, meme principe que horoscope.py."""
import hashlib

MASTER_NUMBERS = (11, 22, 33)


def _seed(*parts):
    digest = hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest, 16)


def _pick(pool, seed):
    return pool[seed % len(pool)]


def _reduce(n):
    while n > 9 and n not in MASTER_NUMBERS:
        n = sum(int(d) for d in str(n))
    return n


def life_path_number(birth_date):
    digits_sum = sum(int(d) for d in birth_date.strftime("%Y%m%d"))
    return _reduce(digits_sum)


NUMEROLOGY_KEYWORDS = {
    1: {"fr": "Le Leader", "tr": "Lider"},
    2: {"fr": "Le Diplomate", "tr": "Diplomat"},
    3: {"fr": "Le Créatif", "tr": "Yaratıcı"},
    4: {"fr": "Le Bâtisseur", "tr": "İnşacı"},
    5: {"fr": "Le Libre", "tr": "Özgür Ruh"},
    6: {"fr": "Le Protecteur", "tr": "Koruyucu"},
    7: {"fr": "Le Chercheur", "tr": "Arayıcı"},
    8: {"fr": "Le Bâtisseur d'Empire", "tr": "İmparatorluk Kurucusu"},
    9: {"fr": "L'Humaniste", "tr": "Hümanist"},
    11: {"fr": "Le Visionnaire", "tr": "Vizyoner"},
    22: {"fr": "Le Maître Bâtisseur", "tr": "Usta İnşacı"},
    33: {"fr": "Le Maître Guérisseur", "tr": "Usta Şifacı"},
}

NUMEROLOGY_TEXTS = {
    1: {
        "fr": [
            "Ton chemin de vie 1 fait de toi un pionnier né : tu avances en premier, tu inities, tu n'attends pas la permission des autres pour te lancer.",
            "Avec un 1, l'indépendance est ton moteur. Tu préfères tracer ta propre voie plutôt que suivre celle des autres, même si cela demande du courage.",
            "Le 1 te pousse naturellement vers le leadership : les projets qui te ressemblent sont ceux où tu peux décider et avancer à ton rythme.",
        ],
        "tr": [
            "1 yaşam yolu seni doğuştan bir öncü yapıyor: ilk adımı sen atarsın, başlatırsın, başkalarının iznini beklemeden harekete geçersin.",
            "1 sayısıyla bağımsızlık senin motorun. Başkalarının yolunu izlemektense kendi yolunu çizmeyi tercih edersin, cesaret gerektirse bile.",
            "1 seni doğal olarak liderliğe yönlendiriyor: sana uygun projeler, karar verip kendi hızında ilerleyebildiğin projeler.",
        ],
    },
    2: {
        "fr": [
            "Ton chemin de vie 2 révèle un talent naturel pour la diplomatie : tu sens les tensions avant qu'elles n'éclatent et tu sais apaiser les situations.",
            "Avec un 2, la sensibilité et l'écoute sont tes forces. Tu t'épanouis dans les relations à deux et le travail d'équipe plus que dans la compétition.",
            "Le 2 te donne un besoin profond d'harmonie : tu cherches l'équilibre partout, dans tes relations comme dans tes choix de vie.",
        ],
        "tr": [
            "2 yaşam yolu doğal bir diplomasi yeteneği ortaya koyuyor: gerginlikleri patlak vermeden hissedip durumları yatıştırmayı bilirsin.",
            "2 sayısıyla hassasiyet ve dinleme gücün en büyük yeteneklerin. Rekabetten çok ikili ilişkilerde ve takım çalışmasında parlarsın.",
            "2 sana derin bir uyum ihtiyacı veriyor: hem ilişkilerinde hem hayat seçimlerinde dengeyi arıyorsun.",
        ],
    },
    3: {
        "fr": [
            "Ton chemin de vie 3 déborde de créativité : les mots, l'art ou l'expression de soi sont des terrains où tu te sens vivant.",
            "Avec un 3, ta joie de vivre est contagieuse. Tu as besoin de t'exprimer, de créer et de partager pour te sentir pleinement toi-même.",
            "Le 3 t'offre un charme naturel et une facilité à communiquer : les autres se sentent bien en ta présence sans savoir vraiment pourquoi.",
        ],
        "tr": [
            "3 yaşam yolu yaratıcılıkla dolup taşıyor: kelimeler, sanat veya kendini ifade etme senin en canlı hissettiğin alanlar.",
            "3 sayısıyla yaşama sevincin bulaşıcı. Kendini tam olarak hissetmek için ifade etmeye, yaratmaya ve paylaşmaya ihtiyacın var.",
            "3 sana doğal bir çekicilik ve kolay iletişim kurma yeteneği veriyor: insanlar yanında neden bilmeden iyi hissediyor.",
        ],
    },
    4: {
        "fr": [
            "Ton chemin de vie 4 fait de toi quelqu'un de solide et méthodique : tu construis pierre par pierre, sans jamais bâcler les fondations.",
            "Avec un 4, la discipline et le sens du travail bien fait sont tes marques de fabrique. On peut compter sur toi, quoi qu'il arrive.",
            "Le 4 te donne un besoin de structure et de stabilité : le désordre te pèse, l'organisation te libère.",
        ],
        "tr": [
            "4 yaşam yolu seni sağlam ve metodik biri yapıyor: temelleri asla atlamadan taş taş üstüne koyarsın.",
            "4 sayısıyla disiplin ve iyi yapılmış iş senin imzan. Ne olursa olsun sana güvenilebilir.",
            "4 sana yapı ve istikrar ihtiyacı veriyor: düzensizlik seni yorar, organizasyon seni özgürleştirir.",
        ],
    },
    5: {
        "fr": [
            "Ton chemin de vie 5 a soif de liberté et de changement : la routine t'étouffe, l'aventure te fait vibrer.",
            "Avec un 5, la curiosité te pousse à tout essayer au moins une fois. Tu t'adaptes vite et tu détestes qu'on t'enferme dans une case.",
            "Le 5 t'offre un magnétisme naturel : les autres sont attirés par ton énergie mouvante et imprévisible.",
        ],
        "tr": [
            "5 yaşam yolu özgürlük ve değişim susuzluğu taşıyor: rutin seni boğar, macera seni canlandırır.",
            "5 sayısıyla merakın seni her şeyi en az bir kez denemeye itiyor. Hızlı uyum sağlarsın ve bir kalıba sokulmaktan nefret edersin.",
            "5 sana doğal bir manyetizma veriyor: çevrendekiler senin hareketli ve öngörülemez enerjine çekiliyor.",
        ],
    },
    6: {
        "fr": [
            "Ton chemin de vie 6 fait de toi un protecteur naturel : la famille, les proches et l'harmonie du foyer comptent plus que tout.",
            "Avec un 6, le sens des responsabilités est immense. Tu prends soin des autres, parfois avant de penser à toi-même.",
            "Le 6 t'offre un grand cœur et un vrai sens esthétique : tu aimes que les choses soient belles et harmonieuses autour de toi.",
        ],
        "tr": [
            "6 yaşam yolu seni doğal bir koruyucu yapıyor: aile, yakınlar ve ev huzuru her şeyden önce gelir.",
            "6 sayısıyla sorumluluk duygun çok güçlü. Bazen kendinden önce başkalarına bakarsın.",
            "6 sana büyük bir kalp ve gerçek bir estetik anlayışı veriyor: çevrendeki her şeyin güzel ve uyumlu olmasını istersin.",
        ],
    },
    7: {
        "fr": [
            "Ton chemin de vie 7 est celui du chercheur : tu veux comprendre le pourquoi des choses, au-delà des apparences.",
            "Avec un 7, la solitude ne te fait pas peur, elle te nourrit. C'est dans le calme que tes meilleures intuitions émergent.",
            "Le 7 te donne un esprit analytique et une intuition rare : tu perçois souvent ce que les autres ne voient même pas.",
        ],
        "tr": [
            "7 yaşam yolu arayıcının yolu: görünenin ötesinde, işlerin neden olduğunu anlamak istersin.",
            "7 sayısıyla yalnızlık seni korkutmaz, seni besler. En iyi sezgilerin sessizlikte ortaya çıkar.",
            "7 sana analitik bir zihin ve nadir bir sezgi veriyor: çoğu zaman başkalarının göremediğini fark edersin.",
        ],
    },
    8: {
        "fr": [
            "Ton chemin de vie 8 porte l'ambition et le sens du pouvoir : tu vises grand, surtout dans le matériel et la réussite concrète.",
            "Avec un 8, ton énergie est faite pour bâtir : les projets d'envergure et les responsabilités importantes ne te font pas peur.",
            "Le 8 t'offre un instinct pour reconnaître les opportunités et un vrai talent pour transformer le travail en résultats durables.",
        ],
        "tr": [
            "8 yaşam yolu hırs ve güç duygusu taşıyor: özellikle maddi başarıda büyük hedefler koyarsın.",
            "8 sayısıyla enerjin inşa etmek için var: büyük projeler ve önemli sorumluluklar seni korkutmaz.",
            "8 sana fırsatları tanıma içgüdüsü ve emeği kalıcı sonuçlara dönüştürme yeteneği veriyor.",
        ],
    },
    9: {
        "fr": [
            "Ton chemin de vie 9 est tourné vers les autres : ta générosité et ton idéalisme dépassent souvent l'intérêt personnel.",
            "Avec un 9, tu ressens profondément le monde qui t'entoure. Les causes justes et l'entraide te touchent particulièrement.",
            "Le 9 t'offre une sagesse qui semble parfois plus grande que ton âge : tu vois large, au-delà de ta propre vie.",
        ],
        "tr": [
            "9 yaşam yolu başkalarına yönelik: cömertliğin ve idealizmin çoğu zaman kişisel çıkarının önüne geçer.",
            "9 sayısıyla çevrendeki dünyayı derinden hissedersin. Adil davalar ve dayanışma seni özellikle etkiler.",
            "9 sana yaşından büyük görünen bir bilgelik veriyor: kendi hayatının ötesini görürsün.",
        ],
    },
    11: {
        "fr": [
            "Ton chemin de vie 11 est un nombre maître : ton intuition est exceptionnelle, presque visionnaire, mais elle demande à être canalisée.",
            "Avec un 11, tu ressens les choses avant même de les comprendre rationnellement. C'est un don puissant, à condition d'apprendre à le maîtriser.",
            "Le 11 t'offre une sensibilité rare qui peut inspirer les autres, mais qui te demande aussi de prendre soin de ton équilibre intérieur.",
        ],
        "tr": [
            "11 yaşam yolu bir usta sayı: sezgin olağanüstü, neredeyse vizyoner düzeyde, ama yönlendirilmeyi gerektiriyor.",
            "11 ile bir şeyleri mantıkla anlamadan önce hissedersin. Bu güçlü bir armağan, ama ustalaşmayı öğrenmek şartıyla.",
            "11 sana başkalarına ilham verebilecek nadir bir hassasiyet veriyor, ama iç dengene de dikkat etmeni istiyor.",
        ],
    },
    22: {
        "fr": [
            "Ton chemin de vie 22 est celui du maître bâtisseur : tu as le potentiel de transformer de grandes idées en réalisations concrètes et durables.",
            "Avec un 22, tu combines la vision du 11 et le sens pratique du 4 : ce qui te distingue, c'est ta capacité à voir grand tout en restant les pieds sur terre.",
            "Le 22 t'offre un potentiel rare pour marquer durablement ton entourage, à condition de croire en l'ampleur de ce que tu peux accomplir.",
        ],
        "tr": [
            "22 yaşam yolu usta inşacının yolu: büyük fikirleri somut ve kalıcı başarılara dönüştürme potansiyeline sahipsin.",
            "22 ile 11'in vizyonunu 4'ün pratikliğiyle birleştiriyorsun: seni farklı kılan, ayakların yere basarken büyük düşünebilmen.",
            "22 sana çevrende kalıcı bir iz bırakma potansiyeli veriyor, yeter ki başarabileceklerinin büyüklüğüne inan.",
        ],
    },
    33: {
        "fr": [
            "Ton chemin de vie 33 est celui du maître guérisseur : ta présence même peut apaiser et soutenir ceux qui t'entourent.",
            "Avec un 33, l'amour inconditionnel et le dévouement aux autres sont au cœur de ta mission de vie, souvent sans que tu t'en rendes compte.",
            "Le 33 t'offre une capacité rare à transformer la souffrance en compassion, la tienne comme celle des autres.",
        ],
        "tr": [
            "33 yaşam yolu usta şifacının yolu: varlığın bile çevrendekileri yatıştırıp destekleyebiliyor.",
            "33 ile koşulsuz sevgi ve başkalarına adanmışlık, çoğu zaman farkında olmadan, yaşam misyonunun merkezinde.",
            "33 sana acıyı -kendi acını ve başkalarınınkini- şefkate dönüştürme konusunda nadir bir yetenek veriyor.",
        ],
    },
}


def numerology_reading(birth_date, lang):
    number = life_path_number(birth_date)
    pool = NUMEROLOGY_TEXTS[number][lang]
    text = _pick(pool, _seed(birth_date.isoformat(), "numerology_text"))
    return {
        "number": number,
        "keyword": NUMEROLOGY_KEYWORDS[number][lang],
        "text": text,
    }
