"""Client for Data Golf API - comprehensive golf data and predictions.

Data Golf API provides:
- Player lists and IDs (unified across tours)
- Tour schedules and field updates
- Model predictions (pre-tournament and live)
- Betting odds with edge calculations
- Historical raw data (scoring, strokes-gained)
- Historical event results
- Historical betting odds
- DFS data

API Documentation: https://datagolf.com/api-access
"""
from __future__ import annotations

import httpx
import time
import random
from datetime import datetime
from typing import Optional, Any, Literal

from ..config import DATAGOLF_API_KEY, DATAGOLF_API_BASE_URL
from ..models.schemas import (
    DataGolfPlayer,
    DataGolfRanking,
    DataGolfFieldPlayer,
    DataGolfTournament,
    DataGolfPrediction,
    DataGolfSkillRating,
    DataGolfLivePrediction,
    DataGolfOutrightOdds,
    DataGolfMatchup,
    DataGolfHistoricalRound,
    DataGolfEventResult,
    DataGolfHistoricalOdds,
)


# Tour codes used by Data Golf
TOUR_CODES = Literal["pga", "euro", "kft", "opp", "alt", "liv"]


class DataGolfClient:
    """Client for interacting with the Data Golf API.

    This client provides access to comprehensive golf data including:
    - Player rankings and skill ratings
    - Tournament fields and schedules
    - Pre-tournament and live predictions
    - Betting odds with edge calculations
    - Historical scoring and strokes-gained data

    Usage:
        with DataGolfClient() as dg:
            # Get current field
            field = dg.get_field_updates()

            # Get pre-tournament predictions
            predictions = dg.get_pre_tournament_predictions()

            # Get betting odds with edges
            odds = dg.get_outright_odds()
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Data Golf API client.

        Args:
            api_key: Data Golf API key. If not provided, uses config/env.
        """
        self.api_key = api_key or DATAGOLF_API_KEY
        self.base_url = DATAGOLF_API_BASE_URL
        self.client = httpx.Client(timeout=60.0)
        self._max_retries = 5

        if not self.api_key:
            raise ValueError(
                "DATAGOLF_API_KEY is required. Set it in .env file or pass directly."
            )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.client.close()

    def _get_with_backoff(
        self, endpoint: str, params: Optional[dict[str, Any]] = None
    ) -> dict:
        """Make GET request with exponential backoff for rate limits.

        Args:
            endpoint: API endpoint path (without base URL)
            params: Query parameters (api key added automatically)

        Returns:
            JSON response as dictionary
        """
        if params is None:
            params = {}

        # Always add API key
        params["key"] = self.api_key

        url = f"{self.base_url}/{endpoint}"
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                resp = self.client.get(url, params=params)

                if resp.status_code == 429:
                    # Rate limited - back off
                    sleep_s = min(30.0, (2**attempt) + random.uniform(0.1, 0.5))
                    print(f"Rate limited, waiting {sleep_s:.1f}s...")
                    time.sleep(sleep_s)
                    continue

                if resp.status_code == 401:
                    raise ValueError("Invalid API key or unauthorized access")

                if 500 <= resp.status_code <= 599 and attempt < self._max_retries - 1:
                    # Server error - retry with backoff
                    time.sleep(min(10.0, 0.5 * (2**attempt)))
                    continue

                resp.raise_for_status()
                return resp.json()

            except httpx.HTTPStatusError as e:
                last_exc = e
                if attempt < self._max_retries - 1:
                    time.sleep(min(10.0, 0.5 * (2**attempt)))
                    continue
                raise

            except Exception as e:
                last_exc = e
                if attempt < self._max_retries - 1:
                    time.sleep(min(10.0, 0.5 * (2**attempt)))
                    continue
                raise

        raise RuntimeError(
            f"Data Golf request failed after {self._max_retries} attempts"
        ) from last_exc

    # =========================================================================
    # GENERAL USE ENDPOINTS
    # =========================================================================

    def get_player_list(self) -> list[DataGolfPlayer]:
        """Get the master list of all players with their IDs.

        This endpoint returns Data Golf's unified player ID system which maps
        players across PGA Tour, European Tour, Korn Ferry, and other tours.

        Returns:
            List of DataGolfPlayer objects with dg_id, name, country, etc.
        """
        data = self._get_with_backoff("get-player-list")

        players = []
        for p in data:
            players.append(
                DataGolfPlayer(
                    dg_id=p.get("dg_id"),
                    player_name=p.get("player_name", ""),
                    country=p.get("country"),
                    country_code=p.get("country_code"),
                    amateur=p.get("amateur", False),
                    pga_id=p.get("pga_id"),
                    espn_id=p.get("espn_id"),
                )
            )
        return players

    def get_tour_schedules(
        self,
        tour: TOUR_CODES = "pga",
        season: Optional[int] = None,
    ) -> list[DataGolfTournament]:
        """Get tour schedule/calendar.

        Args:
            tour: Tour code ('pga', 'euro', 'kft', 'opp', 'alt', 'liv')
            season: Season year (defaults to current season)

        Returns:
            List of tournaments on the schedule
        """
        params = {"tour": tour}
        if season:
            params["season"] = season

        data = self._get_with_backoff("get-schedule", params)

        tournaments = []
        schedule = data.get("schedule", [])
        for t in schedule:
            tournaments.append(
                DataGolfTournament(
                    event_id=t.get("event_id"),
                    event_name=t.get("event_name", ""),
                    tour=tour,
                    course=t.get("course"),
                    start_date=t.get("start_date"),
                    end_date=t.get("end_date"),
                    purse=t.get("purse"),
                    latitude=t.get("latitude"),
                    longitude=t.get("longitude"),
                )
            )
        return tournaments

    def get_field_updates(
        self,
        tour: TOUR_CODES = "pga",
        file_format: str = "json",
    ) -> list[DataGolfFieldPlayer]:
        """Get the current field for the next upcoming event.

        Includes DFS salaries when available (DraftKings, FanDuel).

        Args:
            tour: Tour code ('pga', 'euro', 'kft', 'opp', 'alt', 'liv')
            file_format: Response format ('json' or 'csv')

        Returns:
            List of players in the current field with salary info
        """
        params = {"tour": tour, "file_format": file_format}
        data = self._get_with_backoff("field-updates", params)

        field = []
        for p in data.get("field", []):
            field.append(
                DataGolfFieldPlayer(
                    dg_id=p.get("dg_id"),
                    player_name=p.get("player_name", ""),
                    country=p.get("country"),
                    am=p.get("am", False),
                    dk_salary=p.get("dk_salary"),
                    dk_id=p.get("dk_id"),
                    fd_salary=p.get("fd_salary"),
                    fd_id=p.get("fd_id"),
                    r1_teetime=p.get("r1_teetime"),
                    r2_teetime=p.get("r2_teetime"),
                )
            )
        return field

    # =========================================================================
    # MODEL PREDICTIONS ENDPOINTS
    # =========================================================================

    def get_dg_rankings(self) -> list[DataGolfRanking]:
        """Get Data Golf's model-based player rankings.

        Returns players ranked by Data Golf's skill estimates,
        which often differ from OWGR.

        Returns:
            List of players with DG rankings and skill estimates
        """
        data = self._get_with_backoff("preds/get-dg-rankings")

        rankings = []
        for p in data.get("rankings", []):
            rankings.append(
                DataGolfRanking(
                    dg_id=p.get("dg_id"),
                    player_name=p.get("player_name", ""),
                    country=p.get("country"),
                    owgr=p.get("owgr_rank"),
                    datagolf_rank=p.get("datagolf_rank"),
                    dg_skill_estimate=p.get("dg_skill_estimate"),
                    primary_tour=p.get("primary_tour"),
                )
            )
        return rankings

    def get_pre_tournament_predictions(
        self,
        tour: TOUR_CODES = "pga",
        add_position: Optional[int] = None,
        odds_format: str = "percent",
        file_format: str = "json",
    ) -> dict:
        """Get pre-tournament predictions for the current event.

        Returns probability distributions for each player to finish
        in various positions (win, top 5, top 10, etc.)

        Args:
            tour: Tour code
            add_position: Additional finish position to include (e.g., 30 for top-30)
            odds_format: 'american', 'decimal', or 'percent'
            file_format: 'json' or 'csv'

        Returns:
            Dict with event_name, last_updated, and list of predictions
        """
        params = {
            "tour": tour,
            "odds_format": odds_format,
            "file_format": file_format,
        }
        if add_position:
            params["add_position"] = add_position

        data = self._get_with_backoff("preds/pre-tournament", params)

        predictions = []
        for p in data.get("baseline_history_fit", []):
            predictions.append(
                DataGolfPrediction(
                    dg_id=p.get("dg_id"),
                    player_name=p.get("player_name", ""),
                    country=p.get("country"),
                    win_prob=p.get("win"),
                    top_5_prob=p.get("top_5"),
                    top_10_prob=p.get("top_10"),
                    top_20_prob=p.get("top_20"),
                    make_cut_prob=p.get("make_cut"),
                    baseline_pred=p.get("baseline_pred"),
                    baseline_history_fit=p.get("baseline_history_fit"),
                )
            )

        return {
            "event_name": data.get("event_name"),
            "last_updated": data.get("last_updated"),
            "predictions": predictions,
        }

    def get_pre_tournament_predictions_archive(
        self,
        event_id: str,
        year: int,
        odds_format: str = "american",
        file_format: str = "json",
    ) -> dict:
        """Get archived pre-tournament predictions for a past event.

        Args:
            event_id: Data Golf event ID
            year: Year of the event
            odds_format: 'american', 'decimal', or 'percent'
            file_format: 'json' or 'csv'

        Returns:
            Dict with event info and historical predictions
        """
        params = {
            "event_id": event_id,
            "year": year,
            "odds_format": odds_format,
            "file_format": file_format,
        }
        return self._get_with_backoff("preds/pre-tournament-archive", params)

    def get_player_skill_decompositions(
        self,
        tour: TOUR_CODES = "pga",
        file_format: str = "json",
    ) -> dict:
        """Get detailed skill breakdowns and course fit adjustments for players.

        Returns course-specific adjustments like driving distance adjustment,
        driving accuracy adjustment, strokes-gained category adjustments, etc.
        This is useful for understanding WHY a player fits a particular course.

        Args:
            tour: Tour code
            file_format: 'json' or 'csv'

        Returns:
            Dict with event_name, course_name, and list of player decompositions
        """
        params = {"tour": tour, "file_format": file_format}
        data = self._get_with_backoff("preds/player-decompositions", params)

        return {
            "event_name": data.get("event_name"),
            "course_name": data.get("course_name"),
            "last_updated": data.get("last_updated"),
            "notes": data.get("notes"),
            "players": data.get("players", []),
        }

    def get_player_skill_ratings(
        self,
        display: str = "value",
        file_format: str = "json",
    ) -> list[DataGolfSkillRating]:
        """Get player skill ratings (strokes-gained components).

        This is the main endpoint for strokes-gained data. Returns
        sg_total, sg_ott, sg_app, sg_arg, sg_putt for each player.

        Args:
            display: 'value' for raw values, 'rank' for rankings
            file_format: 'json' or 'csv'

        Returns:
            List of DataGolfSkillRating with strokes-gained components
        """
        params = {"display": display, "file_format": file_format}
        data = self._get_with_backoff("preds/skill-ratings", params)

        skills = []
        for p in data.get("players", []):
            skills.append(
                DataGolfSkillRating(
                    dg_id=p.get("dg_id"),
                    player_name=p.get("player_name", ""),
                    sg_total=p.get("sg_total"),
                    sg_ott=p.get("sg_ott"),
                    sg_app=p.get("sg_app"),
                    sg_arg=p.get("sg_arg"),
                    sg_putt=p.get("sg_putt"),
                    driving_acc=p.get("driving_acc"),
                    driving_dist=p.get("driving_dist"),
                )
            )
        return skills

    def get_detailed_approach_skill(
        self,
        period: str = "l24",
        file_format: str = "json",
    ) -> list[dict]:
        """Get detailed approach shot skill breakdowns.

        Args:
            period: Time period ('l12', 'l24', 'l36' for months)
            file_format: 'json' or 'csv'

        Returns:
            Detailed approach skill data by distance/lie
        """
        params = {"period": period, "file_format": file_format}
        return self._get_with_backoff("preds/approach-skill", params)

    def get_fantasy_projection_defaults(
        self,
        tour: TOUR_CODES = "pga",
        site: str = "draftkings",
        slate: str = "main",
        file_format: str = "json",
    ) -> dict:
        """Get default fantasy projections.

        Args:
            tour: Tour code
            site: 'draftkings' or 'fanduel'
            slate: 'main', 'showdown', etc.
            file_format: 'json' or 'csv'

        Returns:
            Fantasy projections with ownership, points, etc.
        """
        params = {
            "tour": tour,
            "site": site,
            "slate": slate,
            "file_format": file_format,
        }
        return self._get_with_backoff("preds/fantasy-projection-defaults", params)

    # =========================================================================
    # LIVE MODEL ENDPOINTS
    # =========================================================================

    def get_live_predictions(
        self,
        tour: TOUR_CODES = "pga",
        dead_heat: bool = True,
        odds_format: str = "american",
        file_format: str = "json",
    ) -> dict:
        """Get live in-tournament predictions.

        Updates every 5 minutes during tournament play.

        Args:
            tour: Tour code
            dead_heat: Whether to use dead-heat rules for ties
            odds_format: 'american', 'decimal', or 'percent'
            file_format: 'json' or 'csv'

        Returns:
            Dict with current standings and live predictions
        """
        params = {
            "tour": tour,
            "dead_heat": str(dead_heat).lower(),
            "odds_format": odds_format,
            "file_format": file_format,
        }
        data = self._get_with_backoff("preds/in-play", params)

        predictions = []
        for p in data.get("data", []):
            predictions.append(
                DataGolfLivePrediction(
                    dg_id=p.get("dg_id"),
                    player_name=p.get("player_name", ""),
                    current_pos=p.get("current_pos"),
                    current_score=p.get("total"),
                    thru=p.get("thru"),
                    today=p.get("today"),
                    win_prob=p.get("win"),
                    top_5_prob=p.get("top_5"),
                    top_10_prob=p.get("top_10"),
                    top_20_prob=p.get("top_20"),
                    make_cut_prob=p.get("make_cut"),
                    proj_finish=p.get("proj_finish"),
                )
            )

        return {
            "info": data.get("info"),
            "predictions": predictions,
        }

    def get_live_tournament_stats(
        self,
        tour: TOUR_CODES = "pga",
        stats: str = "sg_total,sg_ott,sg_app,sg_arg,sg_putt",
        round_num: Optional[int] = None,
        display: str = "value",
        file_format: str = "json",
    ) -> dict:
        """Get live strokes-gained and stats during a tournament.

        Args:
            tour: Tour code
            stats: Comma-separated list of stats to include
            round_num: Specific round (None for cumulative)
            display: 'value' or 'rank'
            file_format: 'json' or 'csv'

        Returns:
            Live tournament statistics
        """
        params = {
            "tour": tour,
            "stats": stats,
            "display": display,
            "file_format": file_format,
        }
        if round_num:
            params["round"] = round_num

        return self._get_with_backoff("preds/live-tournament-stats", params)

    def get_live_hole_scoring_distributions(
        self,
        tour: TOUR_CODES = "pga",
        file_format: str = "json",
    ) -> dict:
        """Get hole-by-hole scoring distributions for live events.

        Args:
            tour: Tour code
            file_format: 'json' or 'csv'

        Returns:
            Scoring distributions per hole
        """
        params = {"tour": tour, "file_format": file_format}
        return self._get_with_backoff("preds/live-hole-stats", params)

    # =========================================================================
    # BETTING TOOLS ENDPOINTS
    # =========================================================================

    def get_outright_odds(
        self,
        tour: TOUR_CODES = "pga",
        market: str = "win",
        odds_format: str = "american",
        file_format: str = "json",
    ) -> dict:
        """Get outright/finish position odds with Data Golf fair values.

        This is THE key endpoint for betting - it shows:
        - Data Golf's fair odds (baseline and baseline_history_fit models)
        - Current sportsbook odds from multiple books
        - Includes bet365, betmgm, bovada, caesars, draftkings, fanduel, pinnacle, etc.

        Args:
            tour: Tour code
            market: 'win', 'top_5', 'top_10', 'top_20', 'make_cut', 'mc' (miss cut)
            odds_format: 'american', 'decimal', or 'percent'
            file_format: 'json' or 'csv'

        Returns:
            Dict with event info, books offering, and list of player odds
        """
        params = {
            "tour": tour,
            "market": market,
            "odds_format": odds_format,
            "file_format": file_format,
        }
        data = self._get_with_backoff("betting-tools/outrights", params)

        return {
            "event_name": data.get("event_name"),
            "market": data.get("market"),
            "last_updated": data.get("last_updated"),
            "books_offering": data.get("books_offering", []),
            "odds": data.get("odds", []),
        }

    def get_matchup_odds(
        self,
        tour: TOUR_CODES = "pga",
        market: str = "tournament_matchups",
        odds_format: str = "american",
        file_format: str = "json",
    ) -> list[DataGolfMatchup]:
        """Get head-to-head matchup and 3-ball odds.

        Args:
            tour: Tour code
            market: 'tournament_matchups', 'round_matchups', '3_balls'
            odds_format: 'american', 'decimal', or 'percent'
            file_format: 'json' or 'csv'

        Returns:
            List of matchups with fair probabilities and book odds
        """
        params = {
            "tour": tour,
            "market": market,
            "odds_format": odds_format,
            "file_format": file_format,
        }
        data = self._get_with_backoff("betting-tools/matchups", params)

        matchups = []
        for m in data.get("matchups", []):
            matchups.append(
                DataGolfMatchup(
                    matchup_type=m.get("matchup_type", "2-ball"),
                    player_1_dg_id=m.get("player_1_dg_id"),
                    player_1_name=m.get("player_1_name", ""),
                    player_2_dg_id=m.get("player_2_dg_id"),
                    player_2_name=m.get("player_2_name", ""),
                    player_3_dg_id=m.get("player_3_dg_id"),
                    player_3_name=m.get("player_3_name"),
                    player_1_dg_prob=m.get("player_1_prob"),
                    player_2_dg_prob=m.get("player_2_prob"),
                    player_3_dg_prob=m.get("player_3_prob"),
                    tie_prob=m.get("tie_prob"),
                    player_1_book_odds=m.get("player_1_odds"),
                    player_2_book_odds=m.get("player_2_odds"),
                    player_3_book_odds=m.get("player_3_odds"),
                )
            )
        return matchups

    def get_matchup_odds_all_pairings(
        self,
        tour: TOUR_CODES = "pga",
        odds_format: str = "american",
        file_format: str = "json",
    ) -> dict:
        """Get Data Golf fair odds for ALL possible player pairings.

        This is useful for finding value in matchups not offered by books.

        Args:
            tour: Tour code
            odds_format: 'american', 'decimal', or 'percent'
            file_format: 'json' or 'csv'

        Returns:
            Matrix of all possible matchup fair values
        """
        params = {
            "tour": tour,
            "odds_format": odds_format,
            "file_format": file_format,
        }
        return self._get_with_backoff("betting-tools/matchups-all-pairings", params)

    # =========================================================================
    # HISTORICAL RAW DATA ENDPOINTS
    # =========================================================================

    def get_historical_raw_event_ids(
        self,
        tour: Optional[str] = None,
        file_format: str = "json",
    ) -> list[dict]:
        """Get list of event IDs for historical raw data queries.

        Args:
            tour: Optional tour filter
            file_format: 'json' or 'csv'

        Returns:
            List of events with their IDs and basic info
        """
        params = {"file_format": file_format}
        if tour:
            params["tour"] = tour

        return self._get_with_backoff("historical-raw-data/event-list", params)

    def get_historical_rounds(
        self,
        tour: TOUR_CODES = "pga",
        event_id: Optional[str] = None,
        year: Optional[int] = None,
        player_id: Optional[int] = None,
        file_format: str = "json",
    ) -> list[DataGolfHistoricalRound]:
        """Get historical round-level scoring and strokes-gained data.

        This is the main endpoint for building your own models.

        Args:
            tour: Tour code
            event_id: Specific event ID (optional)
            year: Year to filter by (optional)
            player_id: Data Golf player ID (optional)
            file_format: 'json' or 'csv'

        Returns:
            List of round-level data with scoring and strokes-gained
        """
        params = {"tour": tour, "file_format": file_format}
        if event_id:
            params["event_id"] = event_id
        if year:
            params["year"] = year
        if player_id:
            params["player_id"] = player_id

        data = self._get_with_backoff("historical-raw-data/rounds", params)

        rounds = []
        for r in data:
            rounds.append(
                DataGolfHistoricalRound(
                    dg_id=r.get("dg_id"),
                    player_name=r.get("player_name", ""),
                    event_id=r.get("event_id", ""),
                    event_name=r.get("event_name"),
                    round_num=r.get("round_num", 0),
                    course_num=r.get("course_num"),
                    course_par=r.get("course_par"),
                    score=r.get("score"),
                    sg_total=r.get("sg_total"),
                    sg_ott=r.get("sg_ott"),
                    sg_app=r.get("sg_app"),
                    sg_arg=r.get("sg_arg"),
                    sg_putt=r.get("sg_putt"),
                    driving_acc=r.get("driving_acc"),
                    driving_dist=r.get("driving_dist"),
                    gir=r.get("gir"),
                    prox_fw=r.get("prox_fw"),
                    prox_rgh=r.get("prox_rgh"),
                    scrambling=r.get("scrambling"),
                )
            )
        return rounds

    # =========================================================================
    # HISTORICAL EVENT STATS ENDPOINTS
    # =========================================================================

    def get_historical_event_ids(
        self,
        tour: Optional[str] = None,
        file_format: str = "json",
    ) -> list[dict]:
        """Get list of event IDs for historical event stats queries.

        Args:
            tour: Optional tour filter
            file_format: 'json' or 'csv'

        Returns:
            List of events with their IDs
        """
        params = {"file_format": file_format}
        if tour:
            params["tour"] = tour

        return self._get_with_backoff("historical-event-data/event-list", params)

    def get_event_finishes(
        self,
        tour: TOUR_CODES = "pga",
        event_id: Optional[str] = None,
        year: Optional[int] = None,
        player_id: Optional[int] = None,
        file_format: str = "json",
    ) -> list[DataGolfEventResult]:
        """Get historical event finishes, earnings, and FedExCup points.

        Args:
            tour: Tour code
            event_id: Specific event ID (optional)
            year: Year to filter by (optional)
            player_id: Data Golf player ID (optional)
            file_format: 'json' or 'csv'

        Returns:
            List of event results with finish positions and earnings
        """
        params = {"tour": tour, "file_format": file_format}
        if event_id:
            params["event_id"] = event_id
        if year:
            params["year"] = year
        if player_id:
            params["player_id"] = player_id

        data = self._get_with_backoff("historical-event-data/finishes", params)

        results = []
        for r in data:
            results.append(
                DataGolfEventResult(
                    dg_id=r.get("dg_id"),
                    player_name=r.get("player_name", ""),
                    event_id=r.get("event_id", ""),
                    event_name=r.get("event_name"),
                    season=r.get("season"),
                    finish_position=r.get("finish"),
                    finish_numeric=r.get("finish_num"),
                    earnings=r.get("earnings"),
                    fedexcup_pts=r.get("fedexcup_pts"),
                    dg_pts=r.get("dg_pts"),
                    total_score=r.get("total"),
                    total_to_par=r.get("total_to_par"),
                )
            )
        return results

    # =========================================================================
    # HISTORICAL ODDS ENDPOINTS
    # =========================================================================

    def get_historical_odds_event_ids(
        self,
        tour: Optional[str] = None,
        file_format: str = "json",
    ) -> list[dict]:
        """Get list of event IDs for historical odds queries.

        Args:
            tour: Optional tour filter
            file_format: 'json' or 'csv'

        Returns:
            List of events with odds data available
        """
        params = {"file_format": file_format}
        if tour:
            params["tour"] = tour

        return self._get_with_backoff("historical-odds/event-list", params)

    def get_historical_outrights(
        self,
        tour: TOUR_CODES = "pga",
        event_id: Optional[str] = None,
        year: Optional[int] = None,
        book: Optional[str] = None,
        market: str = "win",
        odds_format: str = "american",
        file_format: str = "json",
    ) -> list[DataGolfHistoricalOdds]:
        """Get historical opening and closing outright odds.

        Useful for backtesting betting strategies.

        Args:
            tour: Tour code
            event_id: Specific event ID (optional)
            year: Year to filter by (optional)
            book: Sportsbook to filter by (optional)
            market: 'win', 'top_5', 'top_10', 'top_20', 'make_cut'
            odds_format: 'american', 'decimal', or 'percent'
            file_format: 'json' or 'csv'

        Returns:
            List of historical odds with opening and closing lines
        """
        params = {
            "tour": tour,
            "market": market,
            "odds_format": odds_format,
            "file_format": file_format,
        }
        if event_id:
            params["event_id"] = event_id
        if year:
            params["year"] = year
        if book:
            params["book"] = book

        data = self._get_with_backoff("historical-odds/outrights", params)

        odds_list = []
        for o in data:
            odds_list.append(
                DataGolfHistoricalOdds(
                    event_id=o.get("event_id", ""),
                    event_name=o.get("event_name"),
                    dg_id=o.get("dg_id"),
                    player_name=o.get("player_name", ""),
                    open_win_odds=o.get("open_win"),
                    close_win_odds=o.get("close_win"),
                    open_top_5_odds=o.get("open_top_5"),
                    close_top_5_odds=o.get("close_top_5"),
                    open_top_10_odds=o.get("open_top_10"),
                    close_top_10_odds=o.get("close_top_10"),
                    open_top_20_odds=o.get("open_top_20"),
                    close_top_20_odds=o.get("close_top_20"),
                    book=o.get("book"),
                )
            )
        return odds_list

    def get_historical_matchups(
        self,
        tour: TOUR_CODES = "pga",
        event_id: Optional[str] = None,
        year: Optional[int] = None,
        book: Optional[str] = None,
        odds_format: str = "american",
        file_format: str = "json",
    ) -> list[dict]:
        """Get historical matchup odds.

        Args:
            tour: Tour code
            event_id: Specific event ID (optional)
            year: Year to filter by (optional)
            book: Sportsbook to filter by (optional)
            odds_format: 'american', 'decimal', or 'percent'
            file_format: 'json' or 'csv'

        Returns:
            List of historical matchup odds
        """
        params = {
            "tour": tour,
            "odds_format": odds_format,
            "file_format": file_format,
        }
        if event_id:
            params["event_id"] = event_id
        if year:
            params["year"] = year
        if book:
            params["book"] = book

        return self._get_with_backoff("historical-odds/matchups", params)

    # =========================================================================
    # HISTORICAL DFS DATA ENDPOINTS
    # =========================================================================

    def get_historical_dfs_event_ids(
        self,
        tour: Optional[str] = None,
        file_format: str = "json",
    ) -> list[dict]:
        """Get list of event IDs for historical DFS queries.

        Args:
            tour: Optional tour filter
            file_format: 'json' or 'csv'

        Returns:
            List of events with DFS data available
        """
        params = {"file_format": file_format}
        if tour:
            params["tour"] = tour

        return self._get_with_backoff("historical-dfs/event-list", params)

    def get_historical_dfs_points(
        self,
        tour: TOUR_CODES = "pga",
        event_id: Optional[str] = None,
        year: Optional[int] = None,
        site: str = "draftkings",
        file_format: str = "json",
    ) -> list[dict]:
        """Get historical DFS points and salaries.

        Args:
            tour: Tour code
            event_id: Specific event ID (optional)
            year: Year to filter by (optional)
            site: 'draftkings' or 'fanduel'
            file_format: 'json' or 'csv'

        Returns:
            List of DFS results with points and salaries
        """
        params = {
            "tour": tour,
            "site": site,
            "file_format": file_format,
        }
        if event_id:
            params["event_id"] = event_id
        if year:
            params["year"] = year

        return self._get_with_backoff("historical-dfs/points", params)

    # =========================================================================
    # CONVENIENCE / HELPER METHODS
    # =========================================================================

    def get_player_by_name(self, name: str) -> Optional[DataGolfPlayer]:
        """Find a player by name (case-insensitive partial match).

        Args:
            name: Player name to search for

        Returns:
            DataGolfPlayer if found, None otherwise
        """
        players = self.get_player_list()
        name_lower = name.lower()

        # Try exact match first
        for p in players:
            if p.player_name.lower() == name_lower:
                return p

        # Then partial match
        for p in players:
            if name_lower in p.player_name.lower():
                return p

        return None

    def get_player_by_dg_id(self, dg_id: int) -> Optional[DataGolfPlayer]:
        """Find a player by their Data Golf ID.

        Args:
            dg_id: Data Golf player ID

        Returns:
            DataGolfPlayer if found, None otherwise
        """
        players = self.get_player_list()
        for p in players:
            if p.dg_id == dg_id:
                return p
        return None

    def get_best_bets(
        self,
        tour: TOUR_CODES = "pga",
        market: str = "win",
        min_edge_pct: float = 5.0,
    ) -> list[dict]:
        """Find bets with positive edge according to Data Golf model.

        Compares Data Golf's fair odds against sportsbook odds to find value.

        Args:
            tour: Tour code
            market: Market type ('win', 'top_5', 'top_10', 'top_20', 'make_cut')
            min_edge_pct: Minimum edge percentage (5.0 = 5%)

        Returns:
            List of bets with positive edge, sorted by edge descending
        """
        result = self.get_outright_odds(tour=tour, market=market)
        odds_list = result.get("odds", [])

        def odds_to_prob(odds_str):
            """Convert American odds string to implied probability."""
            if not odds_str:
                return None
            odds = int(str(odds_str).replace("+", ""))
            if odds > 0:
                return 100 / (odds + 100)
            else:
                return abs(odds) / (abs(odds) + 100)

        bets = []
        for o in odds_list:
            dg_odds = o.get("datagolf", {})
            dg_fair_str = dg_odds.get("baseline_history_fit")
            dk_str = o.get("draftkings")

            if not dg_fair_str or not dk_str:
                continue

            dg_prob = odds_to_prob(dg_fair_str)
            dk_prob = odds_to_prob(dk_str)

            if dg_prob and dk_prob and dg_prob > dk_prob:
                edge_pct = ((dg_prob / dk_prob) - 1) * 100
                if edge_pct >= min_edge_pct:
                    bets.append({
                        "player_name": o.get("player_name"),
                        "dg_id": o.get("dg_id"),
                        "dg_fair_odds": dg_fair_str,
                        "dg_prob": dg_prob,
                        "draftkings": dk_str,
                        "dk_prob": dk_prob,
                        "edge_pct": edge_pct,
                    })

        bets.sort(key=lambda x: x["edge_pct"], reverse=True)
        return bets

    def get_current_event_info(self, tour: TOUR_CODES = "pga") -> dict:
        """Get comprehensive info about the current/next event.

        Combines field updates, predictions, skill decompositions, and odds
        into one comprehensive data package.

        Args:
            tour: Tour code

        Returns:
            Dict with field, predictions, odds, decompositions, and event metadata
        """
        field = self.get_field_updates(tour=tour)
        predictions = self.get_pre_tournament_predictions(tour=tour)
        odds = self.get_outright_odds(tour=tour, market="win")
        decompositions = self.get_player_skill_decompositions(tour=tour)

        return {
            "event_name": predictions.get("event_name"),
            "course_name": decompositions.get("course_name"),
            "last_updated": predictions.get("last_updated"),
            "field_size": len(field),
            "field": field,
            "predictions": predictions.get("predictions", []),
            "odds": odds,
            "decompositions": decompositions.get("players", []),
        }

    def close(self):
        """Close the HTTP client."""
        self.client.close()
