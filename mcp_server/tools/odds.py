"""Client for The Odds API to fetch golf betting odds."""
import httpx
from datetime import datetime
from typing import Optional
from ..config import ODDS_API_KEY, ODDS_API_BASE_URL, SUPPORTED_REGIONS
from ..models.schemas import TournamentOdds, BookmakerOdds, PlayerOdds


class OddsAPIClient:
    """Client for interacting with The Odds API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Odds API client.

        Args:
            api_key: The Odds API key. If not provided, uses config.
        """
        self.api_key = api_key or ODDS_API_KEY
        self.base_url = ODDS_API_BASE_URL
        self.client = httpx.Client(timeout=30.0)

        if not self.api_key:
            raise ValueError("ODDS_API_KEY is required. Set it in .env file.")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.client.close()

    def get_golf_sports(self) -> list[dict]:
        """Get all available golf sports/tournaments.

        Returns:
            List of golf sport objects with keys and titles.
        """
        url = f"{self.base_url}/sports"
        params = {"apiKey": self.api_key}

        response = self.client.get(url, params=params)
        response.raise_for_status()

        all_sports = response.json()

        # Filter for golf sports
        golf_sports = [
            sport for sport in all_sports
            if sport.get("key", "").startswith("golf_")
        ]

        return golf_sports

    def get_tournament_odds(
        self,
        sport_key: str,
        regions: Optional[list[str]] = None,
        markets: str = "outrights",
        odds_format: str = "american",
        return_multiple_markets: bool = False
    ) -> Optional[TournamentOdds]:
        """Get odds for a specific golf tournament.

        Args:
            sport_key: The sport key from The Odds API (e.g., 'golf_pga_championship')
            regions: List of regions (default: ['us'])
            markets: Market type (default: 'outrights' for tournament winner)
            odds_format: 'american' or 'decimal' (default: 'american')

        Returns:
            TournamentOdds object with all bookmaker odds, or None if no odds available.
        """
        if regions is None:
            regions = SUPPORTED_REGIONS

        url = f"{self.base_url}/sports/{sport_key}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": ",".join(regions),
            "markets": markets,
            "oddsFormat": odds_format
        }

        response = self.client.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        # Check response headers for quota info
        headers = response.headers
        remaining = headers.get("x-requests-remaining")
        used = headers.get("x-requests-used")

        if remaining:
            print(f"API Requests Remaining: {remaining}")
        if used:
            print(f"API Requests Used: {used}")

        # The Odds API returns a list of events
        if not data or len(data) == 0:
            print(f"No odds data available for {sport_key}")
            return None

        # For golf, typically there's one main event (the tournament)
        event = data[0]

        # Parse bookmakers
        bookmakers = []
        for bookmaker_data in event.get("bookmakers", []):
            # Parse player odds from markets
            players = []
            for market in bookmaker_data.get("markets", []):
                if market.get("key") == markets:
                    for outcome in market.get("outcomes", []):
                        player_odds = PlayerOdds(
                            player_name=outcome.get("name"),
                            odds=outcome.get("price")
                        )
                        players.append(player_odds)

            bookmaker = BookmakerOdds(
                bookmaker_key=bookmaker_data.get("key"),
                bookmaker_name=bookmaker_data.get("title"),
                last_update=datetime.fromisoformat(
                    bookmaker_data.get("last_update").replace("Z", "+00:00")
                ),
                players=players
            )
            bookmakers.append(bookmaker)

        # Create TournamentOdds object
        commence_time = None
        if event.get("commence_time"):
            commence_time = datetime.fromisoformat(
                event.get("commence_time").replace("Z", "+00:00")
            )

        tournament_odds = TournamentOdds(
            sport_key=event.get("sport_key"),
            sport_title=event.get("sport_title"),
            commence_time=commence_time,
            bookmakers=bookmakers
        )

        return tournament_odds

    def get_upcoming_pga_tournament(self) -> Optional[tuple[str, str]]:
        """Find the next upcoming PGA tournament.

        Returns:
            Tuple of (sport_key, sport_title) for the next PGA tournament,
            or None if no upcoming tournaments found.
        """
        golf_sports = self.get_golf_sports()

        # Filter for PGA tournaments (exclude majors for now, can customize)
        pga_tournaments = [
            sport for sport in golf_sports
            if "pga" in sport.get("key", "").lower()
        ]

        if not pga_tournaments:
            print("No PGA tournaments found")
            return None

        # Return the first one (they're typically sorted by date)
        next_tournament = pga_tournaments[0]
        return (next_tournament.get("key"), next_tournament.get("title"))

    def get_all_sportsbooks_for_tournament(
        self,
        sport_key: str
    ) -> dict[str, list[PlayerOdds]]:
        """Get odds from all available sportsbooks for a tournament.

        Args:
            sport_key: The sport key from The Odds API

        Returns:
            Dictionary mapping bookmaker names to their player odds.
        """
        tournament_odds = self.get_tournament_odds(sport_key)

        if not tournament_odds:
            return {}

        sportsbooks = {}
        for bookmaker in tournament_odds.bookmakers:
            sportsbooks[bookmaker.bookmaker_name] = bookmaker.players

        return sportsbooks

    def get_best_odds_aggregated(
        self,
        sport_key: str
    ) -> dict[str, tuple[str, int]]:
        """Get the best odds for each player across all sportsbooks.

        Args:
            sport_key: The sport key from The Odds API

        Returns:
            Dictionary mapping player names to (bookmaker_name, best_odds).
        """
        tournament_odds = self.get_tournament_odds(sport_key)

        if not tournament_odds:
            return {}

        best_odds = {}

        for player_name in tournament_odds.get_all_players():
            result = tournament_odds.get_player_best_odds(player_name)
            if result:
                best_odds[player_name] = result

        return best_odds

    def get_matchup_odds(
        self,
        sport_key: str,
        regions: Optional[list[str]] = None,
        odds_format: str = "american"
    ) -> list[dict]:
        """
        Get head-to-head matchup odds for a golf tournament.

        Args:
            sport_key: The sport key from The Odds API
            regions: List of regions (default: ['us'])
            odds_format: 'american' or 'decimal' (default: 'american')

        Returns:
            List of matchup dictionaries with player1, player2, and odds
        """
        if regions is None:
            regions = SUPPORTED_REGIONS

        url = f"{self.base_url}/sports/{sport_key}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": ",".join(regions),
            "markets": "h2h",  # Head-to-head market
            "oddsFormat": odds_format
        }

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Track quota
            headers = response.headers
            remaining = headers.get("x-requests-remaining")
            if remaining:
                print(f"API Requests Remaining: {remaining}")

            matchups = []

            # Parse matchup data
            for event in data:
                # Each event is a matchup between 2 players
                home_team = event.get("home_team")
                away_team = event.get("away_team")

                if not home_team or not away_team:
                    continue

                matchup = {
                    "id": event.get("id"),
                    "commence_time": event.get("commence_time"),
                    "player1": home_team,
                    "player2": away_team,
                    "bookmakers": []
                }

                # Parse bookmaker odds for this matchup
                for bookmaker in event.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        if market.get("key") == "h2h":
                            outcomes = market.get("outcomes", [])
                            if len(outcomes) >= 2:
                                bookmaker_odds = {
                                    "bookmaker_name": bookmaker.get("title"),
                                    "player1_odds": None,
                                    "player2_odds": None
                                }

                                for outcome in outcomes:
                                    if outcome.get("name") == home_team:
                                        bookmaker_odds["player1_odds"] = outcome.get("price")
                                    elif outcome.get("name") == away_team:
                                        bookmaker_odds["player2_odds"] = outcome.get("price")

                                matchup["bookmakers"].append(bookmaker_odds)

                if matchup["bookmakers"]:
                    matchups.append(matchup)

            print(f"Found {len(matchups)} head-to-head matchups")
            return matchups

        except Exception as e:
            print(f"Error fetching matchup odds: {e}")
            print("Note: Matchup markets may not be available for this golf event")
            return []

    def get_all_markets_for_tournament(
        self,
        sport_key: str,
        regions: Optional[list[str]] = None
    ) -> dict:
        """
        Get all available markets for a tournament (outrights + matchups).

        Args:
            sport_key: The sport key from The Odds API
            regions: List of regions (default: ['us'])

        Returns:
            Dictionary with 'outrights' and 'matchups' keys
        """
        result = {
            "outrights": None,
            "matchups": [],
            "has_matchups": False
        }

        # Get tournament winner odds
        result["outrights"] = self.get_tournament_odds(sport_key, regions)

        # Try to get matchup odds
        matchups = self.get_matchup_odds(sport_key, regions)
        result["matchups"] = matchups
        result["has_matchups"] = len(matchups) > 0

        return result

    def close(self):
        """Close the HTTP client."""
        self.client.close()
