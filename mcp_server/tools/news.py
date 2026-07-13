"""Lightweight golf news fetching utilities.

This intentionally avoids paid search APIs by using Google News RSS feeds.
It is designed to be "good enough" for weekly storyline generation and to
degrade gracefully when network access is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import httpx


@dataclass(frozen=True)
class NewsArticle:
    """A minimal representation of a news item."""

    title: str
    url: str
    published_at: Optional[datetime] = None
    source: Optional[str] = None


class GolfNewsClient:
    """Fetch player-related golf news via RSS."""

    def __init__(
        self,
        *,
        client: Optional[httpx.Client] = None,
        user_agent: str = "CosmosGolfBetting/1.0 (news fetcher)",
        timeout_seconds: float = 30.0,
    ):
        self._owns_client = client is None
        self.client = client or httpx.Client(
            timeout=timeout_seconds,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )

    def __enter__(self) -> "GolfNewsClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._owns_client:
            self.client.close()

    @staticmethod
    def _parse_rfc822_date(value: str) -> Optional[datetime]:
        # Google News RSS uses RFC822 like: "Mon, 19 Jan 2026 12:34:56 GMT"
        try:
            dt = datetime.strptime(value.strip(), "%a, %d %b %Y %H:%M:%S %Z")
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    def search_player_news(
        self,
        player_name: str,
        *,
        tournament_name: Optional[str] = None,
        days: int = 14,
        max_results: int = 6,
        locale: str = "US:en",
    ) -> list[NewsArticle]:
        """Search recent news for a player.

        Args:
            player_name: Player full name.
            tournament_name: Optional tournament name to bias results.
            days: Only keep articles newer than this many days (best-effort).
            max_results: Max number of results to return.
            locale: Google News locale (default US:en).
        """
        query = f'"{player_name}" golf'
        if tournament_name:
            query = f'{query} "{tournament_name}"'

        # Locale breakdown: hl/en-US, gl/US, ceid/US:en
        gl, _, ceid = locale.partition(":")
        hl = "en-US" if locale == "US:en" else "en-US"

        rss_url = (
            "https://news.google.com/rss/search?q="
            + quote_plus(query)
            + f"&hl={quote_plus(hl)}&gl={quote_plus(gl)}&ceid={quote_plus(locale)}"
        )

        response = self.client.get(rss_url)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        channel = root.find("channel")
        if channel is None:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        articles: list[NewsArticle] = []

        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date_raw = (item.findtext("pubDate") or "").strip()
            source = (item.findtext("source") or "").strip() or None

            # Google News titles are often formatted like: "Headline - Publisher"
            # Keep the headline clean; store publisher in `source` when possible.
            if " - " in title:
                headline, possible_source = title.rsplit(" - ", 1)
                if possible_source and len(possible_source) <= 60:
                    title = headline.strip()
                    source = source or possible_source.strip()

            if not title or not link:
                continue

            published_at = self._parse_rfc822_date(pub_date_raw) if pub_date_raw else None
            if published_at and published_at < cutoff:
                continue

            articles.append(
                NewsArticle(
                    title=title,
                    url=link,
                    published_at=published_at,
                    source=source,
                )
            )

            if len(articles) >= max_results:
                break

        return articles

