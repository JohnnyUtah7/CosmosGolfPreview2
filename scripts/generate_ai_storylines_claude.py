#!/usr/bin/env python3
"""
Generate AI-powered storylines using Claude API.

This script feeds Claude rich per-player data (odds, SG breakdown, model predictions,
course fit, historical finishes, recent form) and gets back creative, varied,
bettor-focused "Why They Could Win" storylines.

Usage:
    python scripts/generate_ai_storylines_claude.py --tournament "THE PLAYERS Championship" --year 2026
    python scripts/generate_ai_storylines_claude.py --tournament "THE PLAYERS Championship" --year 2026 --force
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent

from dotenv import load_dotenv
load_dotenv()


def _slugify(name: str) -> str:
    """Convert tournament name to slug."""
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _build_champions_facts(slug: str, year: int) -> str:
    """Authoritative past winners from result caches → a FACTS block for the prompt.

    Keeps the model from mislabeling the defending champ or inventing a title.
    Returns "" if no caches are available.
    """
    cache_dir = ROOT / "data" / "tournament_results_cache"
    winners = {}
    for f in sorted(cache_dir.glob(f"{slug}_*.json")):
        m = re.search(rf"{re.escape(slug)}_(\d{{4}})\.json$", f.name)
        if not m:
            continue
        y = int(m.group(1))
        try:
            res = json.loads(f.read_text(encoding="utf-8")).get("results", {})
        except Exception:
            continue
        w = next((nm for nm, fin in res.items() if str(fin).replace("T", "").strip() == "1"), None)
        if w:
            # cache names may be "Last, First"
            if "," in w:
                a, b = [x.strip() for x in w.split(",", 1)]
                w = f"{b} {a}"
            winners[y] = w
    if not winners:
        return ""
    prior = sorted([y for y in winners if y < year])
    lines = ["FACTS — past champions of THIS event (the ONLY valid 'champion'/'winner here' claims):"]
    for y in sorted(winners, reverse=True):
        tag = "  <-- DEFENDING CHAMPION" if (prior and y == prior[-1]) else ""
        lines.append(f"  {y}: {winners[y]}{tag}")
    lines.append("Do NOT call anyone else a champion/defending champion of this event.\n")
    return "\n".join(lines)


def _format_odds(odds) -> str:
    if odds is None:
        return "N/A"
    try:
        v = int(odds)
        return f"+{v}" if v > 0 else str(v)
    except Exception:
        return str(odds)


def _infer_tier(odds) -> str:
    try:
        v = int(odds)
    except Exception:
        return "longshot"
    if v <= 800:
        return "favorite"
    if v <= 2000:
        return "contender"
    if v <= 5000:
        return "value"
    return "longshot"


def build_rich_player_context(player_name: str, data: dict, recent_form_data: dict) -> str:
    """Build a rich context string for a single player with ALL available data."""
    lines = [f"PLAYER: {player_name}"]

    # Odds
    odds_data = data.get("odds", {}).get(player_name, {})
    win_odds = odds_data.get("odds")
    tier = _infer_tier(win_odds)
    lines.append(f"  Tier: {tier.upper()}")
    lines.append(f"  Win: {_format_odds(win_odds)} | Top 5: {_format_odds(odds_data.get('top5'))} | Top 10: {_format_odds(odds_data.get('top10'))}")

    # Player info
    player_info = data.get("players", {}).get(player_name, {})
    owgr = player_info.get("owgr", "—")
    country = player_info.get("country", "—")
    lines.append(f"  OWGR: #{owgr} | Country: {country}")

    # Historical finishes at THIS event. Be explicit when there are none so the
    # model never invents a finish/championship (a real failure mode).
    hist = data.get("historical", {}).get(player_name, {})
    hist_parts = []
    has_any = False
    for yr in ["2025", "2024", "2023"]:
        val = hist.get(yr, "—")
        if val not in ("—", "", None):
            has_any = True
            tag = " (WON)" if str(val).replace("T", "").strip() == "1" else ""
            hist_parts.append(f"'{yr[-2:]}: {val}{tag}")
        else:
            hist_parts.append(f"'{yr[-2:]}: did not play")
    if has_any:
        lines.append(f"  Course History at THIS event (only these are real): {' | '.join(hist_parts)}")
    else:
        lines.append("  Course History at THIS event: NO PRIOR STARTS — do NOT claim any finish or title here")

    # DataGolf model data (SG + predictions + course fit)
    dg = data.get("datagolf", {}).get(player_name, {})
    if dg:
        sg_total = dg.get("sg_total", "—")
        sg_ott = dg.get("sg_ott", "—")
        sg_app = dg.get("sg_app", "—")
        sg_arg = dg.get("sg_arg", "—")
        sg_putt = dg.get("sg_putt", "—")
        lines.append(f"  SG Total: {sg_total} | OTT: {sg_ott} | Approach: {sg_app} | Around Green: {sg_arg} | Putting: {sg_putt}")

        win_prob = dg.get("win_prob", "—")
        t10_prob = dg.get("top_10_prob", "—")
        t20_prob = dg.get("top_20_prob", "—")
        mc_prob = dg.get("make_cut_prob", "—")
        lines.append(f"  Model: Win {win_prob}% | Top 10: {t10_prob}% | Top 20: {t20_prob}% | Make Cut: {mc_prob}%")

        course_fit = dg.get("course_fit", "—")
        course_hist_adj = dg.get("course_history", "—")
        lines.append(f"  Course Fit Adj: {course_fit} | Course History Adj: {course_hist_adj}")

    # Recent form
    recent = recent_form_data.get(player_name, "—")
    lines.append(f"  Recent Form: {recent}")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are a sharp, opinionated golf betting analyst writing "Why They Could Win" blurbs for a premium betting preview newsletter called COSMOS Golf.

Your voice: confident, direct, data-driven but never dry. You write like a smart friend who actually watches golf and bets on it — not like a press release or a robot. Think Bill Barnwell meets a golf degenerate.

HARD RULES:
1. Each storyline is 3-5 sentences (target 65-90 words). Substantive, not bloated.
2. LEAD WITH THE MOST INTERESTING THING about this player. NOT their odds. Not their name. The hook.
   - If they just won their most recent start → lead with that (name the event)
   - If they won this event before → lead with that
   - If their SG numbers are elite → lead with that
   - If there's a red flag → lead with the contrarian angle
   - If they're on a heater → lead with the momentum
   - CRITICAL: The Recent Form list is in chronological order with most-recent FIRST. If the first event in their Recent Form is a win, T-finish, or runner-up, you MUST reference that event by name in the storyline. Do not skip over a win or top-5 from the most recent event.
   - TIMING — DO NOT use relative-week phrases like "last week", "this week", or "two weeks ago". The recent-form data is NOT anchored to exact calendar weeks, and a player's most-recent listed start is often NOT the most recent event on tour (they may have skipped it). Reference events by NAME only — write "a solo 3rd at the Byron Nelson", never "a solo 3rd at the Byron Nelson last week".
3. NEVER start two players with the same sentence structure. Vary your openers:
   - Stat-first: "The +0.96 SG Approach leads this entire field..."
   - Narrative: "Back-to-back wins here in 2023-24, and the model still loves him..."
   - Contrarian: "Listed as second favorite but the numbers don't support it..."
   - Momentum: "Fresh off a win at Bay Hill, riding 1st-T16-T6-T3 in his last four..."
   - Course fit: "This course rewards precision iron play, and nobody in the field..."
   - Blunt: "The 2017 champion is priced like a contender. He shouldn't be."
4. USE THE DATA. Every storyline must cite at least 3 distinct, specific data points (e.g., a signed SG number, a course-fit/history adjustment, a model win %, a year-tagged finish, a recent T-finish at a named event, or an OWGR rank). Bettors want numbers, not vibes.
5. Make a CLEAR betting implication in every storyline — is this player underpriced, overpriced, a fade, or a lock?
6. DO NOT use these phrases (they are banned):
   - "keep mistakes off the card"
   - "the win path is straightforward"
   - "one elite skill week can flip the board"
   - "if the approach play is a fraction off"
   - "the putter runs neutral-to-cold"
   - "create enough realistic birdie looks"
   - "convert the momentum stretch"
   - "enters [tournament] at [odds]"
   - "which places him in the [tier] tier"
   - "the simplest data point is"
   - "frames some of the attention"
   - "shouldn't override the handicap"
   - "could surprise"
   - "don't overlook"
   - "keep an eye on"
   - "sleeper pick"
   - "last week" / "this week" / "two weeks ago" (any relative-week phrasing — name the event instead)
7. For LONGSHOTS (odds > +10000): Be honest. Don't oversell. Focus on the ONE thing that makes them interesting. It's ok to say "hard to see a win path" if the data doesn't support it.
8. For FAVORITES/CONTENDERS: Be specific about WHY the price is right or wrong. Don't just say they're good.
9. Include the player's odds naturally in the text (e.g., "at +845" or "the +7381 price"), but never as the opening word.
10. Every storyline MUST be unique in structure, word choice, and angle. If you find yourself writing something similar to another player's storyline, scrap it and find a different angle.
11. NEVER invent tournament history. Only state a finish or title at THIS event if it appears on the player's "Course History at THIS event" line. If that line says NO PRIOR STARTS or "did not play" for a year, you must NOT claim any finish/win for that year. The word "champion"/"defending champion" for THIS event may ONLY be used for the players named in the FACTS block of the prompt — never anyone else."""


def generate_content_batch(
    players_batch: list,
    data: dict,
    recent_form_data: dict,
    tournament_name: str,
    course_name: str,
    default_storyline: str,
    previously_written: list[str] = None,
    champions_facts: str = "",
) -> dict:
    """Generate storylines for a batch of players using Claude."""

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    except ImportError:
        print("❌ anthropic package not installed. Run: pip install anthropic")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Could not initialize Anthropic client: {e}")
        sys.exit(1)

    # Build rich context for each player
    player_blocks = []
    for player in players_batch:
        ctx = build_rich_player_context(player, data, recent_form_data)
        player_blocks.append(ctx)

    # Anti-repetition: tell Claude what it already wrote
    anti_repeat = ""
    if previously_written:
        samples = previously_written[-6:]  # last 6 to keep prompt manageable
        anti_repeat = f"""
IMPORTANT — You already wrote storylines for earlier players. Here are the last few opening sentences you used. DO NOT repeat these patterns or structures:
{chr(10).join(f'- "{s[:120]}..."' for s in samples)}

Use DIFFERENT openers, angles, and sentence structures for this batch."""

    tournament_context = ""
    tn_lower = tournament_name.lower()
    if "schwab" in tn_lower or "colonial" in tn_lower or "colonial" in (course_name or "").lower():
        tournament_context = """
TOURNAMENT FLAVOR (Colonial Country Club — use sparingly, never as filler):
- Hogan's Alley par-4 5th: precision iron play and course management beat bombers here
- Par-70, 7,209 yards, elite 120-man field — mistakes compound on a traditional tree-lined layout
- Fort Worth heat / Texas swing: Byron Nelson last week, Colonial this week
- Ben Hogan legacy is texture only — every storyline still needs hard data and a betting angle
"""
    elif "memorial" in tn_lower or "muirfield" in tn_lower or "muirfield" in (course_name or "").lower():
        tournament_context = """
TOURNAMENT FLAVOR (Muirfield Village Golf Club — Jack Nicklaus's place — use sparingly, never as filler):
- Jack built it and hosts it; the Memorial is treated like a fifth major and the field plays it that way
- Par-72, ~7,533 yards, $20M signature event with a small elite field — this is a ball-strikers' test, not a birdie-fest
- Lightning-fast, severely contoured bentgrass greens; brutal rough; water lurks on the closing stretch (11, 14, 15, 16, 18) where loose iron play gets punished
- Course history is unusually sticky here — guys who've contended at Muirfield tend to do it again; SG: Approach and elite iron control travel best
- Texture only — every storyline still needs hard data and a clear betting angle; let the year-tagged finishes name the defending champ, don't guess
"""

    prompt = f"""Tournament: {tournament_name}
Course: {course_name}
{champions_facts}{tournament_context}
Write a "Why They Could Win" storyline for each player below. Follow the system instructions exactly.
{anti_repeat}

--- PLAYER DATA ---
{chr(10).join(player_blocks)}
--- END PLAYER DATA ---

Return ONLY a JSON object:
{{
  "Player Name": {{
    "storyline": "your 2-4 sentence storyline"
  }}
}}

No markdown, no explanation, just valid JSON."""

    try:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text
        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())
        return result

    except Exception as e:
        print(f"❌ Error generating content for batch: {e}")
        return {player: {"storyline": default_storyline} for player in players_batch}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI storylines with Claude for any tournament.")
    parser.add_argument("--tournament", type=str, required=True, help="Tournament name")
    parser.add_argument("--year", type=int, default=2026, help="Tournament year")
    parser.add_argument("--force", action="store_true", help="Overwrite existing storylines")
    parser.add_argument("--slug", type=str, default=None, help="Explicit data-file slug (overrides slugified --tournament; matches the schedule slug)")
    args = parser.parse_args()

    slug = args.slug or _slugify(args.tournament)
    year = args.year
    players_data_path = ROOT / "data" / f"{slug}_{year}_players_data.json"
    storylines_out_path = ROOT / "data" / f"{slug}_{year}_storylines.json"
    recent_form_path = ROOT / "data" / f"{slug}_{year}_recent_form.json"

    if not players_data_path.exists():
        print(f"❌ Missing {players_data_path}")
        return 1

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set in .env — cannot generate storylines")
        return 1

    # Check for existing storylines
    if storylines_out_path.exists() and not args.force:
        print(f"⚠️  Storylines already exist at {storylines_out_path}")
        print("   Use --force to overwrite.")
        return 0

    data = json.loads(players_data_path.read_text(encoding="utf-8"))
    tournament_name = data.get("tournament", {}).get("name", args.tournament)
    course = data.get("tournament", {}).get("course", "")
    default_storyline = f"Competing at {tournament_name}."

    def _is_raw_finish(s: str) -> bool:
        if not s or len(s.strip()) < 40:
            return True
        t = s.strip().upper()
        if t in ("NA", "MC", "WD", "CUT", "DQ", "—", "-"):
            return True
        if t.isdigit() or (t.startswith("T") and t[1:].isdigit()):
            return True
        return False

    # Load recent form data
    recent_form_data = {}
    if recent_form_path.exists():
        try:
            recent_form_data = json.loads(recent_form_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️  Could not load recent form data: {e}")

    # Authoritative champions from result caches, so the model labels the
    # defending champ correctly and never invents one (see audit_tournament_content.py).
    champions_facts = _build_champions_facts(slug, year)

    # Get all players from odds
    players = list(data.get("odds", {}).keys())
    print(f"📊 Generating AI storylines for {len(players)} players using Claude ({tournament_name})...")
    print(f"   Course: {course}")
    print(f"   Model: claude-opus-4-7")
    print()

    storylines = {}
    form_analyses = {}
    previously_written_openers = []

    batch_size = 8  # smaller batches for better quality + variation
    for i in range(0, len(players), batch_size):
        batch = players[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(players) - 1) // batch_size + 1
        print(f"  Batch {batch_num}/{total_batches} ({', '.join(batch[:3])}{'...' if len(batch) > 3 else ''})...", end=" ", flush=True)

        try:
            results = generate_content_batch(
                batch, data, recent_form_data, tournament_name, course,
                default_storyline, previously_written_openers, champions_facts
            )

            for player in batch:
                if player in results:
                    raw = results[player].get("storyline", default_storyline)
                    if _is_raw_finish(raw):
                        storylines[player] = default_storyline
                    else:
                        storylines[player] = raw
                        # Track openers for anti-repetition
                        first_sentence = raw.split(". ")[0] if ". " in raw else raw[:100]
                        previously_written_openers.append(first_sentence)
                    form_analyses[player] = results[player].get("form_analysis", "—")
                else:
                    storylines[player] = default_storyline
                    form_analyses[player] = "—"

            print("✓")

        except Exception as e:
            print(f"❌ {e}")
            for player in batch:
                storylines[player] = default_storyline
                form_analyses[player] = "—"

    output = {
        "storylines": storylines,
        "recent_form_analyses": form_analyses,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": "claude-opus-4-7",
    }

    storylines_out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Wrote {len(storylines)} storylines to {storylines_out_path}")

    # Print a few samples
    print("\n--- SAMPLE STORYLINES ---")
    for i, (name, story) in enumerate(storylines.items()):
        if i >= 5:
            break
        print(f"\n  {name}:")
        print(f"  {story}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
