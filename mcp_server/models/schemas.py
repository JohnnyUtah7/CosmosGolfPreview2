"""Pydantic models for golf betting data."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PlayerOdds(BaseModel):
    """Odds for a single player from a bookmaker."""
    
    player_name: str
    odds: int = Field(description="American odds format (e.g., +1500, -110)")
    
    @property
    def decimal_odds(self) -> float:
        """Convert American odds to decimal odds."""
        if self.odds > 0:
            return (self.odds / 100) + 1
        else:
            return (100 / abs(self.odds)) + 1
    
    @property
    def implied_probability(self) -> float:
        """Calculate implied probability from odds."""
        if self.odds > 0:
            return 100 / (self.odds + 100)
        else:
            return abs(self.odds) / (abs(self.odds) + 100)


class BookmakerOdds(BaseModel):
    """Odds from a single bookmaker for a tournament."""
    
    bookmaker_key: str
    bookmaker_name: str
    last_update: datetime
    players: list[PlayerOdds] = Field(default_factory=list)


class Tournament(BaseModel):
    """PGA Tour tournament information."""
    
    id: str
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    course: Optional[str] = None
    location: Optional[str] = None
    purse: Optional[float] = None
    status: Optional[str] = None


class TournamentOdds(BaseModel):
    """Complete odds data for a tournament."""
    
    sport_key: str
    sport_title: str
    commence_time: Optional[datetime] = None
    bookmakers: list[BookmakerOdds] = Field(default_factory=list)
    
    def get_player_best_odds(self, player_name: str) -> Optional[tuple[str, int]]:
        """Find the best odds for a player across all bookmakers."""
        best_odds: Optional[int] = None
        best_bookmaker: Optional[str] = None
        
        for bookmaker in self.bookmakers:
            for player in bookmaker.players:
                if player.player_name.lower() == player_name.lower():
                    if best_odds is None or player.odds > best_odds:
                        best_odds = player.odds
                        best_bookmaker = bookmaker.bookmaker_name
        
        if best_odds is not None and best_bookmaker is not None:
            return (best_bookmaker, best_odds)
        return None
    
    def get_all_players(self) -> list[str]:
        """Get a list of all unique players in this tournament's odds."""
        players = set()
        for bookmaker in self.bookmakers:
            for player in bookmaker.players:
                players.add(player.player_name)
        return sorted(list(players))


class PlayerStats(BaseModel):
    """PGA Tour player statistics."""
    
    player_id: str
    player_name: str
    season: int
    tournaments_played: Optional[int] = None
    cuts_made: Optional[int] = None
    wins: Optional[int] = None
    top_10s: Optional[int] = None
    scoring_average: Optional[float] = None
    driving_distance: Optional[float] = None
    driving_accuracy: Optional[float] = None
    gir_percentage: Optional[float] = None
    putting_average: Optional[float] = None
    strokes_gained_total: Optional[float] = None
    strokes_gained_tee_to_green: Optional[float] = None
    strokes_gained_putting: Optional[float] = None


class CachedData(BaseModel):
    """Cached data structure for local storage."""

    last_updated: datetime
    tournaments: list[Tournament] = Field(default_factory=list)
    odds: list[TournamentOdds] = Field(default_factory=list)
    player_stats: dict[str, PlayerStats] = Field(default_factory=dict)


# ============================================================================
# Data Golf API Models
# ============================================================================

class DataGolfPlayer(BaseModel):
    """Player from Data Golf API with unified ID."""

    dg_id: int = Field(description="Data Golf unique player ID")
    player_name: str
    country: Optional[str] = None
    country_code: Optional[str] = None
    amateur: bool = False

    # Optional IDs from other systems
    pga_id: Optional[str] = None
    espn_id: Optional[str] = None


class DataGolfRanking(BaseModel):
    """Player ranking from Data Golf rankings endpoint."""

    dg_id: int
    player_name: str
    country: Optional[str] = None
    owgr: Optional[int] = Field(None, description="Official World Golf Ranking")
    datagolf_rank: Optional[int] = Field(None, description="Data Golf model ranking")
    dg_skill_estimate: Optional[float] = Field(None, description="Data Golf skill estimate")

    # Additional ranking metrics
    primary_tour: Optional[str] = None


class DataGolfFieldPlayer(BaseModel):
    """Player in a tournament field."""

    dg_id: int
    player_name: str
    country: Optional[str] = None
    am: bool = Field(False, description="Is amateur")

    # DraftKings salary info (when available)
    dk_salary: Optional[int] = None
    dk_id: Optional[str] = None

    # FanDuel salary info (when available)
    fd_salary: Optional[int] = None
    fd_id: Optional[str] = None

    # Tee time info (when available)
    r1_teetime: Optional[str] = None
    r2_teetime: Optional[str] = None


class DataGolfTournament(BaseModel):
    """Tournament from Data Golf schedule."""

    event_id: Optional[str] = None
    event_name: str
    tour: str = Field(description="Tour name (e.g., 'pga', 'euro')")
    course: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    # Event metadata
    purse: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DataGolfPrediction(BaseModel):
    """Pre-tournament prediction for a player."""

    dg_id: int
    player_name: str
    country: Optional[str] = None

    # Probabilities (0-1 scale)
    win_prob: Optional[float] = None
    top_5_prob: Optional[float] = None
    top_10_prob: Optional[float] = None
    top_20_prob: Optional[float] = None
    make_cut_prob: Optional[float] = None

    # Model-specific predictions
    baseline_pred: Optional[float] = Field(None, description="Baseline model expected finish")
    baseline_history_fit: Optional[float] = None
    course_history_fit_pred: Optional[float] = Field(None, description="Course-fit model expected finish")


class DataGolfSkillRating(BaseModel):
    """Player skill decomposition ratings."""

    dg_id: int
    player_name: str

    # Overall skill
    sg_total: Optional[float] = Field(None, description="Strokes gained total")

    # Skill components
    sg_ott: Optional[float] = Field(None, description="Strokes gained off the tee")
    sg_app: Optional[float] = Field(None, description="Strokes gained approach")
    sg_arg: Optional[float] = Field(None, description="Strokes gained around the green")
    sg_putt: Optional[float] = Field(None, description="Strokes gained putting")

    # Driving skill breakdown
    driving_acc: Optional[float] = None
    driving_dist: Optional[float] = None


class DataGolfLivePrediction(BaseModel):
    """Live in-tournament prediction for a player."""

    dg_id: int
    player_name: str

    # Current position
    current_pos: Optional[str] = None
    current_score: Optional[int] = None
    thru: Optional[int] = None
    today: Optional[int] = None

    # Live probabilities
    win_prob: Optional[float] = None
    top_5_prob: Optional[float] = None
    top_10_prob: Optional[float] = None
    top_20_prob: Optional[float] = None
    make_cut_prob: Optional[float] = None

    # Expected finish
    proj_finish: Optional[float] = None


class DataGolfOutrightOdds(BaseModel):
    """Outright/finish position odds for a player."""

    dg_id: int
    player_name: str

    # Data Golf fair odds (implied probabilities)
    dg_win_prob: Optional[float] = None
    dg_top_5_prob: Optional[float] = None
    dg_top_10_prob: Optional[float] = None
    dg_top_20_prob: Optional[float] = None
    dg_make_cut_prob: Optional[float] = None

    # Sportsbook odds (American format)
    draftkings_win: Optional[int] = None
    fanduel_win: Optional[int] = None
    betmgm_win: Optional[int] = None
    caesars_win: Optional[int] = None

    # Edge calculations
    win_edge: Optional[float] = Field(None, description="Edge vs average book odds")


class DataGolfMatchup(BaseModel):
    """Head-to-head or 3-ball matchup odds."""

    matchup_type: str = Field(description="'2-ball' or '3-ball'")

    # Players in matchup
    player_1_dg_id: int
    player_1_name: str
    player_2_dg_id: int
    player_2_name: str
    player_3_dg_id: Optional[int] = None
    player_3_name: Optional[str] = None

    # Data Golf fair probabilities
    player_1_dg_prob: Optional[float] = None
    player_2_dg_prob: Optional[float] = None
    player_3_dg_prob: Optional[float] = None
    tie_prob: Optional[float] = None

    # Sportsbook odds
    player_1_book_odds: Optional[int] = None
    player_2_book_odds: Optional[int] = None
    player_3_book_odds: Optional[int] = None


class DataGolfHistoricalRound(BaseModel):
    """Historical round-level scoring data."""

    dg_id: int
    player_name: str
    event_id: str
    event_name: Optional[str] = None

    # Round info
    round_num: int
    course_num: Optional[int] = None
    course_par: Optional[int] = None

    # Scoring
    score: Optional[int] = None
    sg_total: Optional[float] = None
    sg_ott: Optional[float] = None
    sg_app: Optional[float] = None
    sg_arg: Optional[float] = None
    sg_putt: Optional[float] = None

    # Driving stats
    driving_acc: Optional[float] = None
    driving_dist: Optional[float] = None
    gir: Optional[float] = None

    # Putting stats
    prox_fw: Optional[float] = Field(None, description="Proximity from fairway")
    prox_rgh: Optional[float] = Field(None, description="Proximity from rough")
    scrambling: Optional[float] = None


class DataGolfEventResult(BaseModel):
    """Historical event finish/result data."""

    dg_id: int
    player_name: str
    event_id: str
    event_name: Optional[str] = None
    season: Optional[int] = None

    # Finish info
    finish_position: Optional[str] = None
    finish_numeric: Optional[int] = None

    # Earnings
    earnings: Optional[float] = None
    fedexcup_pts: Optional[float] = None
    dg_pts: Optional[float] = None

    # Score
    total_score: Optional[int] = None
    total_to_par: Optional[int] = None


class DataGolfHistoricalOdds(BaseModel):
    """Historical betting odds data."""

    event_id: str
    event_name: Optional[str] = None
    dg_id: int
    player_name: str

    # Opening and closing odds
    open_win_odds: Optional[int] = None
    close_win_odds: Optional[int] = None
    open_top_5_odds: Optional[int] = None
    close_top_5_odds: Optional[int] = None
    open_top_10_odds: Optional[int] = None
    close_top_10_odds: Optional[int] = None
    open_top_20_odds: Optional[int] = None
    close_top_20_odds: Optional[int] = None

    book: Optional[str] = Field(None, description="Sportsbook name")
