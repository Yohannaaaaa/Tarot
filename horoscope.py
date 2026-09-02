#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Burc yorumu quotidien, genere sans API : combinaison deterministe
(date + signe + categorie) d'un trait astrologique et d'une formule,
piochee dans des pools ecrits a la main. Gratuit, stable, change chaque jour."""
import hashlib
from datetime import date

ZODIAC_SIGNS = [
    {"id": "aries", "symbol": "♈", "name": {"fr": "Bélier", "tr": "Koç"},
     "dates": {"fr": "21 mars – 19 avril", "tr": "21 Mart – 19 Nisan"}},
    {"id": "taurus", "symbol": "♉", "name": {"fr": "Taureau", "tr": "Boğa"},
     "dates": {"fr": "20 avril – 20 mai", "tr": "20 Nisan – 20 Mayıs"}},
    {"id": "gemini", "symbol": "♊", "name": {"fr": "Gémeaux", "tr": "İkizler"},
     "dates": {"fr": "21 mai – 20 juin", "tr": "21 Mayıs – 20 Haziran"}},
    {"id": "cancer", "symbol": "♋", "name": {"fr": "Cancer", "tr": "Yengeç"},
     "dates": {"fr": "21 juin – 22 juillet", "tr": "21 Haziran – 22 Temmuz"}},
    {"id": "leo", "symbol": "♌", "name": {"fr": "Lion", "tr": "Aslan"},
     "dates": {"fr": "23 juillet – 22 août", "tr": "23 Temmuz – 22 Ağustos"}},
    {"id": "virgo", "symbol": "♍", "name": {"fr": "Vierge", "tr": "Başak"},
     "dates": {"fr": "23 août – 22 septembre", "tr": "23 Ağustos – 22 Eylül"}},
    {"id": "libra", "symbol": "♎", "name": {"fr": "Balance", "tr": "Terazi"},
     "dates": {"fr": "23 septembre – 22 octobre", "tr": "23 Eylül – 22 Ekim"}},
    {"id": "scorpio", "symbol": "♏", "name": {"fr": "Scorpion", "tr": "Akrep"},
     "dates": {"fr": "23 octobre – 21 novembre", "tr": "23 Ekim – 21 Kasım"}},
    {"id": "sagittarius", "symbol": "♐", "name": {"fr": "Sagittaire", "tr": "Yay"},
     "dates": {"fr": "22 novembre – 21 décembre", "tr": "22 Kasım – 21 Aralık"}},
    {"id": "capricorn", "symbol": "♑", "name": {"fr": "Capricorne", "tr": "Oğlak"},
     "dates": {"fr": "22 décembre – 19 janvier", "tr": "22 Aralık – 19 Ocak"}},
    {"id": "aquarius", "symbol": "♒", "name": {"fr": "Verseau", "tr": "Kova"},
     "dates": {"fr": "20 janvier – 18 février", "tr": "20 Ocak – 18 Şubat"}},
    {"id": "pisces", "symbol": "♓", "name": {"fr": "Poissons", "tr": "Balık"},
     "dates": {"fr": "19 février – 20 mars", "tr": "19 Şubat – 20 Mart"}},
]

TRAITS = {
    "aries": {
        "fr": ["Ton énergie de feu prend les devants aujourd'hui.",
               "Ton impatience naturelle veut des résultats rapides.",
               "Ton instinct de pionnier s'active dès le matin.",
               "Ta franchise directe marque les esprits autour de toi."],
        "tr": ["Ateşli enerjin bugün seni öne çıkarıyor.",
               "Doğal sabırsızlığın hızlı sonuç istiyor.",
               "Öncü içgüdün sabahtan itibaren devreye giriyor.",
               "Dobra tavrın çevrendekilerin aklında kalıyor."],
    },
    "taurus": {
        "fr": ["Ta stabilité légendaire rassure ceux qui t'entourent.",
               "Ton goût du confort guide tes choix aujourd'hui.",
               "Ta patience têtue finit toujours par payer.",
               "Ton sens pratique évite les faux pas inutiles."],
        "tr": ["Efsanevi kararlılığın çevrendekileri rahatlatıyor.",
               "Konfor sevgin bugünkü seçimlerine yön veriyor.",
               "İnatçı sabrın er ya da geç meyvesini veriyor.",
               "Pratik yaklaşımın gereksiz yanlış adımları önlüyor."],
    },
    "gemini": {
        "fr": ["Ta curiosité vive papillonne d'une idée à l'autre.",
               "Ton besoin de parler trouve enfin une bonne oreille.",
               "Ton esprit vif jongle avec plusieurs projets à la fois.",
               "Ta double nature hésite entre deux options aujourd'hui."],
        "tr": ["Canlı merakın bir fikirden diğerine sıçrıyor.",
               "Konuşma ihtiyacın nihayet iyi bir dinleyici buluyor.",
               "Çevik zihnin aynı anda birkaç işi birden çeviriyor.",
               "İkili doğan bugün iki seçenek arasında kararsız."],
    },
    "cancer": {
        "fr": ["Ta sensibilité lunaire capte ce que les autres taisent.",
               "Ton instinct protecteur veille sur ceux que tu aimes.",
               "Ta mémoire affective refait surface sans prévenir.",
               "Ton besoin de cocon se fait sentir ce soir."],
        "tr": ["Ay gibi hassasiyetin başkalarının söylemediğini seziyor.",
               "Koruyucu içgüdün sevdiklerini kolluyor.",
               "Duygusal hafızan habersizce yeniden canlanıyor.",
               "Bugün kendi köşene çekilme isteğin ağır basıyor."],
    },
    "leo": {
        "fr": ["Ton rayonnement solaire attire naturellement les regards.",
               "Ta générosité de cœur ouvre des portes aujourd'hui.",
               "Ta fierté demande à être reconnue à sa juste valeur.",
               "Ton envie de briller trouve une belle occasion."],
        "tr": ["Güneş gibi parlaklığın doğal olarak dikkat çekiyor.",
               "Cömert kalbin bugün kapılar açıyor.",
               "Gururun hak ettiği takdiri görmek istiyor.",
               "Parlama isteğin güzel bir fırsatla karşılaşıyor."],
    },
    "virgo": {
        "fr": ["Ton sens du détail repère ce qui cloche immédiatement.",
               "Ton envie d'aider se met au service des autres.",
               "Ton perfectionnisme veut tout reprendre à zéro.",
               "Ton esprit analytique cherche une explication logique."],
        "tr": ["Detaycı bakışın aksayan noktayı hemen fark ediyor.",
               "Yardım etme isteğin başkalarının hizmetine giriyor.",
               "Mükemmeliyetçiliğin her şeyi baştan yapmak istiyor.",
               "Analitik zihnin mantıklı bir açıklama arıyor."],
    },
    "libra": {
        "fr": ["Ton besoin d'équilibre pèse le pour et le contre.",
               "Ton sens esthétique embellit tout ce que tu touches.",
               "Ta diplomatie naturelle désamorce une tension latente.",
               "Ton envie de partage cherche une belle compagnie."],
        "tr": ["Denge ihtiyacın artıları eksileri tartıyor.",
               "Estetik anlayışın dokunduğun her şeyi güzelleştiriyor.",
               "Doğal diplomasin gizli bir gerginliği yumuşatıyor.",
               "Paylaşma isteğin güzel bir beraberlik arıyor."],
    },
    "scorpio": {
        "fr": ["Ton intensité intérieure ne laisse rien paraître.",
               "Ton instinct perçant voit au-delà des apparences.",
               "Ta détermination silencieuse avance sans faire de bruit.",
               "Ton magnétisme trouble attire autant qu'il intrigue."],
        "tr": ["İçindeki yoğunluk dışarıya hiçbir şey sızdırmıyor.",
               "Keskin sezgin görünenin ötesini fark ediyor.",
               "Sessiz kararlılığın gürültü çıkarmadan ilerliyor.",
               "Gizemli manyetizman hem çekiyor hem meraklandırıyor."],
    },
    "sagittarius": {
        "fr": ["Ton envie d'ailleurs te fait rêver de grands espaces.",
               "Ton optimisme contagieux remonte le moral autour de toi.",
               "Ta soif de vérité te pousse à dire les choses.",
               "Ton besoin de liberté supporte mal les contraintes."],
        "tr": ["Uzaklara gitme isteğin geniş ufuklar hayal ettiriyor.",
               "Bulaşıcı iyimserliğin çevrendekilerin moralini yükseltiyor.",
               "Gerçeği arayışın seni açık konuşmaya itiyor.",
               "Özgürlük ihtiyacın kısıtlamalara pek tahammül etmiyor."],
    },
    "capricorn": {
        "fr": ["Ta discipline de fond avance un pas après l'autre.",
               "Ton ambition tranquille vise déjà plus loin.",
               "Ton sens du devoir passe avant tes envies du jour.",
               "Ta patience de bâtisseur construit sur le long terme."],
        "tr": ["Köklü disiplinin adım adım ilerliyor.",
               "Sakin hırsın şimdiden daha ileriyi hedefliyor.",
               "Sorumluluk duygun bugünkü isteklerinin önüne geçiyor.",
               "İnşacı sabrın uzun vadeli bir şey kuruyor."],
    },
    "aquarius": {
        "fr": ["Ton esprit indépendant refuse de suivre le troupeau.",
               "Ta vision d'avant-garde surprend ton entourage.",
               "Ton détachement apparent cache une vraie sensibilité.",
               "Ton goût pour la nouveauté cherche à casser la routine."],
        "tr": ["Bağımsız ruhun sürüyü takip etmeyi reddediyor.",
               "İleri görüşlü bakışın çevreni şaşırtıyor.",
               "Görünürdeki mesafen aslında gerçek bir duyarlılığı saklıyor.",
               "Yenilik arayışın rutini kırmak istiyor."],
    },
    "pisces": {
        "fr": ["Ton imagination débordante t'emmène loin de la réalité.",
               "Ta sensibilité artistique capte des émotions invisibles aux autres.",
               "Ton empathie profonde absorbe l'ambiance autour de toi.",
               "Ton besoin d'évasion se fait sentir aujourd'hui."],
        "tr": ["Taşan hayal gücün seni gerçeklikten uzaklaştırıyor.",
               "Sanatsal duyarlılığın başkalarının fark etmediği duyguları seziyor.",
               "Derin empatin çevrendeki havayı olduğu gibi emiyor.",
               "Bugün kaçış ihtiyacın kendini hissettiriyor."],
    },
}

CATEGORY_TEMPLATES = {
    "love": {
        "fr": [
            "En amour, une conversation honnête peut rapprocher deux cœurs.",
            "Côté sentimental, laisse parler ton cœur avant ta raison.",
            "En couple, un petit geste tendre vaut plus qu'un grand discours.",
            "Célibataire, une rencontre inattendue pourrait retenir ton attention.",
            "En amour, évite de dramatiser un simple malentendu.",
            "Ta relation a besoin d'un moment rien qu'à deux aujourd'hui.",
            "En amour, la patience compte plus que les grandes déclarations.",
            "Un sentiment ancien refait surface et mérite d'être écouté.",
        ],
        "tr": [
            "Aşkta dürüst bir konuşma iki kalbi yakınlaştırabilir.",
            "Duygusal konularda bugün mantığından çok kalbini dinle.",
            "İlişkinde küçük bir jest, büyük laflardan daha değerli.",
            "Bekarsan, beklenmedik bir tanışma dikkatini çekebilir.",
            "Aşkta basit bir yanlış anlaşılmayı büyütmekten kaçın.",
            "İlişkin bugün sadece ikinize ait bir ana ihtiyaç duyuyor.",
            "Aşkta sabır, büyük sözlerden daha değerli bugün.",
            "Eski bir duygu yeniden gün yüzüne çıkıyor ve dinlenmeyi hak ediyor."],
    },
    "work": {
        "fr": [
            "Côté carrière, une initiative discrète peut porter ses fruits.",
            "Sur le plan financier, évite une dépense impulsive aujourd'hui.",
            "Au travail, ta rigueur est remarquée par les bonnes personnes.",
            "Une opportunité professionnelle mérite d'être étudiée de près.",
            "Côté argent, un ancien dossier pourrait enfin se débloquer.",
            "Au travail, mieux vaut clarifier les choses que les laisser traîner.",
            "Sur le plan matériel, la prudence paie plus que la précipitation.",
            "Une collaboration bien menée aujourd'hui ouvre une porte demain.",
        ],
        "tr": [
            "Kariyerde sessiz bir girişim meyvesini verebilir.",
            "Maddi konularda bugün ani bir harcamadan kaçın.",
            "İşte gösterdiğin titizlik doğru kişilerin dikkatini çekiyor.",
            "Önüne çıkan bir iş fırsatı yakından incelenmeyi hak ediyor.",
            "Para konusunda eski bir mesele nihayet çözülebilir.",
            "İşte bir şeyi belirsiz bırakmaktansa netleştirmek daha iyi.",
            "Maddi konularda acele etmek yerine temkinli olmak kazandırıyor.",
            "Bugün iyi yürütülen bir iş birliği yarın yeni bir kapı açıyor."],
    },
    "general": {
        "fr": [
            "La journée favorise les décisions prises calmement.",
            "Un signe extérieur confirme ce que tu pressentais déjà.",
            "Ton énergie du jour se prête bien à un nouveau départ.",
            "Prends le temps d'écouter ton intuition avant d'agir.",
            "Une petite contrariété du matin s'arrange dans l'après-midi.",
            "C'est un bon jour pour remettre de l'ordre dans tes priorités.",
            "Ton entourage a plus d'influence sur ton humeur que d'habitude.",
            "Une pause loin des écrans te ferait beaucoup de bien aujourd'hui.",
        ],
        "tr": [
            "Bugün sakin alınan kararlar daha çok işine yarıyor.",
            "Dışarıdan gelen bir işaret zaten sezdiğini doğruluyor.",
            "Bugünkü enerjin yeni bir başlangıç için uygun.",
            "Harekete geçmeden önce sezgilerini dinlemeye zaman ayır.",
            "Sabahki küçük bir aksilik öğleden sonra düzeliyor.",
            "Önceliklerini yeniden düzenlemek için iyi bir gün.",
            "Çevrendekiler bugün ruh haline her zamankinden fazla etki ediyor.",
            "Ekranlardan uzak kısa bir mola bugün sana çok iyi gelir."],
    },
}

CATEGORIES = ["love", "work", "general"]


def _seed(*parts):
    digest = hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest, 16)


def _pick(pool, seed):
    return pool[seed % len(pool)]


def daily_line(sign_id, category, lang, day=None):
    day = day or date.today()
    day_str = day.isoformat()
    trait_pool = TRAITS[sign_id][lang]
    template_pool = CATEGORY_TEMPLATES[category][lang]
    trait = _pick(trait_pool, _seed(day_str, sign_id, "trait"))
    template = _pick(template_pool, _seed(day_str, sign_id, category))
    return f"{trait} {template}"


def daily_horoscope_for_sign(sign, lang, day=None):
    return {
        "id": sign["id"],
        "symbol": sign["symbol"],
        "name": sign["name"][lang],
        "dates": sign["dates"][lang],
        "love": daily_line(sign["id"], "love", lang, day),
        "work": daily_line(sign["id"], "work", lang, day),
        "general": daily_line(sign["id"], "general", lang, day),
    }


def daily_horoscopes(lang, day=None):
    return [daily_horoscope_for_sign(sign, lang, day) for sign in ZODIAC_SIGNS]
