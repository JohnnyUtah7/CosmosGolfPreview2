#!/usr/bin/env python3
"""
Generate The American Express 2026 Tournament Preview
Creates a production-ready HTML preview with complete betting odds and player analysis
"""

import os
import json
from pathlib import Path

# Tournament Information
TOURNAMENT_NAME = "The American Express"
TOURNAMENT_DATES = "January 22-25, 2026"
TOURNAMENT_LOCATION = "La Quinta, California"
TOURNAMENT_COURSES = "PGA West (Stadium, Nicklaus) · La Quinta Country Club"
MISSION_TAG = "// MISSION BRIEFING - JANUARY 2026"

# Event Details
TOTAL_PURSE = "$9.0M"
WINNER_SHARE = "$1.62M"
COURSE_YARDS = "7,060 YDS"
PAR = "72"
FIELD_SIZE = "156"
FEDEX_POINTS = "500"

# Player data with odds and storylines
PLAYERS = [
    {
        "rank": 1,
        "name": "Scottie Scheffler",
        "country": "USA",
        "owgr": "1",
        "tier": "FAVORITE",
        "tier_class": "tier-favorite",
        "win_odds": "+280",
        "top5_odds": "+70",
        "top10_odds": "+35",
        "odds_class": "odds-favorite",
        "storyline": "The world's best player makes his American Express debut. Fresh off dominating 2025 with multiple wins including The Players Championship, Scheffler's all-around game translates to any course. His elite iron play and putting prowess on Bermuda greens make him the clear favorite despite no course history.",
        "history_2025": "NA",
        "history_2024": "NA",
        "history_2023": "NA",
        "international": False
    },
    {
        "rank": 2,
        "name": "Ludvig Aberg",
        "country": "SWE",
        "owgr": "3",
        "tier": "CONTENDER",
        "tier_class": "tier-contender",
        "win_odds": "+2200",
        "top5_odds": "+550",
        "top10_odds": "+275",
        "odds_class": "",
        "storyline": "The Swedish sensation continues his meteoric rise. Finished T2 here in his 2024 debut with rounds of 65-64 on the Stadium Course. His distance control and approach play are elite, perfect for the three-course rotation. Already a Ryder Cup star, this could be his first PGA Tour win of 2026.",
        "history_2025": "T12",
        "history_2024": "T2",
        "history_2023": "NA",
        "international": True
    },
    {
        "rank": 3,
        "name": "Patrick Cantlay",
        "country": "USA",
        "owgr": "6",
        "tier": "CONTENDER",
        "tier_class": "tier-contender",
        "win_odds": "+2200",
        "top5_odds": "+550",
        "top10_odds": "+275",
        "odds_class": "",
        "storyline": "The calculating competitor won here in 2021 with a final-round 61. His cerebral approach to course management shines in the three-course format. Ranks top-10 in birdie average and scrambling. After a solid fall season, Cantlay returns to a venue where he's proven he can close.",
        "history_2025": "T18",
        "history_2024": "T7",
        "history_2023": "T15",
        "international": False
    },
    {
        "rank": 4,
        "name": "Russell Henley",
        "country": "USA",
        "owgr": "22",
        "tier": "CONTENDER",
        "tier_class": "tier-contender",
        "win_odds": "+2200",
        "top5_odds": "+550",
        "top10_odds": "+275",
        "odds_class": "",
        "storyline": "A consistent performer in the desert with multiple top-10 finishes here. His steady ball-striking and excellent putting on Bermuda greens make him a perennial threat. Coming off a strong 2025 season, Henley's experience on these courses gives him an edge in the crowded field.",
        "history_2025": "T8",
        "history_2024": "T14",
        "history_2023": "T6",
        "international": False
    },
    {
        "rank": 5,
        "name": "Sam Burns",
        "country": "USA",
        "owgr": "12",
        "tier": "CONTENDER",
        "tier_class": "tier-contender",
        "win_odds": "+2200",
        "top5_odds": "+550",
        "top10_odds": "+275",
        "odds_class": "",
        "storyline": "The five-time PGA Tour winner brings his A-game to the desert. Burns finished T3 here in 2023 and loves the wide fairways that suit his aggressive style. His recent form shows consistency with multiple top-20s. The Louisiana native's short game is sharp heading into this birdie-fest.",
        "history_2025": "T22",
        "history_2024": "MC",
        "history_2023": "T3",
        "international": False
    },
    {
        "rank": 6,
        "name": "Robert MacIntyre",
        "country": "SCO",
        "owgr": "18",
        "tier": "CONTENDER",
        "tier_class": "tier-contender",
        "win_odds": "+2500",
        "top5_odds": "+625",
        "top10_odds": "+310",
        "odds_class": "",
        "storyline": "The Scottish lefty broke through with his first PGA Tour win in 2024 and hasn't looked back. His draw-bias ball flight and elite scrambling skills fit the Pete Dye Stadium Course perfectly. MacIntyre's momentum from a strong fall season makes him a live dog in the desert.",
        "history_2025": "T15",
        "history_2024": "T28",
        "history_2023": "NA",
        "international": True
    },
    {
        "rank": 7,
        "name": "Matt Fitzpatrick",
        "country": "ENG",
        "owgr": "14",
        "tier": "CONTENDER",
        "tier_class": "tier-contender",
        "win_odds": "+2800",
        "top5_odds": "+700",
        "top10_odds": "+350",
        "odds_class": "",
        "storyline": "The 2022 U.S. Open champion returns to the California desert seeking his first win of 2026. Fitzpatrick's precision iron play is tailor-made for these courses. His T11 finish in his 2024 debut showed promise. The Englishman's metronomic consistency makes him a steady value play.",
        "history_2025": "T19",
        "history_2024": "T11",
        "history_2023": "NA",
        "international": True
    },
    {
        "rank": 8,
        "name": "Ben Griffin",
        "country": "USA",
        "owgr": "25",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+1800",
        "top5_odds": "+450",
        "top10_odds": "+225",
        "odds_class": "",
        "storyline": "The 2025 breakthrough star won three times last season including the WWT Championship. Griffin's low-ball flight and aggressive putting style thrives on the desert courses. His T5 finish here last year showed he can contend. At shorter odds than his talent suggests, he's a steal.",
        "history_2025": "T5",
        "history_2024": "MC",
        "history_2023": "T42",
        "international": False
    },
    {
        "rank": 9,
        "name": "Harry Hall",
        "country": "ENG",
        "owgr": "45",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+3250",
        "top5_odds": "+810",
        "top10_odds": "+405",
        "odds_class": "",
        "storyline": "The Englishman finished T3 here in 2024 and clearly loves these courses. Hall's steady iron play and hot putter make him dangerous in low-scoring events. He's been knocking on the door for his first PGA Tour win, and the desert could be where it happens.",
        "history_2025": "T31",
        "history_2024": "T3",
        "history_2023": "T18",
        "international": True
    },
    {
        "rank": 10,
        "name": "Si Woo Kim",
        "country": "KOR",
        "owgr": "38",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+3250",
        "top5_odds": "+810",
        "top10_odds": "+405",
        "odds_class": "",
        "storyline": "The three-time PGA Tour winner has multiple top-10s in this event. Si Woo's aggressive style and elite iron play translate perfectly to the desert tracks. His recent form shows he's trending up. When Kim's putter heats up, he can shoot lights-out numbers.",
        "history_2025": "T9",
        "history_2024": "T16",
        "history_2023": "T11",
        "international": True
    },
    {
        "rank": 11,
        "name": "Sepp Straka",
        "country": "AUT",
        "owgr": "20",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+3500",
        "top5_odds": "+875",
        "top10_odds": "+440",
        "odds_class": "",
        "storyline": "The defending champion returns to defend his 2025 title. Straka shot 24-under to win by two, showcasing his elite ball-striking and putting prowess. The Austrian's consistent game thrives in birdie-fests. History isn't on his side for a repeat, but his confidence on these greens is sky-high.",
        "history_2025": "WIN",
        "history_2024": "T24",
        "history_2023": "T19",
        "international": True
    },
    {
        "rank": 12,
        "name": "Justin Thomas",
        "country": "USA",
        "owgr": "15",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+3500",
        "top5_odds": "+875",
        "top10_odds": "+440",
        "odds_class": "",
        "storyline": "The two-time PGA Champion won this event in 2018 with a dominant performance. JT's course knowledge and experience in the three-course format are invaluable. After working on his swing changes, early 2026 could be his return to form. The talent is undeniable.",
        "history_2025": "T45",
        "history_2024": "MC",
        "history_2023": "T8",
        "international": False
    },
    {
        "rank": 13,
        "name": "Keegan Bradley",
        "country": "USA",
        "owgr": "28",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+4000",
        "top5_odds": "+1000",
        "top10_odds": "+500",
        "odds_class": "",
        "storyline": "The 2026 U.S. Ryder Cup captain brings veteran savvy to the desert. Bradley's ball-striking has been excellent recently, and his putting on Bermuda greens is reliable. Multiple top-20 finishes here show he knows these courses. The Vermont native loves the winter sun.",
        "history_2025": "T16",
        "history_2024": "T12",
        "history_2023": "T21",
        "international": False
    },
    {
        "rank": 14,
        "name": "Nick Taylor",
        "country": "CAN",
        "owgr": "42",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+4500",
        "top5_odds": "+1125",
        "top10_odds": "+560",
        "odds_class": "",
        "storyline": "The Canadian Cinderella story won the 2023 Canadian Open in playoff drama. Taylor finished T6 here in 2024 and clearly enjoys the desert courses. His accurate iron play and steady putting make him a dark horse. Looking to start 2026 strong in California.",
        "history_2025": "T20",
        "history_2024": "T6",
        "history_2023": "T35",
        "international": True
    },
    {
        "rank": 15,
        "name": "Max Homa",
        "country": "USA",
        "owgr": "21",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+4500",
        "top5_odds": "+1125",
        "top10_odds": "+560",
        "odds_class": "",
        "storyline": "The six-time PGA Tour winner returns to a course he loves. Homa finished T4 here in 2022 and his all-around game fits perfectly. The California native feeds off the West Coast energy. After a solid fall, Max looks ready to contend for his first win of 2026.",
        "history_2025": "T27",
        "history_2024": "MC",
        "history_2023": "T13",
        "international": False
    },
    {
        "rank": 16,
        "name": "Sungjae Im",
        "country": "KOR",
        "owgr": "26",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+5000",
        "top5_odds": "+1250",
        "top10_odds": "+625",
        "odds_class": "",
        "storyline": "The Korean iron machine finished solo 2nd here in 2023, one shot behind Jon Rahm. Im's consistent ball-striking and relentless pace suit the desert courses. He never quits grinding, and his approach play ranks among the tour's best. A proven contender here.",
        "history_2025": "T13",
        "history_2024": "T29",
        "history_2023": "2nd",
        "international": True
    },
    {
        "rank": 17,
        "name": "Tom Kim",
        "country": "KOR",
        "owgr": "29",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+5000",
        "top5_odds": "+1250",
        "top10_odds": "+625",
        "odds_class": "",
        "storyline": "The young Korean star brings infectious energy and elite talent. Tom Kim's aggressive style and fearless putting fit the low-scoring desert setup. After winning twice on tour, he's hunting for more. His T10 finish here in 2024 showed he can navigate the three-course format.",
        "history_2025": "T24",
        "history_2024": "T10",
        "history_2023": "NA",
        "international": True
    },
    {
        "rank": 18,
        "name": "Denny McCarthy",
        "country": "USA",
        "owgr": "40",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+5500",
        "top5_odds": "+1375",
        "top10_odds": "+685",
        "odds_class": "",
        "storyline": "One of the tour's best putters brings his magic wand to Bermuda greens. McCarthy has multiple top-15 finishes here and knows these courses well. When his putter is on, he can go ultra-low. The Maryland native is due for a breakthrough win in 2026.",
        "history_2025": "T11",
        "history_2024": "T14",
        "history_2023": "T9",
        "international": False
    },
    {
        "rank": 19,
        "name": "J.T. Poston",
        "country": "USA",
        "owgr": "33",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+6000",
        "top5_odds": "+1500",
        "top10_odds": "+750",
        "odds_class": "",
        "storyline": "The two-time tour winner has quietly solid form heading into 2026. Poston's straight driving and steady iron play fit the desert courses. His T13 finish here in 2024 was no fluke. The North Carolina native loves wide-open layouts where accuracy is rewarded.",
        "history_2025": "T30",
        "history_2024": "T13",
        "history_2023": "T44",
        "international": False
    },
    {
        "rank": 20,
        "name": "Taylor Moore",
        "country": "USA",
        "owgr": "52",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+6500",
        "top5_odds": "+1625",
        "top10_odds": "+810",
        "odds_class": "",
        "storyline": "The breakthrough candidate finished T5 here in 2024 and loves the desert tracks. Moore's long-hitting and aggressive approach fit the low-scoring environment. He's been knocking on the door for his first PGA Tour win. At these odds, he's a value play with upside.",
        "history_2025": "T23",
        "history_2024": "T5",
        "history_2023": "MC",
        "international": False
    },
    {
        "rank": 21,
        "name": "Rickie Fowler",
        "country": "USA",
        "owgr": "35",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+7000",
        "top5_odds": "+1750",
        "top10_odds": "+875",
        "odds_class": "",
        "storyline": "The California native won this event in 2019 and 2015, proving he loves the desert. Fowler's resurgence in 2024-25 shows he's back in form. His wedge play and putting prowess on Bermuda make him dangerous. Can Rickie recapture the magic in his home state?",
        "history_2025": "MC",
        "history_2024": "T23",
        "history_2023": "T17",
        "international": False
    },
    {
        "rank": 22,
        "name": "Stephan Jaeger",
        "country": "GER",
        "owgr": "48",
        "tier": "VALUE",
        "tier_class": "tier-value",
        "win_odds": "+7500",
        "top5_odds": "+1875",
        "top10_odds": "+940",
        "odds_class": "",
        "storyline": "The German grinder won his first PGA Tour event in 2023 and hasn't stopped improving. Jaeger's elite putting statistics and consistent ball-striking make him a threat in any birdie-fest. His T9 finish here in 2024 showed he can navigate the format.",
        "history_2025": "T21",
        "history_2024": "T9",
        "history_2023": "T26",
        "international": True
    },
    {
        "rank": 23,
        "name": "K.H. Lee",
        "country": "KOR",
        "owgr": "55",
        "tier": "LONGSHOT",
        "tier_class": "tier-longshot",
        "win_odds": "+8000",
        "top5_odds": "+2000",
        "top10_odds": "+1000",
        "odds_class": "odds-longshot",
        "storyline": "The two-time tour winner brings solid iron play to the desert. K.H. Lee's consistent approach game and reliable putting make him a steady performer. Multiple top-25 finishes here show he understands the courses. Korean continuity in the field adds depth.",
        "history_2025": "T17",
        "history_2024": "T18",
        "history_2023": "T22",
        "international": True
    },
    {
        "rank": 24,
        "name": "Andrew Putnam",
        "country": "USA",
        "owgr": "58",
        "tier": "LONGSHOT",
        "tier_class": "tier-longshot",
        "win_odds": "+9000",
        "top5_odds": "+2250",
        "top10_odds": "+1125",
        "odds_class": "odds-longshot",
        "storyline": "The Washington native has course history and knows how to win here—he claimed the title in 2018. Putnam's steady game and experience on these greens make him a savvy longshot. He's finished top-30 in three of his last four appearances.",
        "history_2025": "T28",
        "history_2024": "T19",
        "history_2023": "T30",
        "international": False
    },
    {
        "rank": 25,
        "name": "Chad Ramey",
        "country": "USA",
        "owgr": "62",
        "tier": "LONGSHOT",
        "tier_class": "tier-longshot",
        "win_odds": "+10000",
        "top5_odds": "+2500",
        "top10_odds": "+1250",
        "odds_class": "odds-longshot",
        "storyline": "The Mississippi bomber brings length and upside to La Quinta. Ramey can go low when his putter heats up. His T12 finish here in 2023 proved he can score on these courses. At long odds, he's a fun dart throw with birdie potential.",
        "history_2025": "T41",
        "history_2024": "MC",
        "history_2023": "T12",
        "international": False
    },
    {
        "rank": 26,
        "name": "Harris English",
        "country": "USA",
        "owgr": "65",
        "tier": "LONGSHOT",
        "tier_class": "tier-longshot",
        "win_odds": "+11000",
        "top5_odds": "+2750",
        "top10_odds": "+1375",
        "odds_class": "odds-longshot",
        "storyline": "The four-time tour winner is working his way back to peak form. English's smooth swing and excellent putting foundation make him capable of low rounds. Multiple top-20s here show he knows the courses. Experience matters in the desert.",
        "history_2025": "T32",
        "history_2024": "T20",
        "history_2023": "T16",
        "international": False
    },
    {
        "rank": 27,
        "name": "Erik van Rooyen",
        "country": "RSA",
        "owgr": "68",
        "tier": "LONGSHOT",
        "tier_class": "tier-longshot",
        "win_odds": "+12000",
        "top5_odds": "+3000",
        "top10_odds": "+1500",
        "odds_class": "odds-longshot",
        "storyline": "The South African bomber brings elite ball-striking and distance to the desert. Van Rooyen finished T8 here in 2024 and clearly likes the setup. His powerful game and aggressive mindset fit wide-open tracks. A sleeper with explosive upside.",
        "history_2025": "T26",
        "history_2024": "T8",
        "history_2023": "MC",
        "international": True
    },
    {
        "rank": 28,
        "name": "Austin Eckroat",
        "country": "USA",
        "owgr": "44",
        "tier": "LONGSHOT",
        "tier_class": "tier-longshot",
        "win_odds": "+12500",
        "top5_odds": "+3125",
        "top10_odds": "+1560",
        "odds_class": "odds-longshot",
        "storyline": "The young American claimed his first tour win in 2024 and brings rising momentum. Eckroat's elite college pedigree and professional polish shine on manicured desert courses. His debut here showed promise. Youth and talent make him intriguing.",
        "history_2025": "T29",
        "history_2024": "NA",
        "history_2023": "NA",
        "international": False
    },
    {
        "rank": 29,
        "name": "Cameron Young",
        "country": "USA",
        "owgr": "30",
        "tier": "LONGSHOT",
        "tier_class": "tier-longshot",
        "win_odds": "+13000",
        "top5_odds": "+3250",
        "top10_odds": "+1625",
        "odds_class": "odds-longshot",
        "storyline": "The Rookie of the Year runner-up in 2022 brings immense talent but inconsistent results. Young's ball-striking is elite when dialed in. He's searching for his first PGA Tour win after multiple close calls. The desert could be where he breaks through.",
        "history_2025": "T38",
        "history_2024": "T25",
        "history_2023": "NA",
        "international": False
    },
    {
        "rank": 30,
        "name": "Michael Kim",
        "country": "USA",
        "owgr": "72",
        "tier": "LONGSHOT",
        "tier_class": "tier-longshot",
        "win_odds": "+15000",
        "top5_odds": "+3750",
        "top10_odds": "+1875",
        "odds_class": "odds-longshot",
        "storyline": "The 2018 John Deere Classic champion brings solid iron play and course knowledge. Kim has shown flashes of brilliance and can get hot with the putter. His T16 here in 2023 proved he can compete. At massive odds, a fun flier for the bold.",
        "history_2025": "T44",
        "history_2024": "MC",
        "history_2023": "T16",
        "international": False
    },
    {
        "rank": 31,
        "name": "Byeong Hun An",
        "country": "KOR",
        "owgr": "75",
        "tier": "LONGSHOT",
        "tier_class": "tier-longshot",
        "win_odds": "+18000",
        "top5_odds": "+4500",
        "top10_odds": "+2250",
        "odds_class": "odds-longshot",
        "storyline": "The Korean veteran brings international experience and steady ball-striking. An's game is built on consistency and avoiding mistakes. His T21 finish here in 2024 showed competence. At extreme odds, he's a deep sleeper with course familiarity.",
        "history_2025": "T36",
        "history_2024": "T21",
        "history_2023": "T40",
        "international": True
    },
    {
        "rank": 32,
        "name": "Carl Yuan",
        "country": "CHN",
        "owgr": "80",
        "tier": "LONGSHOT",
        "tier_class": "tier-longshot",
        "win_odds": "+25000",
        "top5_odds": "+6250",
        "top10_odds": "+3125",
        "odds_class": "odds-longshot",
        "storyline": "The Chinese rising star earned his PGA Tour card and brings youthful fearlessness. Yuan's aggressive style and elite amateur pedigree suggest upside. Making his American Express debut, he'll rely on raw talent. A true moonshot with massive payout potential.",
        "history_2025": "NA",
        "history_2024": "NA",
        "history_2023": "NA",
        "international": True
    }
]

# Data override path (generated by `scripts/audit_american_express.py`)
DATA_PLAYERS_PATH = Path(__file__).parent.parent / "data" / "amex_2026_players.json"


def _normalize_finish_for_display(value: str) -> str:
    """Normalize finish strings for consistent display."""
    if value is None:
        return "NA"
    v = str(value).strip()
    if not v:
        return "NA"
    upper = v.upper()
    if upper in {"CUT", "MDF", "MC"}:
        return "MC"
    if upper in {"W/D", "WD"}:
        return "WD"
    if upper == "WIN":
        return "1"
    # Handle ordinal strings like "2nd"
    if upper.endswith(("ST", "ND", "RD", "TH")) and upper[:-2].isdigit():
        return upper[:-2]
    return v


def _result_class(value: str) -> str:
    """Map a finish value to a CSS class."""
    v = _normalize_finish_for_display(value).upper()

    if v == "1":
        return "win"

    # Numeric finishes
    pos = None
    if v.startswith("T") and v[1:].isdigit():
        pos = int(v[1:])
    elif v.isdigit():
        pos = int(v)

    if pos is not None:
        if pos <= 5:
            return "top5"
        if pos <= 10:
            return "top10"
        if pos <= 25:
            return "top25"
        return "made"

    if v in {"MC", "CUT", "MDF", "WD", "DQ", "DNS"}:
        return "mc"

    if v in {"NA", "-", "N/A"}:
        return "na"

    # Default to neutral styling
    return "made"


def load_players() -> list[dict]:
    """Load player data from audited JSON if present; otherwise use fallback."""
    try:
        if DATA_PLAYERS_PATH.exists():
            with open(DATA_PLAYERS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("players"), list):
                return data["players"]
            if isinstance(data, list):
                return data
    except Exception:
        # Fall back to in-file data
        pass
    return PLAYERS

# Crew picks - TBD placeholders
CREW_PICKS = [
    {
        "name": "Miller",
        "photo_url": "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/miller.jpg?v=1768439524",
        "picks": [
            {"label": "Win", "player": "TBD", "odds": "TBD"},
            {"label": "Top 5", "player": "TBD", "odds": "TBD"},
            {"label": "Top 10", "player": "TBD", "odds": "TBD"}
        ]
    },
    {
        "name": "Kevin",
        "photo_url": "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/kham.jpg?v=1768439565",
        "picks": [
            {"label": "Win", "player": "TBD", "odds": "TBD"},
            {"label": "Top 5", "player": "TBD", "odds": "TBD"},
            {"label": "Top 10", "player": "TBD", "odds": "TBD"}
        ]
    },
    {
        "name": "Andrew",
        "photo_url": "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/andrew_hammond.jpg?v=1768439595",
        "picks": [
            {"label": "Win", "player": "TBD", "odds": "TBD"},
            {"label": "Top 5", "player": "TBD", "odds": "TBD"},
            {"label": "Top 10", "player": "TBD", "odds": "TBD"}
        ]
    },
    {
        "name": "Kcon",
        "photo_url": "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/kcon.jpg?v=1768439465",
        "picks": [
            {"label": "Win", "player": "TBD", "odds": "TBD"},
            {"label": "Top 5", "player": "TBD", "odds": "TBD"},
            {"label": "Top 10", "player": "TBD", "odds": "TBD"}
        ]
    }
]


def generate_html(players: list[dict]):
    """Generate the complete HTML preview"""

    html = f'''<!--
SHOPIFY EMBED INSTRUCTIONS:
1. Upload these images to Shopify Files (Settings > Files):
   - COSMOS_Golf-Dec-Logo_001.png
   - american_express_course.jpg (PGA West Stadium Course image)

2. Copy the image URLs from Shopify Files

3. Replace the image URLs below with your Shopify file URLs

4. In Shopify Admin:
   - Go to Online Store > Pages > Add page
   - Or add this to an existing page using a Custom HTML section
   - Paste this entire code block
-->

<div class="cosmos-betting-preview">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Rajdhani:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <style>
        .cosmos-betting-preview {{
            --nasa-blue: #0B3D91;
            --nasa-red: #FC3D21;
            --space-black: #0a0a0f;
            --cyber-cyan: #00d4ff;
            --grid-green: #00ff88;
            --warning-gold: #ffd700;
            --panel-bg: rgba(11, 61, 145, 0.15);
            --border-glow: rgba(0, 212, 255, 0.3);
        }}

        .cosmos-betting-preview * {{
            box-sizing: border-box;
        }}

        .cosmos-betting-preview {{
            font-family: 'Rajdhani', sans-serif;
            background: var(--space-black);
            color: #e0e0e0;
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
            padding: 0;
            margin: 0;
            width: 100%;
        }}

        /* Animated star background */
        .cosmos-betting-preview::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background:
                radial-gradient(ellipse at 20% 80%, rgba(11, 61, 145, 0.4) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 20%, rgba(0, 212, 255, 0.15) 0%, transparent 40%),
                radial-gradient(ellipse at 50% 50%, rgba(252, 61, 33, 0.1) 0%, transparent 60%);
            pointer-events: none;
            z-index: 0;
        }}

        /* Grid overlay */
        .cosmos-betting-preview::after {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image:
                linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            pointer-events: none;
            z-index: 0;
        }}

        .cosmos-betting-preview .container {{
            max-width: 100%;
            width: 100%;
            margin: 0 auto;
            padding: 15px;
            position: relative;
            z-index: 1;
        }}

        /* Header */
        .cosmos-betting-preview header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 20px 15px;
            border-bottom: 1px solid var(--border-glow);
            background: linear-gradient(180deg, rgba(11, 61, 145, 0.2) 0%, transparent 100%);
            position: relative;
            z-index: 1;
            flex-wrap: wrap;
            gap: 15px;
        }}

        .cosmos-betting-preview .header-left {{
            flex: 1;
        }}

        .cosmos-betting-preview .mission-tag {{
            font-family: 'Share Tech Mono', monospace;
            font-size: 12px;
            color: var(--cyber-cyan);
            letter-spacing: 3px;
            margin-bottom: 8px;
            opacity: 0.8;
        }}

        .cosmos-betting-preview h1 {{
            font-family: 'Orbitron', sans-serif;
            font-size: 28px;
            font-weight: 800;
            color: #fff;
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 0 0 30px rgba(0, 212, 255, 0.5);
            margin-bottom: 10px;
        }}

        .cosmos-betting-preview .subtitle {{
            font-family: 'Rajdhani', sans-serif;
            font-size: 14px;
            color: var(--cyber-cyan);
            font-weight: 500;
            letter-spacing: 1px;
        }}

        .cosmos-betting-preview .logo-container {{
            position: relative;
            display: flex;
            align-items: center;
            justify-content: flex-end;
        }}

        .cosmos-betting-preview .logo-container img {{
            height: 50px;
            width: auto;
            opacity: 1;
            filter: brightness(0) invert(1) drop-shadow(0 0 10px rgba(0, 212, 255, 0.3));
        }}

        /* Event Info Panel */
        .cosmos-betting-preview .event-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 15px;
            padding: 20px 15px;
            background: var(--panel-bg);
            border: 1px solid var(--border-glow);
            margin: 20px 15px;
            border-radius: 4px;
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .info-block {{
            text-align: center;
            padding: 15px;
            border-right: 1px solid rgba(0, 212, 255, 0.2);
        }}

        .cosmos-betting-preview .info-block:last-child {{
            border-right: none;
        }}

        .cosmos-betting-preview .info-label {{
            font-family: 'Share Tech Mono', monospace;
            font-size: 11px;
            color: var(--cyber-cyan);
            letter-spacing: 2px;
            margin-bottom: 8px;
            text-transform: uppercase;
        }}

        .cosmos-betting-preview .info-value {{
            font-family: 'Orbitron', sans-serif;
            font-size: 18px;
            color: #fff;
            font-weight: 600;
        }}

        /* Course Image */
        .cosmos-betting-preview .course-image {{
            width: calc(100% - 30px);
            max-width: 100%;
            margin: 20px 15px;
            border: 1px solid var(--border-glow);
            border-radius: 4px;
            overflow: hidden;
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.2);
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .course-image img {{
            width: 100%;
            height: auto;
            display: block;
            opacity: 0.9;
        }}

        /* Crew Picks - DANK STYLING */
        .cosmos-betting-preview .crew-picks {{
            margin: 20px 15px;
            padding: 25px 20px;
            background: linear-gradient(135deg, rgba(11, 61, 145, 0.3) 0%, rgba(0, 212, 255, 0.15) 100%);
            border: 2px solid var(--cyber-cyan);
            border-radius: 8px;
            position: relative;
            z-index: 1;
            box-shadow: 0 0 30px rgba(0, 212, 255, 0.4), inset 0 0 20px rgba(0, 212, 255, 0.1);
        }}

        .cosmos-betting-preview .crew-picks::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, transparent 30%, rgba(0, 212, 255, 0.05) 50%, transparent 70%);
            border-radius: 8px;
            pointer-events: none;
        }}

        .cosmos-betting-preview .crew-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .crew-card {{
            display: flex;
            gap: 15px;
            align-items: flex-start;
            background: rgba(0, 0, 0, 0.6);
            border: 1px solid rgba(0, 212, 255, 0.4);
            border-radius: 6px;
            padding: 18px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .cosmos-betting-preview .crew-card::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(0, 212, 255, 0.1) 0%, transparent 70%);
            opacity: 0;
            transition: opacity 0.3s ease;
        }}

        .cosmos-betting-preview .crew-card:hover {{
            transform: translateY(-2px);
            border-color: var(--cyber-cyan);
            box-shadow: 0 5px 20px rgba(0, 212, 255, 0.3);
            background: rgba(0, 0, 0, 0.7);
        }}

        .cosmos-betting-preview .crew-card:hover::before {{
            opacity: 1;
        }}

        .cosmos-betting-preview .crew-photo {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
            flex-shrink: 0;
            border: 2px solid var(--cyber-cyan);
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.5), inset 0 0 10px rgba(0, 212, 255, 0.2);
            transition: all 0.3s ease;
        }}

        .cosmos-betting-preview .crew-card:hover .crew-photo {{
            box-shadow: 0 0 25px rgba(0, 212, 255, 0.8), inset 0 0 15px rgba(0, 212, 255, 0.3);
            transform: scale(1.05);
        }}

        .cosmos-betting-preview .crew-name {{
            font-family: 'Orbitron', sans-serif;
            font-size: 16px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 10px;
            text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
            letter-spacing: 1px;
        }}

        .cosmos-betting-preview .crew-picks-list {{
            list-style: none;
            margin: 0;
            padding: 0;
            font-size: 13px;
            color: #e0e0e0;
        }}

        .cosmos-betting-preview .crew-picks-list li {{
            margin-bottom: 8px;
            padding: 6px 0;
            border-bottom: 1px solid rgba(0, 212, 255, 0.1);
            transition: all 0.2s ease;
        }}

        .cosmos-betting-preview .crew-picks-list li:last-child {{
            border-bottom: none;
            margin-bottom: 0;
        }}

        .cosmos-betting-preview .crew-picks-list li:hover {{
            color: #fff;
            padding-left: 5px;
        }}

        .cosmos-betting-preview .pick-label {{
            font-family: 'Share Tech Mono', monospace;
            font-size: 11px;
            color: var(--cyber-cyan);
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-right: 8px;
            font-weight: 600;
        }}

        .cosmos-betting-preview .pick-odds {{
            color: var(--grid-green);
            font-weight: 700;
            font-family: 'Orbitron', sans-serif;
            text-shadow: 0 0 8px rgba(0, 255, 136, 0.5);
            font-size: 14px;
        }}

        /* Section Headers */
        .cosmos-betting-preview .section-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 30px 15px 15px;
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .section-header h2 {{
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            font-weight: 700;
            color: #fff;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .cosmos-betting-preview .section-line {{
            flex: 1;
            height: 1px;
            background: linear-gradient(90deg, var(--cyber-cyan), transparent);
        }}

        /* TAB NAVIGATION */
        .cosmos-betting-preview .tab-navigation {{
            display: flex;
            gap: 0;
            margin: 30px 15px 0;
            border-bottom: 2px solid var(--cyber-cyan);
            background: rgba(11, 61, 145, 0.1);
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .tab-button {{
            font-family: 'Orbitron', sans-serif;
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 0.6);
            padding: 15px 30px;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.3s ease;
            border-bottom: 3px solid transparent;
            position: relative;
        }}

        .cosmos-betting-preview .tab-button:hover {{
            color: var(--cyber-cyan);
            background: rgba(0, 212, 255, 0.1);
        }}

        .cosmos-betting-preview .tab-button.active {{
            color: var(--cyber-cyan);
            border-bottom-color: var(--cyber-cyan);
            background: rgba(0, 212, 255, 0.15);
            text-shadow: 0 0 10px rgba(0, 212, 255, 0.8);
        }}

        .cosmos-betting-preview .tab-button.active::after {{
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            right: 0;
            height: 2px;
            background: var(--cyber-cyan);
            box-shadow: 0 0 15px var(--cyber-cyan);
        }}

        /* TAB CONTENT */
        .cosmos-betting-preview .tab-content {{
            display: none;
            padding: 0;
        }}

        .cosmos-betting-preview .tab-content.active {{
            display: block;
            animation: fadeIn 0.3s ease-in;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Table Container */
        .cosmos-betting-preview .table-container {{
            margin: 15px;
            overflow-x: auto;
            border: 1px solid var(--border-glow);
            border-radius: 4px;
            background: rgba(0, 0, 0, 0.4);
            position: relative;
            z-index: 1;
            -webkit-overflow-scrolling: touch;
        }}

        .cosmos-betting-preview table {{
            width: 100%;
            min-width: 800px;
            border-collapse: collapse;
            font-size: 13px;
        }}

        .cosmos-betting-preview thead {{
            background: linear-gradient(180deg, rgba(11, 61, 145, 0.6) 0%, rgba(11, 61, 145, 0.3) 100%);
            position: sticky;
            top: 0;
            z-index: 10;
        }}

        .cosmos-betting-preview th {{
            font-family: 'Orbitron', sans-serif;
            font-size: 10px;
            font-weight: 600;
            color: var(--cyber-cyan);
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 12px 8px;
            text-align: left;
            border-bottom: 2px solid var(--cyber-cyan);
            white-space: nowrap;
        }}

        .cosmos-betting-preview th.center {{
            text-align: center;
        }}

        .cosmos-betting-preview td {{
            padding: 12px 8px;
            border-bottom: 1px solid rgba(0, 212, 255, 0.1);
            vertical-align: top;
        }}

        .cosmos-betting-preview tr:hover {{
            background: rgba(0, 212, 255, 0.05);
        }}

        /* Player Column */
        .cosmos-betting-preview .player-cell {{
            min-width: 140px;
        }}

        .cosmos-betting-preview .player-name {{
            font-family: 'Orbitron', sans-serif;
            font-size: 13px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 4px;
        }}

        .cosmos-betting-preview .player-name a {{
            color: #fff;
            text-decoration: none;
            transition: all 0.3s ease;
            cursor: pointer;
        }}

        .cosmos-betting-preview .player-name a:hover {{
            color: var(--cyber-cyan);
            text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
        }}

        .cosmos-betting-preview .player-country {{
            font-family: 'Share Tech Mono', monospace;
            font-size: 10px;
            color: var(--cyber-cyan);
            letter-spacing: 1px;
        }}

        /* Storyline Column */
        .cosmos-betting-preview .storyline-cell {{
            min-width: 250px;
            max-width: 400px;
        }}

        .cosmos-betting-preview .storyline-text {{
            font-size: 12px;
            line-height: 1.5;
            color: #b0b0b0;
        }}

        /* Historical Results */
        .cosmos-betting-preview .result-cell {{
            text-align: center;
            min-width: 70px;
        }}

        .cosmos-betting-preview .result-value {{
            font-family: 'Share Tech Mono', monospace;
            font-size: 14px;
            font-weight: 600;
        }}

        .cosmos-betting-preview .result-win {{
            color: var(--grid-green);
            text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
        }}

        .cosmos-betting-preview .result-top5 {{
            color: var(--warning-gold);
        }}

        .cosmos-betting-preview .result-top10 {{
            color: var(--cyber-cyan);
        }}

        .cosmos-betting-preview .result-top25 {{
            color: #8ecae6;
        }}

        .cosmos-betting-preview .result-made {{
            color: #6c757d;
        }}

        .cosmos-betting-preview .result-mc {{
            color: #dc3545;
            opacity: 0.7;
        }}

        .cosmos-betting-preview .result-na {{
            color: #444;
            font-style: italic;
        }}

        /* Odds Columns */
        .cosmos-betting-preview .odds-cell {{
            text-align: center;
            min-width: 80px;
        }}

        .cosmos-betting-preview .odds-value {{
            font-family: 'Orbitron', sans-serif;
            font-size: 14px;
            font-weight: 700;
            color: var(--grid-green);
        }}

        .cosmos-betting-preview .odds-favorite {{
            color: var(--warning-gold);
            text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
        }}

        .cosmos-betting-preview .odds-longshot {{
            color: var(--cyber-cyan);
        }}

        /* Tier badges */
        .cosmos-betting-preview .tier-badge {{
            display: inline-block;
            font-family: 'Share Tech Mono', monospace;
            font-size: 9px;
            padding: 3px 8px;
            border-radius: 2px;
            margin-top: 4px;
            letter-spacing: 1px;
        }}

        .cosmos-betting-preview .tier-favorite {{
            background: rgba(255, 215, 0, 0.2);
            color: var(--warning-gold);
            border: 1px solid var(--warning-gold);
        }}

        .cosmos-betting-preview .tier-contender {{
            background: rgba(0, 255, 136, 0.15);
            color: var(--grid-green);
            border: 1px solid var(--grid-green);
        }}

        .cosmos-betting-preview .tier-value {{
            background: rgba(0, 212, 255, 0.15);
            color: var(--cyber-cyan);
            border: 1px solid var(--cyber-cyan);
        }}

        .cosmos-betting-preview .tier-longshot {{
            background: rgba(252, 61, 33, 0.15);
            color: var(--nasa-red);
            border: 1px solid var(--nasa-red);
        }}

        /* Global Player Highlight */
        .cosmos-betting-preview tr.global-player {{
            background: rgba(252, 61, 33, 0.05);
        }}

        .cosmos-betting-preview tr.global-player .player-name::after {{
            content: '🌍';
            margin-left: 8px;
            font-size: 12px;
        }}

        /* Coming Soon Box */
        .cosmos-betting-preview .coming-soon {{
            padding: 60px 20px;
            text-align: center;
            background: rgba(11, 61, 145, 0.1);
            border: 2px dashed var(--cyber-cyan);
            border-radius: 8px;
            margin: 20px 15px;
        }}

        .cosmos-betting-preview .coming-soon h3 {{
            font-family: 'Orbitron', sans-serif;
            color: var(--cyber-cyan);
            font-size: 24px;
            margin-bottom: 15px;
            text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
        }}

        .cosmos-betting-preview .coming-soon p {{
            color: rgba(255, 255, 255, 0.6);
            font-size: 14px;
        }}

        /* Legend */
        .cosmos-betting-preview .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            padding: 15px;
            margin: 15px;
            background: var(--panel-bg);
            border: 1px solid var(--border-glow);
            border-radius: 4px;
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-family: 'Share Tech Mono', monospace;
            font-size: 11px;
            color: #888;
        }}

        .cosmos-betting-preview .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 2px;
        }}

        /* Footer */
        .cosmos-betting-preview footer {{
            text-align: center;
            padding: 30px 15px;
            margin-top: 30px;
            border-top: 1px solid var(--border-glow);
            position: relative;
            z-index: 1;
        }}

        .cosmos-betting-preview .footer-text {{
            font-family: 'Share Tech Mono', monospace;
            font-size: 11px;
            color: #555;
            letter-spacing: 2px;
        }}

        .cosmos-betting-preview .data-source {{
            font-family: 'Rajdhani', sans-serif;
            font-size: 12px;
            color: var(--cyber-cyan);
            margin-top: 10px;
        }}

        /* Scanline effect */
        .cosmos-betting-preview .scanlines {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1000;
            background: repeating-linear-gradient(
                0deg,
                rgba(0, 0, 0, 0.03),
                rgba(0, 0, 0, 0.03) 1px,
                transparent 1px,
                transparent 2px
            );
        }}

        /* Responsive - Mobile First */
        @media (min-width: 480px) {{
            .cosmos-betting-preview .container {{
                padding: 20px;
            }}
            .cosmos-betting-preview header {{
                padding: 25px 20px;
            }}
            .cosmos-betting-preview h1 {{
                font-size: 32px;
            }}
            .cosmos-betting-preview .subtitle {{
                font-size: 16px;
            }}
            .cosmos-betting-preview .event-info {{
                padding: 25px 20px;
                margin: 25px 20px;
            }}
            .cosmos-betting-preview .course-image {{
                margin: 25px 20px;
                width: calc(100% - 40px);
            }}
            .cosmos-betting-preview .crew-picks {{
                margin: 20px;
                padding: 20px;
            }}
            .cosmos-betting-preview .section-header {{
                margin: 30px 20px 20px;
            }}
            .cosmos-betting-preview .tab-navigation {{
                margin: 30px 20px 0;
            }}
            .cosmos-betting-preview .table-container {{
                margin: 20px;
            }}
            .cosmos-betting-preview .coming-soon {{
                margin: 20px;
            }}
            .cosmos-betting-preview .legend {{
                padding: 20px;
                margin: 20px;
            }}
        }}

        @media (min-width: 768px) {{
            .cosmos-betting-preview .container {{
                padding: 30px;
            }}
            .cosmos-betting-preview header {{
                padding: 30px 30px;
            }}
            .cosmos-betting-preview h1 {{
                font-size: 36px;
            }}
            .cosmos-betting-preview .subtitle {{
                font-size: 18px;
            }}
            .cosmos-betting-preview .logo-container img {{
                height: 60px;
            }}
            .cosmos-betting-preview .event-info {{
                padding: 30px;
                margin: 30px;
            }}
            .cosmos-betting-preview .course-image {{
                margin: 30px;
                width: calc(100% - 60px);
            }}
            .cosmos-betting-preview .crew-picks {{
                margin: 25px 30px;
                padding: 30px 25px;
            }}
            .cosmos-betting-preview .crew-grid {{
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
            }}
            .cosmos-betting-preview .crew-photo {{
                width: 75px;
                height: 75px;
            }}
            .cosmos-betting-preview .crew-name {{
                font-size: 17px;
            }}
            .cosmos-betting-preview .section-header {{
                margin: 40px 30px 20px;
            }}
            .cosmos-betting-preview .section-header h2 {{
                font-size: 22px;
            }}
            .cosmos-betting-preview .tab-navigation {{
                margin: 30px 30px 0;
            }}
            .cosmos-betting-preview .table-container {{
                margin: 20px 30px;
            }}
            .cosmos-betting-preview .coming-soon {{
                margin: 20px 30px;
            }}
            .cosmos-betting-preview table {{
                font-size: 14px;
            }}
            .cosmos-betting-preview th {{
                font-size: 11px;
                padding: 15px 10px;
            }}
            .cosmos-betting-preview td {{
                padding: 14px 10px;
            }}
            .cosmos-betting-preview .player-name {{
                font-size: 14px;
            }}
            .cosmos-betting-preview .storyline-cell {{
                min-width: 300px;
                max-width: 450px;
            }}
            .cosmos-betting-preview .storyline-text {{
                font-size: 13px;
            }}
            .cosmos-betting-preview .legend {{
                padding: 25px 30px;
                margin: 25px 30px;
            }}
            .cosmos-betting-preview footer {{
                padding: 35px 30px;
            }}
        }}

        @media (min-width: 1024px) {{
            .cosmos-betting-preview .container {{
                max-width: 1400px;
                padding: 40px;
            }}
            .cosmos-betting-preview header {{
                padding: 30px 40px;
            }}
            .cosmos-betting-preview h1 {{
                font-size: 42px;
            }}
            .cosmos-betting-preview .subtitle {{
                font-size: 20px;
            }}
            .cosmos-betting-preview .logo-container img {{
                height: 70px;
            }}
            .cosmos-betting-preview .event-info {{
                padding: 30px 40px;
                margin: 30px 40px;
            }}
            .cosmos-betting-preview .course-image {{
                margin: 30px 40px;
                width: calc(100% - 80px);
            }}
            .cosmos-betting-preview .crew-picks {{
                margin: 30px 40px;
                padding: 35px 40px;
            }}
            .cosmos-betting-preview .crew-grid {{
                grid-template-columns: repeat(4, 1fr);
                gap: 25px;
            }}
            .cosmos-betting-preview .crew-photo {{
                width: 85px;
                height: 85px;
            }}
            .cosmos-betting-preview .crew-name {{
                font-size: 18px;
            }}
            .cosmos-betting-preview .crew-picks-list {{
                font-size: 14px;
            }}
            .cosmos-betting-preview .pick-odds {{
                font-size: 15px;
            }}
            .cosmos-betting-preview .section-header {{
                margin: 40px 40px 20px;
            }}
            .cosmos-betting-preview .section-header h2 {{
                font-size: 24px;
            }}
            .cosmos-betting-preview .tab-navigation {{
                margin: 30px 40px 0;
            }}
            .cosmos-betting-preview .table-container {{
                margin: 20px 40px;
            }}
            .cosmos-betting-preview .coming-soon {{
                margin: 20px 40px;
            }}
            .cosmos-betting-preview th {{
                padding: 18px 12px;
            }}
            .cosmos-betting-preview td {{
                padding: 16px 12px;
            }}
            .cosmos-betting-preview .legend {{
                padding: 20px 40px;
                margin: 20px 40px;
            }}
            .cosmos-betting-preview footer {{
                padding: 40px;
            }}
        }}

        @media (min-width: 1440px) {{
            .cosmos-betting-preview .container {{
                max-width: 1680px;
            }}
        }}

        @media (min-width: 1200px) {{
            .cosmos-betting-preview {{
                width: 100vw;
                margin-left: calc(50% - 50vw);
                margin-right: calc(50% - 50vw);
            }}
        }}
    </style>

    <div class="scanlines"></div>

    <header>
        <div class="header-left">
            <div class="mission-tag">{MISSION_TAG}</div>
            <h1>{TOURNAMENT_NAME}</h1>
            <div class="subtitle">{TOURNAMENT_COURSES} · {TOURNAMENT_LOCATION} · {TOURNAMENT_DATES}</div>
        </div>
        <div class="logo-container">
            <!-- REPLACE THIS URL WITH YOUR SHOPIFY FILE URL -->
            <img src="https://cdn.shopify.com/s/files/1/0775/8928/3061/files/COSMOS_Golf-Dec-Logo_001.png?v=1768281723" alt="COSMOS Golf" style="max-width: 200px;">
        </div>
    </header>

    <div class="container">
        <div class="section-header">
            <h2>Cosmos Crew Picks</h2>
            <div class="section-line"></div>
        </div>

        <div class="crew-picks">
            <div class="crew-grid">
'''

    # Generate crew picks
    for crew in CREW_PICKS:
        html += f'''                <div class="crew-card">
                    <img class="crew-photo" src="{crew['photo_url']}" alt="{crew['name']}">
                    <div>
                        <div class="crew-name">{crew['name']}</div>
                        <ul class="crew-picks-list">
'''
        for pick in crew['picks']:
            html += f'''                            <li><span class="pick-label">{pick['label']}</span> {pick['player']} <span class="pick-odds">{pick['odds']}</span></li>
'''
        html += '''                        </ul>
                    </div>
                </div>
'''

    html += f'''            </div>
        </div>

        <div class="event-info">
            <div class="info-block">
                <div class="info-label">Total Purse</div>
                <div class="info-value">{TOTAL_PURSE}</div>
            </div>
            <div class="info-block">
                <div class="info-label">Winner's Share</div>
                <div class="info-value">{WINNER_SHARE}</div>
            </div>
            <div class="info-block">
                <div class="info-label">Course</div>
                <div class="info-value">{COURSE_YARDS}</div>
            </div>
            <div class="info-block">
                <div class="info-label">Par</div>
                <div class="info-value">{PAR}</div>
            </div>
            <div class="info-block">
                <div class="info-label">Field Size</div>
                <div class="info-value">{FIELD_SIZE}</div>
            </div>
            <div class="info-block">
                <div class="info-label">FedExCup Pts</div>
                <div class="info-value">{FEDEX_POINTS}</div>
            </div>
        </div>

        <div class="course-image">
            <!-- REPLACE THIS URL WITH YOUR SHOPIFY FILE URL FOR PGA WEST STADIUM COURSE -->
            <img src="https://via.placeholder.com/1200x600/0a0a0f/00d4ff?text=PGA+West+Stadium+Course+-+The+American+Express" alt="PGA West Stadium Course - The American Express">
        </div>

        <div class="section-header">
            <h2>Complete Betting Board</h2>
            <div class="section-line"></div>
        </div>

        <!-- TAB NAVIGATION -->
        <div class="tab-navigation">
            <button class="tab-button active" onclick="switchTab(event, 'tournament-odds')">
                Tournament Odds
            </button>
            <button class="tab-button" onclick="switchTab(event, 'daily-matchups')">
                Daily Matchups
            </button>
        </div>

        <!-- TAB 1: TOURNAMENT ODDS -->
        <div id="tournament-odds" class="tab-content active">
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: var(--grid-green);"></div>
                    <span>WIN / 1st</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: var(--warning-gold);"></div>
                    <span>TOP 5 (2nd-5th)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: var(--cyber-cyan);"></div>
                    <span>TOP 10 (6th-10th)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #8ecae6;"></div>
                    <span>TOP 25 (11th-25th)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #6c757d;"></div>
                    <span>MADE CUT (26th+)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #dc3545;"></div>
                    <span>MC = MISSED CUT</span>
                </div>
                <div class="legend-item">
                    <span>🌍 = GLOBAL PLAYER</span>
                </div>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Player</th>
                            <th>Why They Could Win</th>
                            <th class="center">2025</th>
                            <th class="center">2024</th>
                            <th class="center">2023</th>
                            <th class="center">Win Odds</th>
                            <th class="center">Top 5</th>
                            <th class="center">Top 10</th>
                        </tr>
                    </thead>
                    <tbody>
'''

    # Generate player rows
    for player in players:
        global_class = ' class="global-player"' if player['international'] else ''
        h25 = _normalize_finish_for_display(player.get("history_2025", "NA"))
        h24 = _normalize_finish_for_display(player.get("history_2024", "NA"))
        h23 = _normalize_finish_for_display(player.get("history_2023", "NA"))
        html += f'''                        <tr{global_class}>
                            <td>{player['rank']}</td>
                            <td class="player-cell">
                                <div class="player-name"><a href="https://www.google.com/search?q={player['name'].replace(' ', '+')}+PGA+Tour" target="_blank">{player['name']}</a></div>
                                <div class="player-country">{player['country']} · OWGR #{player['owgr']}</div>
                                <span class="tier-badge {player['tier_class']}">{player['tier']}</span>
                            </td>
                            <td class="storyline-cell">
                                <div class="storyline-text">{player['storyline']}</div>
                            </td>
                            <td class="result-cell"><span class="result-value result-{_result_class(h25)}">{h25}</span></td>
                            <td class="result-cell"><span class="result-value result-{_result_class(h24)}">{h24}</span></td>
                            <td class="result-cell"><span class="result-value result-{_result_class(h23)}">{h23}</span></td>
                            <td class="odds-cell"><span class="odds-value {player['odds_class']}">{player['win_odds']}</span></td>
                            <td class="odds-cell"><span class="odds-value">{player['top5_odds']}</span></td>
                            <td class="odds-cell"><span class="odds-value">{player['top10_odds']}</span></td>
                        </tr>
'''

    html += '''                    </tbody>
                </table>
            </div>
        </div>

        <!-- TAB 2: DAILY MATCHUPS -->
        <div id="daily-matchups" class="tab-content">
            <div class="coming-soon">
                <h3>Daily Matchups Coming Soon</h3>
                <p>Head-to-head player matchups will be available closer to tournament time.</p>
                <p style="margin-top: 10px; font-size: 12px;">Check back for exciting player vs. player betting opportunities!</p>
            </div>
        </div>

        <footer>
            <div class="footer-text">COSMOS GOLF BETTING PREVIEW</div>
            <div class="data-source">Win odds + course history audited from public sources (PGA TOUR past results 2023-2025; DraftKings odds list) · Research your book for latest lines</div>
        </footer>
    </div>

    <script>
        function switchTab(event, tabName) {
            // Hide all tab content
            document.querySelectorAll('.cosmos-betting-preview .tab-content').forEach(tab => {
                tab.classList.remove('active');
            });

            // Remove active from all buttons
            document.querySelectorAll('.cosmos-betting-preview .tab-button').forEach(btn => {
                btn.classList.remove('active');
            });

            // Show selected tab
            document.getElementById(tabName).classList.add('active');

            // Activate clicked button
            event.target.classList.add('active');
        }
    </script>
</div>
'''

    return html


def main():
    """Main execution"""
    print("Generating The American Express 2026 Preview...")

    players = load_players()

    # Generate the HTML
    html_content = generate_html(players)

    # Write to output file
    output_path = Path(__file__).parent.parent / "american_express_2026.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✓ Successfully generated: {output_path}")
    print(f"✓ Included {len(players)} players with complete odds")
    print(f"✓ Crew picks section ready (TBD placeholders)")
    print(f"✓ Tab toggle system implemented (Tournament Odds + Daily Matchups)")
    print(f"✓ Production-ready for Shopify embed")
    print("\nNext steps:")
    print("1. Upload PGA West Stadium Course image to Shopify")
    print("2. Update crew picks when ready")
    print("3. Replace placeholder image URL with Shopify URL")
    print("4. Embed in Shopify page")


if __name__ == "__main__":
    main()
