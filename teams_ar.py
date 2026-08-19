# English team names -> Arabic (for DB migration)

import re

_ARABIC_INDIC = "٠١٢٣٤٥٦٧٨٩"

_MATCH_WINNER_EN = re.compile(r"^Match Winner (\d+)$", re.IGNORECASE)
_MATCH_N_WINNER_EN = re.compile(r"^Match (\d+) Winner$", re.IGNORECASE)
_WINNER_M_EN = re.compile(r"^Winner M(\d+)$", re.IGNORECASE)
_MATCH_N_LOSER_EN = re.compile(r"^Match (\d+) Loser$", re.IGNORECASE)
_RUNNER_UP_M_EN = re.compile(r"^Runner-up M(\d+)$", re.IGNORECASE)

TEAM_EN_TO_AR: dict[str, str] = {
    "Mexico": "المكسيك",
    "South Africa": "جنوب أفريقيا",
    "South Korea": "كوريا الجنوبية",
    "Czechia": "التشيك",
    "Canada": "كندا",
    "Bosnia and Herzegovina": "البوسنة والهرسك",
    "USA": "الولايات المتحدة",
    "Paraguay": "باراغواي",
    "Haiti": "هايتي",
    "Scotland": "اسكتلندا",
    "Australia": "أستراليا",
    "Turkiye": "تركيا",
    "Brazil": "البرازيل",
    "Morocco": "المغرب",
    "Qatar": "قطر",
    "Switzerland": "سويسرا",
    "Ivory Coast": "ساحل العاج",
    "Ecuador": "الإكوادور",
    "Germany": "ألمانيا",
    "Curacao": "كوراساو",
    "Netherlands": "هولندا",
    "Japan": "اليابان",
    "Sweden": "السويد",
    "Tunisia": "تونس",
    "Saudi Arabia": "السعودية",
    "Uruguay": "الأوروغواي",
    "Spain": "إسبانيا",
    "Cape Verde": "الرأس الأخضر",
    "Iran": "إيران",
    "New Zealand": "نيوزيلندا",
    "Belgium": "بلجيكا",
    "Egypt": "مصر",
    "France": "فرنسا",
    "Senegal": "السنغال",
    "Iraq": "العراق",
    "Norway": "النرويج",
    "Argentina": "الأرجنتين",
    "Algeria": "الجزائر",
    "Austria": "النمسا",
    "Jordan": "الأردن",
    "Ghana": "غانا",
    "Panama": "بنما",
    "England": "إنجلترا",
    "Croatia": "كرواتيا",
    "Portugal": "البرتغال",
    "DR Congo": "الكونغو الديمقراطية",
    "Uzbekistan": "أوزبكستان",
    "Colombia": "كولومبيا",
    # League season clubs
    "Real Madrid": "ريال مدريد",
    "Barcelona": "برشلونة",
    "Man United": "مانشستر يونايتد",
    "Manchester United": "مانشستر يونايتد",
    "Man City": "مانشستر سيتي",
    "Manchester City": "مانشستر سيتي",
    "Liverpool": "ليفربول",
    "Arsenal": "أرسنال",
    "Chelsea": "تشيلسي",

    # La Liga / PL / CL opponents for league season
    "AC Milan": "ميلان",
    "Ajax": "أياكس",
    "Aston Villa": "أستون فيلا",
    "Atalanta": "أتلنتا",
    "Athletic Bilbao": "أتلتيك بيلباو",
    "Espanyol": "إسبانيول",
    "Atletico Madrid": "أتلتيكو مدريد",
    "Bayer Leverkusen": "بايل ليفركوزن",
    "Bayern Munich": "بايرن ميونخ",
    "Benfica": "بنفيكا",
    "Borussia Dortmund": "بوروسيا دورتموند",
    "Bournemouth": "بورنموث",
    "Brighton": "برايتون",
    "Celtic": "سلتيك",
    "Crystal Palace": "كريستال بالاس",
    "Coventry City": "كوفنتري",
    "Coventry": "كوفنتري",
    "Como": "كومو",
    "Club Brugge": "كلوب بروج",
    "Elche": "إلتشي",
    "Feyenoord": "فينوورد",
    "Galatasaray": "غلطة سراي",
    "Hull City": "هال",
    "Hull": "هال",
    "Ipswich Town": "إبسويتش",
    "Ipswich": "إبسويتش",
    "Lille": "ليل",
    "Málaga": "مالaga",
    "Malaga": "مالaga",
    "Málaga CF": "مالaga",
    "Osasuna": "أوساسونا",
    "PSV": "بي إس في",
    "PSV Eindhoven": "بي إس في",
    "Rayo Vallecano": "رايو فاليكانو",
    "Real Oviedo": "ريال أوفييدo",
    "Shakhtar Donetsk": "شاختار دونيتسك",
    "Slavia Prague": "سلافيا براغ",
    "Sunderland": "سندرلاند",
    "Fulham": "فولهام",
    "Girona": "جيرونا",
    "Inter Milan": "إنتر ميلان",
    "Juventus": "يوفنتوس",
    "Lazio": "لاتسيو",
    "Milan": "ميلان",
    "Napoli": "نابولي",
    "Newcastle": "نيوكاسل",
    "PSG": "باريس سان جيرمان",
    "Paris Saint-Germain": "باريس سان جيرمان",
    "Porto": "بورتو",
    "Real Betis": "ريال بيتيس",
    "Real Sociedad": "ريال سوسيداد",
    "Salzburg": "سالزبورج",
    "Sevilla": "إشبيلية",
    "Sporting CP": "سبورتنج ليشبونة",
    "Tottenham": "توتنهام",
    "Valencia": "فالنسيا",
    "Villarreal": "فياريال",
    "West Ham": "ويست هام",
    "Wolves": "ولفرهامبتون",
    # Knockout placeholders
    "Group A 2nd": "ثاني المجموعة أ",
    "Group B 2nd": "ثاني المجموعة ب",
    "Group C 2nd": "ثاني المجموعة ج",
    "Group D 2nd": "ثاني المجموعة د",
    "Group E 1st": "أول المجموعة هـ",
    "Group E 2nd": "ثاني المجموعة هـ",
    "Group F 1st": "أول المجموعة و",
    "Group F 2nd": "ثاني المجموعة و",
    "Group C 1st": "أول المجموعة ج",
    "Group A 1st": "أول المجموعة أ",
    "Group I 1st": "أول المجموعة ط",
    "Group I 2nd": "ثاني المجموعة ط",
    "Group L 1st": "أول المجموعة ل",
    "Group L 2nd": "ثاني المجموعة ل",
    "Group D 1st": "أول المجموعة د",
    "Group G 1st": "أول المجموعة ز",
    "Group G 2nd": "ثاني المجموعة ز",
    "Group K 1st": "أول المجموعة ك",
    "Group K 2nd": "ثاني المجموعة ك",
    "Group H 1st": "أول المجموعة ح",
    "Group H 2nd": "ثاني المجموعة ح",
    "Group B 1st": "أول المجموعة ب",
    "Group J 1st": "أول المجموعة ي",
    "Group J 2nd": "ثاني المجموعة ي",
    "3rd Group A/B/C/D/F": "ثالث (أ/ب/ج/د/و)",
    "3rd Group C/D/F/G/H": "ثالث (ج/د/و/ز/ح)",
    "3rd Group C/E/F/H/I": "ثالث (ج/هـ/و/ح/ط)",
    "3rd Group E/H/I/J/K": "ثالث (هـ/ح/ط/ي/ك)",
    "3rd Group B/E/F/I/J": "ثالث (ب/هـ/و/ط/ي)",
    "3rd Group A/E/H/I/J": "ثالث (أ/هـ/ح/ط/ي)",
    "3rd Group E/F/G/I/J": "ثالث (هـ/و/ز/ط/ي)",
    "3rd Group D/E/I/J/L": "ثالث (د/هـ/ط/ي/ل)",
    "Winner M73": "فائز م٧٣",
    "Winner M74": "فائز م٧٤",
    "Winner M75": "فائز م٧٥",
    "Winner M76": "فائز م٧٦",
    "Winner M77": "فائز م٧٧",
    "Winner M78": "فائز م٧٨",
    "Winner M79": "فائز م٧٩",
    "Winner M80": "فائز م٨٠",
    "Winner M81": "فائز م٨١",
    "Winner M82": "فائز م٨٢",
    "Winner M83": "فائز م٨٣",
    "Winner M84": "فائز م٨٤",
    "Winner M85": "فائز م٨٥",
    "Winner M86": "فائز م٨٦",
    "Winner M87": "فائز م٨٧",
    "Winner M88": "فائز م٨٨",
    "Winner M89": "فائز م٨٩",
    "Winner M90": "فائز م٩٠",
    "Winner M91": "فائز م٩١",
    "Winner M92": "فائز م٩٢",
    "Winner M93": "فائز م٩٣",
    "Winner M94": "فائز م٩٤",
    "Winner M95": "فائز م٩٥",
    "Winner M96": "فائز م٩٦",
    "Winner M97": "فائز م٩٧",
    "Winner M98": "فائز م٩٨",
    "Winner M99": "فائز م٩٩",
    "Winner M100": "فائز م١٠٠",
    "Winner M101": "فائز م١٠١",
    "Winner M102": "فائز م١٠٢",
    "Runner-up M101": "وصيف م١٠١",
    "Runner-up M102": "وصيف م١٠٢",
}

GROUP_EN_TO_AR: dict[str, str] = {
    "Group A": "المجموعة أ",
    "Group B": "المجموعة ب",
    "Group C": "المجموعة ج",
    "Group D": "المجموعة د",
    "Group E": "المجموعة هـ",
    "Group F": "المجموعة و",
    "Group G": "المجموعة ز",
    "Group H": "المجموعة ح",
    "Group I": "المجموعة ط",
    "Group J": "المجموعة ي",
    "Group K": "المجموعة ك",
    "Group L": "المجموعة ل",
    "Round of 32": "دور الـ32",
    "Round of 16": "دور الـ16",
    "Quarter-final": "ربع النهائي",
    "Semi-final": "نصف النهائي",
    "3rd place": "مباراة المركز الثالث",
    "Final": "النهائي",
}


def _arabic_indic_number(value: int) -> str:
    return "".join(_ARABIC_INDIC[int(digit)] for digit in str(value))


def _arabic_winner_placeholder(match_number: int) -> str:
    return f"فائز م{_arabic_indic_number(match_number)}"


def _arabic_runner_up_placeholder(match_number: int) -> str:
    return f"وصيف م{_arabic_indic_number(match_number)}"


def normalize_team_name(name: str) -> str:
    """Map English team/placeholder spellings to canonical Arabic."""
    text = name.strip()
    if not text:
        return text
    if text in TEAM_EN_TO_AR:
        return TEAM_EN_TO_AR[text]

    from worldcup_kickoffs import _EN_ALIASES

    aliased = _EN_ALIASES.get(text, text)
    if aliased in TEAM_EN_TO_AR:
        return TEAM_EN_TO_AR[aliased]

    if match := _MATCH_WINNER_EN.match(text):
        return _arabic_winner_placeholder(int(match.group(1)))
    if match := _MATCH_N_WINNER_EN.match(text):
        return _arabic_winner_placeholder(int(match.group(1)))
    if match := _WINNER_M_EN.match(text):
        return _arabic_winner_placeholder(int(match.group(1)))
    if match := _MATCH_N_LOSER_EN.match(text):
        return _arabic_runner_up_placeholder(int(match.group(1)))
    if match := _RUNNER_UP_M_EN.match(text):
        return _arabic_runner_up_placeholder(int(match.group(1)))

    return text
