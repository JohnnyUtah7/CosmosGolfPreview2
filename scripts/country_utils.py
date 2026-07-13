"""
Country + flag helpers.

This project stores player countries primarily as 3-letter codes (often ISO-3166 alpha-3).
To render consistent flags in HTML (including ENG/SCO/WAL which aren't ISO countries),
we convert codes to FlagCDN slugs.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Optional


@dataclass(frozen=True)
class FlagRender:
    """How to render a country flag."""

    # If set, render as <img> from FlagCDN using this slug (e.g. "us", "gb-eng").
    flagcdn_slug: Optional[str]
    # A human-friendly label (for alt/aria).
    label: str


# Non-ISO "country" codes that appear in golf/OWGR contexts.
# FlagCDN supports UK subdivisions as: gb-eng, gb-sct, gb-wls, gb-nir.
SPECIAL_FLAGCDN_SLUGS: dict[str, FlagRender] = {
    "ENG": FlagRender(flagcdn_slug="gb-eng", label="England"),
    "SCO": FlagRender(flagcdn_slug="gb-sct", label="Scotland"),
    "WAL": FlagRender(flagcdn_slug="gb-wls", label="Wales"),
    "NIR": FlagRender(flagcdn_slug="gb-nir", label="Northern Ireland"),
}

# A small fallback mapping used when pycountry isn't installed or doesn't recognize a code.
# Keep this short; the audit script will report any unknowns so we can add as needed.
FALLBACK_ISO3_TO_ISO2: dict[str, str] = {
    "USA": "US",
    "CAN": "CA",
    "MEX": "MX",
    "ARG": "AR",
    "COL": "CO",
    "CHI": "CL",  # common sports code for Chile
    "BRA": "BR",
    "URU": "UY",
    "VEN": "VE",
    "ESP": "ES",
    "FRA": "FR",
    "GER": "DE",
    "NED": "NL",
    "BEL": "BE",
    "SUI": "CH",
    "AUT": "AT",
    "DEN": "DK",
    "NOR": "NO",
    "SWE": "SE",
    "FIN": "FI",
    "IRL": "IE",
    "GBR": "GB",
    "RSA": "ZA",
    "AUS": "AU",
    "NZL": "NZ",
    "JPN": "JP",
    "KOR": "KR",
    "CHN": "CN",
    "TPE": "TW",
    "IND": "IN",
    "VEN": "VE",
    "PRI": "PR",
}


def normalize_country_code(code: str | None) -> str:
    return (code or "").strip().upper()


def _iso3_to_iso2_pycountry(code: str) -> Optional[str]:
    try:
        import pycountry  # type: ignore
    except Exception:
        return None

    try:
        rec = pycountry.countries.get(alpha_3=code)
        if rec and getattr(rec, "alpha_2", None):
            return str(rec.alpha_2).upper()
    except Exception:
        return None
    return None


def iso3_to_iso2(code: str | None) -> Optional[str]:
    c = normalize_country_code(code)
    if not c:
        return None
    iso2 = _iso3_to_iso2_pycountry(c)
    if iso2:
        return iso2
    return FALLBACK_ISO3_TO_ISO2.get(c)


def country_code_to_flag_render(code: str | None) -> Optional[FlagRender]:
    c = normalize_country_code(code)
    if not c:
        return None

    if c in SPECIAL_FLAGCDN_SLUGS:
        return SPECIAL_FLAGCDN_SLUGS[c]

    iso2 = iso3_to_iso2(c)
    if not iso2:
        return None

    return FlagRender(flagcdn_slug=iso2.lower(), label=iso2.upper())


def country_display_html(*, country_code: str | None, owgr: str | None = None) -> str:
    """Return HTML for the country line (flag + code + optional OWGR)."""
    code = normalize_country_code(country_code)
    owgr_txt = (owgr or "").strip()

    parts: list[str] = []

    if code:
        fr = country_code_to_flag_render(code)
        if fr and fr.flagcdn_slug:
            # SVG scales crisply at any size; avoids blur on Retina.
            img = (
                f'<img class="flag-img" src="https://flagcdn.com/{escape(fr.flagcdn_slug)}.svg" '
                f'width="20" height="15" loading="lazy" alt="{escape(fr.label)} flag" />'
            )
            parts.append(f'{img} <span class="country-code">{escape(code)}</span>')
        else:
            parts.append(f'<span class="country-code">{escape(code)}</span>')

    if owgr_txt:
        parts.append(f'<span class="owgr">OWGR #{escape(owgr_txt)}</span>')

    if not parts:
        return "—"

    # Use a centered dot between left/right groups to match existing style.
    return " · ".join(parts)

