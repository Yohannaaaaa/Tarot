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

ZODIAC_PROFILES = {
    "aries": {
        "element": {"fr": "Feu", "tr": "Ateş"},
        "quality": {"fr": "Cardinal", "tr": "Öncü"},
        "planet": {"fr": "Mars", "tr": "Mars"},
        "strengths": {"fr": ["Courageux", "Direct", "Plein d'initiative"],
                      "tr": ["Cesur", "Dobra", "Girişimci"]},
        "weaknesses": {"fr": ["Impatient", "Impulsif"], "tr": ["Sabırsız", "Aceleci"]},
        "compatible": ["leo", "sagittarius", "gemini"],
        "description": {
            "fr": "Premier signe du zodiaque, le Bélier fonce tête baissée vers ce qu'il désire, porté par une énergie de feu qui ne demande qu'à s'exprimer.",
            "tr": "Zodyağın ilk burcu olan Koç, ifade edilmeyi bekleyen ateşli bir enerjiyle istediğine doğru cesurca ilerler."},
    },
    "taurus": {
        "element": {"fr": "Terre", "tr": "Toprak"},
        "quality": {"fr": "Fixe", "tr": "Sabit"},
        "planet": {"fr": "Vénus", "tr": "Venüs"},
        "strengths": {"fr": ["Fiable", "Patient", "Sensuel"], "tr": ["Güvenilir", "Sabırlı", "Duyusal"]},
        "weaknesses": {"fr": ["Têtu", "Possessif"], "tr": ["İnatçı", "Sahiplenici"]},
        "compatible": ["virgo", "capricorn", "cancer"],
        "description": {
            "fr": "Signe de terre gouverné par Vénus, le Taureau cherche la stabilité et le plaisir des sens, avec une patience à toute épreuve.",
            "tr": "Venüs'ün yönettiği bir toprak burcu olan Boğa, tükenmez bir sabırla istikrar ve duyusal zevkler arar."},
    },
    "gemini": {
        "element": {"fr": "Air", "tr": "Hava"},
        "quality": {"fr": "Mutable", "tr": "Değişken"},
        "planet": {"fr": "Mercure", "tr": "Merkür"},
        "strengths": {"fr": ["Curieux", "Communicatif", "Adaptable"], "tr": ["Meraklı", "İletişimci", "Uyumlu"]},
        "weaknesses": {"fr": ["Dispersé", "Changeant"], "tr": ["Dağınık", "Değişken"]},
        "compatible": ["libra", "aquarius", "aries"],
        "description": {
            "fr": "Signe d'air régi par Mercure, les Gémeaux ont l'esprit vif et le besoin constant d'échanger, d'apprendre et de se réinventer.",
            "tr": "Merkür'ün yönettiği bir hava burcu olan İkizler, çevik bir zihne ve sürekli paylaşma, öğrenme, kendini yenileme ihtiyacına sahiptir."},
    },
    "cancer": {
        "element": {"fr": "Eau", "tr": "Su"},
        "quality": {"fr": "Cardinal", "tr": "Öncü"},
        "planet": {"fr": "Lune", "tr": "Ay"},
        "strengths": {"fr": ["Loyal", "Intuitif", "Protecteur"], "tr": ["Sadık", "Sezgisel", "Koruyucu"]},
        "weaknesses": {"fr": ["Susceptible", "Craintif"], "tr": ["Alıngan", "Endişeli"]},
        "compatible": ["scorpio", "pisces", "taurus"],
        "description": {
            "fr": "Signe d'eau gouverné par la Lune, le Cancer vit au rythme de ses émotions et veille sur ceux qu'il aime avec une tendresse discrète.",
            "tr": "Ay'ın yönettiği bir su burcu olan Yengeç, duygularının ritmiyle yaşar ve sevdiklerini sessiz bir şefkatle kollar."},
    },
    "leo": {
        "element": {"fr": "Feu", "tr": "Ateş"},
        "quality": {"fr": "Fixe", "tr": "Sabit"},
        "planet": {"fr": "Soleil", "tr": "Güneş"},
        "strengths": {"fr": ["Généreux", "Charismatique", "Loyal"], "tr": ["Cömert", "Karizmatik", "Sadık"]},
        "weaknesses": {"fr": ["Orgueilleux", "Autoritaire"], "tr": ["Gururlu", "Otoriter"]},
        "compatible": ["aries", "sagittarius", "gemini"],
        "description": {
            "fr": "Signe de feu gouverné par le Soleil, le Lion aime rayonner et être reconnu, tout en restant d'une grande générosité envers son entourage.",
            "tr": "Güneş'in yönettiği bir ateş burcu olan Aslan, parlamayı ve takdir görmeyi sever, çevresine karşı da son derece cömerttir."},
    },
    "virgo": {
        "element": {"fr": "Terre", "tr": "Toprak"},
        "quality": {"fr": "Mutable", "tr": "Değişken"},
        "planet": {"fr": "Mercure", "tr": "Merkür"},
        "strengths": {"fr": ["Méthodique", "Serviable", "Analytique"], "tr": ["Düzenli", "Yardımsever", "Analitik"]},
        "weaknesses": {"fr": ["Perfectionniste", "Anxieux"], "tr": ["Mükemmeliyetçi", "Kaygılı"]},
        "compatible": ["taurus", "capricorn", "cancer"],
        "description": {
            "fr": "Signe de terre régi par Mercure, la Vierge observe, analyse et perfectionne avec un sens du service rarement égalé.",
            "tr": "Merkür'ün yönettiği bir toprak burcu olan Başak, ender rastlanan bir hizmet anlayışıyla gözlemler, analiz eder ve mükemmelleştirir."},
    },
    "libra": {
        "element": {"fr": "Air", "tr": "Hava"},
        "quality": {"fr": "Cardinal", "tr": "Öncü"},
        "planet": {"fr": "Vénus", "tr": "Venüs"},
        "strengths": {"fr": ["Diplomate", "Élégant", "Sociable"], "tr": ["Diplomatik", "Zarif", "Sosyal"]},
        "weaknesses": {"fr": ["Indécis", "Conflit-phobe"], "tr": ["Kararsız", "Çatışmadan kaçan"]},
        "compatible": ["gemini", "aquarius", "leo"],
        "description": {
            "fr": "Signe d'air gouverné par Vénus, la Balance recherche l'harmonie en toute chose et déploie un sens esthétique très marqué.",
            "tr": "Venüs'ün yönettiği bir hava burcu olan Terazi, her şeyde uyum arar ve belirgin bir estetik anlayışa sahiptir."},
    },
    "scorpio": {
        "element": {"fr": "Eau", "tr": "Su"},
        "quality": {"fr": "Fixe", "tr": "Sabit"},
        "planet": {"fr": "Pluton / Mars", "tr": "Plüton / Mars"},
        "strengths": {"fr": ["Déterminé", "Intense", "Loyal"], "tr": ["Kararlı", "Yoğun", "Sadık"]},
        "weaknesses": {"fr": ["Jaloux", "Méfiant"], "tr": ["Kıskanç", "Güvensiz"]},
        "compatible": ["cancer", "pisces", "virgo"],
        "description": {
            "fr": "Signe d'eau gouverné par Pluton, le Scorpion vit tout avec intensité et cache une force de volonté redoutable sous des dehors calmes.",
            "tr": "Plüton'un yönettiği bir su burcu olan Akrep, her şeyi yoğun yaşar ve sakin görünüşünün altında güçlü bir irade saklar."},
    },
    "sagittarius": {
        "element": {"fr": "Feu", "tr": "Ateş"},
        "quality": {"fr": "Mutable", "tr": "Değişken"},
        "planet": {"fr": "Jupiter", "tr": "Jüpiter"},
        "strengths": {"fr": ["Optimiste", "Aventurier", "Franc"], "tr": ["İyimser", "Maceracı", "Dürüst"]},
        "weaknesses": {"fr": ["Sans-tact", "Instable"], "tr": ["Patavatsız", "İstikrarsız"]},
        "compatible": ["aries", "leo", "aquarius"],
        "description": {
            "fr": "Signe de feu gouverné par Jupiter, le Sagittaire a soif de grands espaces, de vérité et de sens à donner à sa vie.",
            "tr": "Jüpiter'in yönettiği bir ateş burcu olan Yay, geniş ufuklara, gerçeğe ve hayatına anlam katmaya susamıştır."},
    },
    "capricorn": {
        "element": {"fr": "Terre", "tr": "Toprak"},
        "quality": {"fr": "Cardinal", "tr": "Öncü"},
        "planet": {"fr": "Saturne", "tr": "Satürn"},
        "strengths": {"fr": ["Discipliné", "Ambitieux", "Responsable"], "tr": ["Disiplinli", "Hırslı", "Sorumlu"]},
        "weaknesses": {"fr": ["Pessimiste", "Rigide"], "tr": ["Karamsar", "Katı"]},
        "compatible": ["taurus", "virgo", "pisces"],
        "description": {
            "fr": "Signe de terre gouverné par Saturne, le Capricorne construit patiemment sa réussite, pierre après pierre, avec un sérieux à toute épreuve.",
            "tr": "Satürn'ün yönettiği bir toprak burcu olan Oğlak, tükenmez bir ciddiyetle başarısını taş taş, sabırla inşa eder."},
    },
    "aquarius": {
        "element": {"fr": "Air", "tr": "Hava"},
        "quality": {"fr": "Fixe", "tr": "Sabit"},
        "planet": {"fr": "Uranus", "tr": "Uranüs"},
        "strengths": {"fr": ["Indépendant", "Visionnaire", "Humaniste"], "tr": ["Bağımsız", "Vizyoner", "İnsancıl"]},
        "weaknesses": {"fr": ["Détaché", "Imprévisible"], "tr": ["Mesafeli", "Öngörülemez"]},
        "compatible": ["gemini", "libra", "sagittarius"],
        "description": {
            "fr": "Signe d'air gouverné par Uranus, le Verseau pense en avance sur son temps et défend ses idées avec une indépendance farouche.",
            "tr": "Uranüs'ün yönettiği bir hava burcu olan Kova, çağının ötesinde düşünür ve fikirlerini yılmaz bir bağımsızlıkla savunur."},
    },
    "pisces": {
        "element": {"fr": "Eau", "tr": "Su"},
        "quality": {"fr": "Mutable", "tr": "Değişken"},
        "planet": {"fr": "Neptune", "tr": "Neptün"},
        "strengths": {"fr": ["Empathique", "Créatif", "Intuitif"], "tr": ["Empatik", "Yaratıcı", "Sezgisel"]},
        "weaknesses": {"fr": ["Évasif", "Influençable"], "tr": ["Kaçıngan", "Kolay etkilenen"]},
        "compatible": ["cancer", "scorpio", "capricorn"],
        "description": {
            "fr": "Dernier signe du zodiaque, gouverné par Neptune, les Poissons nagent entre rêve et réalité avec une sensibilité artistique hors norme.",
            "tr": "Neptün'ün yönettiği zodyağın son burcu olan Balık, olağanüstü bir sanatsal duyarlılıkla hayal ile gerçek arasında yüzer."},
    },
}


def zodiac_profile(sign_id, lang):
    sign = next(s for s in ZODIAC_SIGNS if s["id"] == sign_id)
    profile = ZODIAC_PROFILES[sign_id]
    compatible_names = [
        next(s for s in ZODIAC_SIGNS if s["id"] == cid)["name"][lang]
        for cid in profile["compatible"]
    ]
    return {
        "id": sign_id,
        "symbol": sign["symbol"],
        "name": sign["name"][lang],
        "dates": sign["dates"][lang],
        "element": profile["element"][lang],
        "quality": profile["quality"][lang],
        "planet": profile["planet"][lang],
        "strengths": profile["strengths"][lang],
        "weaknesses": profile["weaknesses"][lang],
        "compatible": compatible_names,
        "description": profile["description"][lang],
    }


def zodiac_profiles(lang):
    return [zodiac_profile(sign["id"], lang) for sign in ZODIAC_SIGNS]


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


ASCENDANT_MEANINGS = {
    "aries": {
        "fr": "Avec un ascendant Bélier, tu dégages dès le premier contact une énergie directe et dynamique. On te perçoit comme quelqu'un de spontané, impatient d'agir et naturellement compétitif.",
        "tr": "Yükselen burcun Koç olunca ilk izlenimin enerjik ve doğrudan oluyor. Çevrendekiler seni girişken, harekete geçmekten çekinmeyen ve doğal olarak rekabetçi biri olarak görüyor.",
    },
    "taurus": {
        "fr": "Avec un ascendant Taureau, tu inspires calme et stabilité dès la première rencontre. Ton allure posée et ton besoin de confort rassurent naturellement ceux qui t'approchent.",
        "tr": "Yükselen burcun Boğa olunca ilk tanışmada sakinlik ve istikrar hissi veriyorsun. Ağırbaşlı duruşun ve konfor arayışın çevrendekileri doğal olarak rahatlatıyor.",
    },
    "gemini": {
        "fr": "Avec un ascendant Gémeaux, tu donnes immédiatement une image vive, curieuse et bavarde. Les gens te trouvent facile d'approche, spirituel et toujours prêt à échanger.",
        "tr": "Yükselen burcun İkizler olunca ilk anda canlı, meraklı ve konuşkan bir izlenim bırakıyorsun. Çevrendekiler seni yaklaşılması kolay, esprili ve her zaman sohbete açık biri olarak buluyor.",
    },
    "cancer": {
        "fr": "Avec un ascendant Cancer, ton allure dégage une douceur protectrice dès le premier regard. On te perçoit comme quelqu'un de sensible, attentionné, parfois réservé tant qu'on ne te connaît pas.",
        "tr": "Yükselen burcun Yengeç olunca ilk bakışta koruyucu bir yumuşaklık yansıtıyorsun. Çevrendekiler seni duyarlı, ilgili ama tanınana kadar biraz mesafeli biri olarak algılıyor.",
    },
    "leo": {
        "fr": "Avec un ascendant Lion, tu attires naturellement l'attention par ta prestance chaleureuse et confiante. Les autres te voient comme charismatique, généreux et fait pour être remarqué.",
        "tr": "Yükselen burcun Aslan olunca sıcak ve özgüvenli duruşunla doğal olarak dikkat çekiyorsun. Çevrendekiler seni karizmatik, cömert ve fark edilmeye değer biri olarak görüyor.",
    },
    "virgo": {
        "fr": "Avec un ascendant Vierge, tu projettes une image soignée, discrète et posée dès le premier contact. On te perçoit comme quelqu'un de sérieux, attentif aux détails et serviable.",
        "tr": "Yükselen burcun Başak olunca ilk izlenimin derli toplu, mütevazı ve ölçülü oluyor. Çevrendekiler seni ciddi, detaylara dikkat eden ve yardımsever biri olarak görüyor.",
    },
    "libra": {
        "fr": "Avec un ascendant Balance, tu dégages d'emblée charme, élégance et sens du contact. Les gens te trouvent aimable, diplomate et agréable à côtoyer.",
        "tr": "Yükselen burcun Terazi olunca ilk anda zarafet ve kolay iletişim kuran bir hava yayıyorsun. Çevrendekiler seni sevimli, diplomatik ve arkadaş canlısı biri olarak buluyor.",
    },
    "scorpio": {
        "fr": "Avec un ascendant Scorpion, ta présence intense et mystérieuse marque dès la première rencontre. On te perçoit comme magnétique, déterminé et difficile à cerner complètement.",
        "tr": "Yükselen burcun Akrep olunca ilk tanışmada yoğun ve gizemli bir hava bırakıyorsun. Çevrendekiler seni manyetik, kararlı ve tam olarak çözülmesi zor biri olarak algılıyor.",
    },
    "sagittarius": {
        "fr": "Avec un ascendant Sagittaire, tu donnes une impression optimiste, ouverte et aventureuse dès le premier échange. Les autres te voient comme franc, enthousiaste et épris de liberté.",
        "tr": "Yükselen burcun Yay olunca ilk temasta iyimser, açık ve maceracı bir izlenim bırakıyorsun. Çevrendekiler seni dürüst, hevesli ve özgürlüğüne düşkün biri olarak görüyor.",
    },
    "capricorn": {
        "fr": "Avec un ascendant Capricorne, tu affiches d'emblée sérieux, retenue et sens des responsabilités. On te perçoit comme fiable, ambitieux et un peu réservé au premier abord.",
        "tr": "Yükselen burcun Oğlak olunca ilk izlenimin ciddi, ölçülü ve sorumluluk sahibi oluyor. Çevrendekiler seni güvenilir, hırslı ve ilk başta biraz mesafeli biri olarak görüyor.",
    },
    "aquarius": {
        "fr": "Avec un ascendant Verseau, ton originalité et ton indépendance se remarquent dès le premier contact. Les gens te trouvent différent, ouvert d'esprit et parfois imprévisible.",
        "tr": "Yükselen burcun Kova olunca ilk anda özgünlüğün ve bağımsızlığın dikkat çekiyor. Çevrendekiler seni farklı, açık fikirli ve bazen öngörülmesi zor biri olarak buluyor.",
    },
    "pisces": {
        "fr": "Avec un ascendant Poissons, tu dégages une douceur rêveuse et empathique dès la première rencontre. On te perçoit comme sensible, artiste dans l'âme et facilement touché par les autres.",
        "tr": "Yükselen burcun Balık olunca ilk tanışmada hayalperest ve empatik bir yumuşaklık yansıtıyorsun. Çevrendekiler seni duyarlı, ruhen sanatçı ve başkalarından kolay etkilenen biri olarak görüyor.",
    },
}


def ascendant_meaning(sign_id, lang):
    return ASCENDANT_MEANINGS[sign_id][lang]
