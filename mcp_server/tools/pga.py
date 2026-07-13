"""Client for BallDontLie PGA API to fetch tournament and player data."""
from __future__ import annotations

import httpx
from datetime import datetime
import random
import time
from typing import Optional, Any
from ..config import BALLDONTLIE_API_KEY, BALLDONTLIE_API_BASE_URL


class PGAAPIClient:
    """Client for interacting with BallDontLie PGA API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the PGA API client.

        Args:
            api_key: BallDontLie API key. If not provided, uses config.
        """
        self.api_key = api_key or BALLDONTLIE_API_KEY
        self.base_url = BALLDONTLIE_API_BASE_URL
        self.client = httpx.Client(timeout=30.0)
        self._max_retries = 6

        if not self.api_key:
            raise ValueError("BALLDONTLIE_API_KEY is required. Set it in .env file.")

        # Set up headers with API key
        self.headers = {
            "Authorization": self.api_key
        }

    @staticmethod
    def _parse_retry_after_seconds(value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        v = value.strip()
        # Retry-After can be seconds or an HTTP date; handle seconds only.
        try:
            sec = float(v)
            if sec >= 0:
                return sec
        except Exception:
            return None
        return None

    def _get_with_backoff(self, url: str, *, params: dict[str, Any]) -> httpx.Response:
        """
        Wrapper for GET requests that handles 429 rate limits gracefully.

        Strategy:
        - If we receive 429, respect Retry-After when present, else exponential backoff.
        - Retry some transient 5xx errors too.
        """
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                resp = self.client.get(url, headers=self.headers, params=params)

                if resp.status_code == 429:
                    retry_after = self._parse_retry_after_seconds(resp.headers.get("Retry-After"))
                    base = retry_after if retry_after is not None else (0.75 * (2 ** attempt))
                    # Small jitter to avoid thundering herd.
                    sleep_s = min(20.0, base + random.uniform(0.0, 0.35))
                    time.sleep(sleep_s)
                    continue

                # Retry on transient server errors
                if 500 <= resp.status_code <= 599 and attempt < self._max_retries - 1:
                    time.sleep(min(10.0, 0.4 * (2 ** attempt)))
                    continue

                resp.raise_for_status()
                return resp
            except Exception as e:
                last_exc = e
                # Small backoff on network errors
                if attempt < self._max_retries - 1:
                    time.sleep(min(10.0, 0.4 * (2 ** attempt)))
                    continue
                raise

        # Should be unreachable, but keep a helpful error if it happens.
        raise RuntimeError(f"BallDontLie request failed after {self._max_retries} attempts") from last_exc

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.client.close()

    def get_players(
        self,
        search: Optional[str] = None,
        country: Optional[str] = None,
        per_page: int = 25,
        cursor: Optional[str] = None
    ) -> dict:
        """Get PGA Tour players.

        Args:
            search: Search by player name
            country: Filter by country code (e.g., 'USA')
            per_page: Results per page (max 100, default 25)
            cursor: Pagination cursor for next page

        Returns:
            Dictionary with 'data' (list of players) and 'meta' (pagination info)
        """
        url = f"{self.base_url}/players"
        params = {"per_page": min(per_page, 100)}

        if search:
            params["search"] = search
        if country:
            params["country"] = country
        if cursor:
            params["cursor"] = cursor

        return self._get_with_backoff(url, params=params).json()

    def get_tournaments(
        self,
        season: Optional[int] = None,
        status: Optional[str] = None,
        per_page: int = 25,
        cursor: Optional[str] = None
    ) -> dict:
        """Get PGA Tour tournaments.

        Args:
            season: Filter by season year (e.g., 2026)
            status: Filter by status ('upcoming', 'in_progress', 'completed')
            per_page: Results per page (max 100, default 25)
            cursor: Pagination cursor for next page

        Returns:
            Dictionary with 'data' (list of tournaments) and 'meta' (pagination info)
        """
        url = f"{self.base_url}/tournaments"
        params = {"per_page": min(per_page, 100)}

        if season:
            params["season"] = season
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor

        return self._get_with_backoff(url, params=params).json()

    def get_tournament_results(
        self,
        *,
        season: Optional[int] = None,
        tournament_ids: Optional[list[int]] = None,
        player_ids: Optional[list[int]] = None,
        per_page: int = 100,
        cursor: Optional[str] = None,
    ) -> dict:
        """
        Get leaderboard/results rows.

        NOTE: BallDontLie's PGA `/tournament_results` endpoint may require a paid tier.

        Args:
            season: Filter by season year (e.g., 2026)
            tournament_ids: Filter by tournament IDs
            player_ids: Filter by player IDs
            per_page: Results per page (max 100)
            cursor: Pagination cursor

        Returns:
            Dictionary with 'data' (list of results) and 'meta' (pagination info)
        """
        url = f"{self.base_url}/tournament_results"
        params: dict[str, Any] = {"per_page": min(int(per_page), 100)}

        if season:
            params["season"] = int(season)
        if tournament_ids:
            # BallDontLie expects repeated query params, but their API accepts bracket syntax too.
            params["tournament_ids[]"] = [int(x) for x in tournament_ids]
        if player_ids:
            params["player_ids[]"] = [int(x) for x in player_ids]
        if cursor:
            params["cursor"] = cursor

        return self._get_with_backoff(url, params=params).json()

    def get_courses(
        self,
        search: Optional[str] = None,
        per_page: int = 25,
        cursor: Optional[str] = None
    ) -> dict:
        """Get golf course information.

        Args:
            search: Search by course name
            per_page: Results per page (max 100, default 25)
            cursor: Pagination cursor for next page

        Returns:
            Dictionary with 'data' (list of courses) and 'meta' (pagination info)
        """
        url = f"{self.base_url}/courses"
        params = {"per_page": min(per_page, 100)}

        if search:
            params["search"] = search
        if cursor:
            params["cursor"] = cursor

        return self._get_with_backoff(url, params=params).json()

    def get_next_tournament(self, season: Optional[int] = None) -> Optional[dict]:
        """Get the next upcoming PGA Tour tournament.

        Args:
            season: Season year (defaults to current year)

        Returns:
            Tournament dictionary or None if no upcoming tournaments.
        """
        if not season:
            season = datetime.now().year

        # First try to get upcoming tournaments
        response = self.get_tournaments(season=season, status="upcoming", per_page=100)

        tournaments = response.get("data", [])

        if not tournaments:
            # If no upcoming, check in_progress
            response = self.get_tournaments(season=season, status="in_progress", per_page=1)
            tournaments = response.get("data", [])

        if tournaments:
            return tournaments[0]

        return None

    def get_tournament_by_name(self, name: str, season: Optional[int] = None) -> Optional[dict]:
        """Search for a tournament by name.

        Args:
            name: Tournament name to search for
            season: Season year (optional)

        Returns:
            Tournament dictionary or None if not found.
        """
        params = {"per_page": 100}
        if season:
            params["season"] = season

        url = f"{self.base_url}/tournaments"
        tournaments = self._get_with_backoff(url, params=params).json().get("data", [])

        # Search for tournament by name (case-insensitive)
        name_lower = name.lower()
        for tournament in tournaments:
            if name_lower in tournament.get("name", "").lower():
                return tournament

        return None

    def get_player_by_name(self, name: str) -> Optional[dict]:
        """Search for a player by name.

        Args:
            name: Player name to search for

        Returns:
            Player dictionary or None if not found.
        """
        response = self.get_players(search=name, per_page=1)
        players = response.get("data", [])

        if players:
            return players[0]

        return None

    def get_all_players_paginated(self, max_pages: int = 10) -> list[dict]:
        """Get multiple pages of players.

        Args:
            max_pages: Maximum number of pages to fetch (default 10)

        Returns:
            List of all player dictionaries.
        """
        all_players = []
        cursor = None

        for _ in range(max_pages):
            response = self.get_players(per_page=100, cursor=cursor)
            players = response.get("data", [])
            all_players.extend(players)

            # Check if there's a next page
            meta = response.get("meta", {})
            cursor = meta.get("next_cursor")

            if not cursor:
                break

        return all_players

    def get_all_tournaments_for_season(self, season: int) -> list[dict]:
        """Get all tournaments for a given season.

        Args:
            season: Season year (e.g., 2026)

        Returns:
            List of all tournament dictionaries for that season.
        """
        all_tournaments = []
        cursor = None

        while True:
            response = self.get_tournaments(season=season, per_page=100, cursor=cursor)
            tournaments = response.get("data", [])
            all_tournaments.extend(tournaments)

            # Check if there's a next page
            meta = response.get("meta", {})
            cursor = meta.get("next_cursor")

            if not cursor:
                break

        return all_tournaments

    def close(self):
        """Close the HTTP client."""
        self.client.close()
