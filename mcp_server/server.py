"""DataGolf MCP server — thin FastMCP (stdio) wrapper around DataGolfClient.

Lets any Claude session in this project query the Data Golf API directly
(the PRIMARY data source for this repo: odds, strokes-gained, predictions,
schedules, historical results).

Registered in .mcp.json; runs on the repo's .venv-mcp interpreter:
    .venv-mcp/bin/python -m mcp_server.server

API key comes from .env (DATAGOLF_API_KEY) via mcp_server/config.py — never
hardcoded. Pipeline scripts keep calling DataGolfClient directly; this server
is for interactive/agent use.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP

from mcp_server.tools.datagolf import DataGolfClient

mcp = FastMCP("datagolf")


def _dump(obj: Any) -> Any:
    """Make pydantic models / lists JSON-serializable."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict") and not isinstance(obj, dict):
        try:
            return obj.dict()
        except Exception:
            pass
    if isinstance(obj, list):
        return [_dump(o) for o in obj]
    if isinstance(obj, dict):
        return {k: _dump(v) for k, v in obj.items()}
    return obj


@mcp.tool()
def get_schedule(tour: str = "pga") -> Any:
    """Tour schedule (event names, dates, courses). tour: pga/euro/kft/opp/alt/liv."""
    with DataGolfClient() as dg:
        return _dump(dg.get_tour_schedules(tour=tour))


@mcp.tool()
def get_field_updates(tour: str = "pga") -> Any:
    """Current-event field: who's playing this week, WDs, tee times. Rolls over to the new event before the odds endpoints do."""
    with DataGolfClient() as dg:
        return _dump(dg.get_field_updates(tour=tour))


@mcp.tool()
def get_outright_odds(tour: str = "pga", market: str = "win", odds_format: str = "american") -> Any:
    """Outright odds with DataGolf fair values + sportsbook lines. market: win/top_5/top_10/top_20/make_cut/mc. The response's event_name shows which event DG is currently serving (stale-data check)."""
    with DataGolfClient() as dg:
        return _dump(dg.get_outright_odds(tour=tour, market=market, odds_format=odds_format))


@mcp.tool()
def get_pre_tournament_predictions(tour: str = "pga", odds_format: str = "percent") -> Any:
    """Model win/top-finish probabilities for the current event (baseline + course-fit models)."""
    with DataGolfClient() as dg:
        return _dump(dg.get_pre_tournament_predictions(tour=tour, odds_format=odds_format))


@mcp.tool()
def get_skill_ratings(display: str = "value") -> Any:
    """Player strokes-gained skill decomposition (off-the-tee, approach, around-green, putting)."""
    with DataGolfClient() as dg:
        return _dump(dg.get_player_skill_ratings(display=display))


@mcp.tool()
def get_dg_rankings() -> Any:
    """DataGolf's own player rankings (top ~500, with skill estimate)."""
    with DataGolfClient() as dg:
        return _dump(dg.get_dg_rankings())


@mcp.tool()
def get_matchup_odds(tour: str = "pga", market: str = "tournament_matchups", odds_format: str = "american") -> Any:
    """Head-to-head matchup odds with DataGolf fair values. market: tournament_matchups/round_matchups/3_balls."""
    with DataGolfClient() as dg:
        return _dump(dg.get_matchup_odds(tour=tour, market=market, odds_format=odds_format))


@mcp.tool()
def get_historical_event_list(tour: Optional[str] = None) -> Any:
    """List event IDs/years available for historical queries (use before get_historical_rounds)."""
    with DataGolfClient() as dg:
        return _dump(dg.get_historical_raw_event_ids(tour=tour))


@mcp.tool()
def get_historical_rounds(tour: str = "pga", event_id: Optional[str] = None, year: Optional[int] = None) -> Any:
    """Round-level historical scoring/strokes-gained incl. fin_text finish positions (works on this plan; historical-event-data/finishes does NOT)."""
    with DataGolfClient() as dg:
        return _dump(dg.get_historical_rounds(tour=tour, event_id=event_id, year=year))


@mcp.tool()
def search_player(name: str) -> Any:
    """Look up a player (name fragment) in the DataGolf player list -> dg_id, country, amateur status."""
    with DataGolfClient() as dg:
        player = dg.get_player_by_name(name)
        return _dump(player) if player else {"error": f"no player matching '{name}'"}


if __name__ == "__main__":
    mcp.run()
