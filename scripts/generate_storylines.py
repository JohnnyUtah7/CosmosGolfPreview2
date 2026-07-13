#!/usr/bin/env python3
"""
Generate player storylines using current golf news + (optional) LLM.

This script is designed to run as part of the weekly workflow (Phase 3).
It will:
- Load odds + player info from the JSON produced by `generate_preview.py`
- Optionally load historical finishes from a separate JSON file
- Fetch recent player news via Google News RSS (no paid API required)
- Generate 150–200 word storylines (Claude/Anthropic if configured, otherwise a
  deterministic template fallback)

Usage:
  python scripts/generate_storylines.py \
    --tournament "Sony Open" \
    --players-data ./previews/preview_data_20260116.json \
    --previous-week ./data/previous_tournament_storylines.json \
    --output ./data/storylines_sony_open.json
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import os
import re
from typing import Any, Optional

import httpx

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tools.news import GolfNewsClient, NewsArticle

def _safe_int(val: Any, default: int = 10000) -> int:
    try:
        return int(val)
    except Exception:
        return default


def _format_american_odds(odds: int) -> str:
    if odds > 0:
        return f"+{odds}"
    return str(odds)


def _infer_tier(odds: int) -> str:
    if odds <= 800:
        return "favorite"
    if odds <= 2000:
        return "contender"
    if odds <= 5000:
        return "value"
    return "longshot"


def _squash_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _summarize_headlines(articles: list[NewsArticle]) -> str:
    if not articles:
        return ""
    # Keep it short and avoid "laundry list" feel in the final copy.
    for a in articles:
        if a.title:
            return a.title
    return ""


def _render_historical_snippet(historical_finishes: dict[str, str]) -> str:
    if not historical_finishes:
        return ""
    # Keep stable ordering (most recent first if years look like numbers)
    items = list(historical_finishes.items())
    try:
        items.sort(key=lambda kv: int(kv[0]), reverse=True)
    except Exception:
        pass
    rendered = ", ".join([f"{y}: {v}" for y, v in items[:3] if v])
    return rendered


def _anthropic_generate_storyline(
    *,
    api_key: str,
    model: str,
    player_name: str,
    tournament_name: str,
    odds: int,
    country: Optional[str],
    historical_snippet: str,
    headlines_summary: str,
    previous_storyline: Optional[str],
    timeout_seconds: float = 45.0,
) -> str:
    """
    Generate storyline using Anthropic Messages API.
    This uses `httpx` directly (no extra dependency).
    """
    system = (
        "You write strategic “Why they could win” blurbs for a golf betting preview in a consistent voice. "
        "Hard rules:\n"
        "- 5–7 sentences (~110–160 words)\n"
        "- Do NOT invent specific wins/finishes/records unless provided in inputs\n"
        "- If you reference news, do so generally (e.g., 'recent coverage has focused on...')\n"
        "- Briefly acknowledge the market tier from odds (favorite/contender/value/longshot)\n"
        "- Avoid absolute claims; prefer data-grounded framing\n"
        "- Focus on a plausible win path: what needs to show up in the player's game this week\n"
    )

    tier = _infer_tier(odds)
    user = (
        f"Player: {player_name}\n"
        f"Tournament: {tournament_name}\n"
        f"Odds (American): {_format_american_odds(odds)} ({tier})\n"
        f"Country: {country or 'unknown'}\n"
        f"Course history (only use if present): {historical_snippet or 'none provided'}\n"
        f"Recent headlines (titles only; do not claim facts beyond them): {headlines_summary or 'none found'}\n"
        f"Previous storyline (optional for continuity): {previous_storyline or 'none'}\n"
        "\nWrite one paragraph. No bullet points."
    )

    payload = {
        "model": model,
        "max_tokens": 300,
        "temperature": 0.6,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    parts = data.get("content") or []
    text = ""
    for part in parts:
        if part.get("type") == "text":
            text += part.get("text", "")
    return _squash_ws(text)


def _fallback_storyline(
    *,
    player_name: str,
    tournament_name: str,
    odds: int,
    country: Optional[str],
    historical_finishes: dict[str, str],
    headlines: list[NewsArticle],
    previous_storyline: Optional[str],
) -> str:
    """
    Deterministic storyline that avoids making unverifiable claims.
    Target length: ~110–160 words.
    """
    tier = _infer_tier(odds)
    odds_str = _format_american_odds(odds)
    hist = _render_historical_snippet(historical_finishes)
    headline = _summarize_headlines(headlines)

    # Turn history into a safe, data-grounded sentence.
    history_sentence = ""
    if hist:
        history_sentence = f" The simplest data point is course history: {hist}."

    # Turn one headline into a non-committal hook.
    news_sentence = ""
    if headline:
        news_sentence = (
            f" The week’s news cycle has touched on “{headline},” which frames some of the attention—"
            "but it shouldn’t override the handicap."
        )

    # Tier-aware but still “why they could win”.
    if tier == "favorite":
        tier_sentence = " The market sees him as a front-runner, so the bar is simple: play to his baseline and avoid a cold putter week."
    elif tier == "contender":
        tier_sentence = " He sits in the contender tier—good enough to win if the scoring weapons show up for four straight rounds."
    elif tier == "value":
        tier_sentence = " In the value range, the win case is real but volatile: one elite skill week can flip the board."
    else:
        tier_sentence = " At longshot odds, the win case is narrower—but not imaginary if the key strengths hit at the same time."

    win_path_sentence = (
        " The win path is straightforward: keep mistakes off the card, create enough realistic birdie looks, and convert the momentum stretch when it shows up."
    )
    risk_sentence = (
        " The risk is the opposite profile—if the approach play is a fraction off or the putter runs neutral-to-cold, it’s hard to separate in a packed field."
    )

    continuity_sentence = ""
    if previous_storyline:
        continuity_sentence = " There’s also a continuity angle from last week—what mattered then still matters now, with small tweaks based on the venue."

    base = (
        f"{player_name}{f' ({country})' if country else ''} enters {tournament_name} at {odds_str}, "
        f"which places him in the {tier} tier by market expectation."
        + history_sentence
        + news_sentence
        + tier_sentence
        + win_path_sentence
        + risk_sentence
        + continuity_sentence
    )

    # Nudge toward the target if we’re short.
    text = _squash_ws(base)
    if len(text.split()) < 110:
        text = _squash_ws(
            text
            + " If he’s trending the right way in the run-up to this week, that’s usually visible in the quality of scoring chances created—especially on the holes you have to take advantage of."
        )
    return text


def fetch_recent_golf_news(
    news_client: GolfNewsClient,
    player_name: str,
    tournament_name: str,
    *,
    days: int,
    max_results: int,
    use_news: bool,
) -> list[NewsArticle]:
    if not use_news:
        return []
    try:
        return news_client.search_player_news(
            player_name,
            tournament_name=tournament_name,
            days=days,
            max_results=max_results,
        )
    except Exception as e:
        print(f"⚠️  News fetch failed for {player_name}: {e}")
        return []


def generate_player_storyline(
    *,
    player_name: str,
    tournament_name: str,
    current_odds: int,
    country: Optional[str],
    historical_finishes: dict[str, str],
    headlines: list[NewsArticle],
    previous_storyline: Optional[str],
    use_llm: bool,
    anthropic_api_key: str,
    anthropic_model: str,
) -> str:
    headlines_summary = _summarize_headlines(headlines)
    historical_snippet = _render_historical_snippet(historical_finishes)

    if use_llm and anthropic_api_key:
        try:
            return _anthropic_generate_storyline(
                api_key=anthropic_api_key,
                model=anthropic_model,
                player_name=player_name,
                tournament_name=tournament_name,
                odds=current_odds,
                country=country,
                historical_snippet=historical_snippet,
                headlines_summary=headlines_summary,
                previous_storyline=previous_storyline,
            )
        except Exception as e:
            print(f"⚠️  LLM generation failed for {player_name}, falling back: {e}")

    return _fallback_storyline(
        player_name=player_name,
        tournament_name=tournament_name,
        odds=current_odds,
        country=country,
        historical_finishes=historical_finishes,
        headlines=headlines,
        previous_storyline=previous_storyline,
    )


def build_storyline_database(
    players: list[str],
    tournament_name: str,
    historical_data: dict[str, dict[str, str]],
    odds_data: dict[str, dict[str, Any]],
    players_info: dict[str, dict[str, Any]],
    previous_tournament_data: dict = None
) -> dict[str, str]:
    """
    Build complete storyline database for all players.

    Args:
        players: List of player names
        tournament_name: Tournament name
        historical_data: Historical finishes for each player
        odds_data: Current odds for each player
        previous_tournament_data: Storylines from previous tournament (optional)

    Returns:
        Dictionary mapping player names to storylines
    """
    storylines: dict[str, str] = {}

    use_llm = os.getenv("USE_LLM", "1").strip() not in {"0", "false", "False", "no", "NO"}
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest").strip()
    news_days = _safe_int(os.getenv("NEWS_DAYS", "14"), default=14)
    news_max = _safe_int(os.getenv("NEWS_MAX_ARTICLES", "6"), default=6)
    use_news = os.getenv("USE_NEWS", "1").strip() not in {"0", "false", "False", "no", "NO"}

    with GolfNewsClient() as news_client:
        for player in players:
            print(f"\n📝 Generating storyline for {player}...")

            historical = historical_data.get(player, {}) or {}
            odds = _safe_int((odds_data.get(player) or {}).get("odds", 10000), default=10000)
            country = (players_info.get(player) or {}).get("country")
            previous_storyline = None

            if previous_tournament_data:
                previous_storyline = (previous_tournament_data.get("storylines") or previous_tournament_data.get(player) or {}).get(
                    "storyline", None
                )
                # Some previous files may be flat {player: storyline}
                if isinstance(previous_tournament_data.get(player), str):
                    previous_storyline = previous_tournament_data.get(player)

            headlines = fetch_recent_golf_news(
                news_client,
                player,
                tournament_name,
                days=news_days,
                max_results=news_max,
                use_news=use_news,
            )

            storyline = generate_player_storyline(
                player_name=player,
                tournament_name=tournament_name,
                current_odds=odds,
                country=country,
                historical_finishes=historical,
                headlines=headlines,
                previous_storyline=previous_storyline,
                use_llm=use_llm,
                anthropic_api_key=anthropic_api_key,
                anthropic_model=anthropic_model,
            )

            storylines[player] = storyline
            print(f"   ✓ {storyline[:80]}...")

    return storylines


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate player storylines with AI and news"
    )
    parser.add_argument(
        "--tournament",
        type=str,
        required=True,
        help="Tournament name"
    )
    parser.add_argument(
        "--players-data",
        type=Path,
        help="JSON file with player odds and historical data"
    )
    parser.add_argument(
        "--historical-data",
        type=Path,
        help="Optional historical finishes JSON (player -> year -> finish)"
    )
    parser.add_argument(
        "--previous-week",
        type=Path,
        help="Previous week's storylines JSON (for continuity)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file path"
    )
    parser.add_argument(
        "--max-players",
        type=int,
        default=0,
        help="Limit number of players generated (0 = all)"
    )
    parser.add_argument(
        "--players",
        type=str,
        nargs="*",
        default=[],
        help="Optional explicit player list to generate (names must match odds keys)"
    )

    args = parser.parse_args()

    print("✍️  AI Storyline Generator")
    print("=" * 60)

    # Load player data
    if args.players_data and args.players_data.exists():
        with open(args.players_data) as f:
            players_data = json.load(f)
    else:
        print("⚠️  No player data file provided. Use --players-data option.")
        return 1

    # Load historical finishes (optional)
    historical_data = {}
    if args.historical_data and args.historical_data.exists():
        with open(args.historical_data) as f:
            historical_data = json.load(f)
        print("📊 Loaded historical finishes")

    # Load previous week (optional)
    previous_data = None
    if args.previous_week and args.previous_week.exists():
        with open(args.previous_week) as f:
            previous_data = json.load(f)
        print(f"📚 Loaded previous tournament data for continuity")

    try:
        # Extract players list (optionally filtered)
        odds_block = players_data.get("odds", {}) if isinstance(players_data, dict) else {}
        players_all = list(odds_block.keys())

        if args.players:
            players = [p for p in players_all if p in set(args.players)]
        else:
            players = players_all

        if args.max_players and args.max_players > 0:
            players = players[: args.max_players]

        players_info = players_data.get("players", {}) if isinstance(players_data, dict) else {}

        # Build storylines
        storylines = build_storyline_database(
            players,
            args.tournament,
            historical_data or players_data.get("historical", {}) or {},
            players_data.get("odds", {}) or {},
            players_info or {},
            previous_data
        )

        # Prepare output
        output_data = {
            "tournament": args.tournament,
            "generated_at": datetime.now().isoformat(),
            "storylines": storylines,
            "metadata": {
                "player_count": len(players),
                "used_previous_data": previous_data is not None,
                "used_news": os.getenv("USE_NEWS", "1").strip() not in {"0", "false", "False", "no", "NO"},
                "used_llm": bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
                and (os.getenv("USE_LLM", "1").strip() not in {"0", "false", "False", "no", "NO"}),
                "anthropic_model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest").strip(),
            }
        }

        # Save to file
        if args.output:
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            print(f"\n💾 Storylines saved to: {args.output}")

        print("\n✅ Storyline generation complete!")
        if not os.getenv("ANTHROPIC_API_KEY", "").strip():
            print("\nℹ️  Note: Set ANTHROPIC_API_KEY to enable Claude-written storylines.")
            print("   Fallback mode uses a deterministic template + RSS headlines.")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
