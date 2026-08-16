#!/usr/bin/env python3
"""
Fetch weather forecast for any PGA Tour tournament location.

Uses free NOAA weather API (National Weather Service) for accurate government data.
No API key required - completely free.

Note: NOAA only covers US territories. For international events (Scotland, England,
Japan, etc.) the script will print a warning and save a placeholder.

Usage:
    # Auto-detect this week's tournament from schedule
    python scripts/fetch_tournament_weather.py

    # Specify tournament
    python scripts/fetch_tournament_weather.py --tournament "Masters Tournament" --year 2026
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ── Coordinates lookup for known PGA Tour venues ────────────────────────
# Keys are normalized location strings (lowercase city + state/country).
# Values are (latitude, longitude) tuples.
VENUE_COORDINATES: dict[str, tuple[float, float]] = {
    # Hawaii
    "kapalua, maui, hawaii":        (20.9986, -156.6618),
    "honolulu, hawaii":             (21.2907, -157.8425),
    # California
    "la quinta, california":        (33.6633, -116.3100),
    "san diego, california":        (32.9003, -117.2543),
    "pebble beach, california":     (36.5685, -121.9476),
    "pacific palisades, california": (34.0366, -118.5178),
    # Arizona
    "scottsdale, arizona":          (33.6275, -111.8914),
    # Florida
    "palm beach gardens, florida":  (26.8234, -80.1387),
    "orlando, florida":             (28.4585, -81.4555),
    "ponte vedra beach, florida":   (30.2376, -81.3916),
    "palm harbor, florida":         (28.0834, -82.7637),
    "doral, florida":               (25.8195, -80.3553),
    # Puerto Rico
    "rio grande, puerto rico":      (18.3802, -65.8310),
    # Texas
    "houston, texas":               (29.7604, -95.3698),
    "san antonio, texas":           (29.4600, -98.5254),
    "mckinney, texas":              (33.1972, -96.6398),
    "fort worth, texas":            (32.7349, -97.3903),
    "austin, texas":                (30.2672, -97.7431),
    # Georgia
    "augusta, georgia":             (33.4735, -82.0105),
    "atlanta, georgia":             (33.7684, -84.3416),
    "st. simons island, georgia":   (31.1544, -81.3887),
    # South Carolina
    "hilton head island, south carolina": (32.2163, -80.7526),
    "myrtle beach, south carolina": (33.6891, -78.8867),
    # Louisiana
    "avondale, louisiana":          (29.9116, -90.2056),
    # North Carolina
    "charlotte, north carolina":    (35.2271, -80.8431),
    "greensboro, north carolina":   (36.0726, -79.7920),
    "asheville, north carolina":    (35.5951, -82.5515),
    # Tennessee
    "memphis, tennessee":           (35.1495, -90.0490),
    # Ohio
    "dublin, ohio":                 (40.0992, -83.1141),
    # Missouri
    "st. louis, missouri":          (38.6270, -90.1994),
    # Connecticut
    "cromwell, connecticut":        (41.5959, -72.6554),
    # Illinois
    "silvis, illinois":             (41.5120, -90.4158),
    "medinah, illinois":            (41.9744, -88.0403),
    # Minnesota
    "blaine, minnesota":            (45.1608, -93.2349),
    # Michigan
    "detroit, michigan":            (42.3314, -83.0458),
    # Pennsylvania
    "newtown square, pennsylvania": (39.9865, -75.4166),
    # New York
    "southampton, new york":        (40.8843, -72.3893),
    # Kentucky
    "louisville, kentucky":         (38.2527, -85.7585),
    # Utah
    "ivins, utah":                  (37.1683, -113.6811),
    # Canada (TPC Toronto at Osprey Valley is in Caledon/Alton, ON)
    "toronto, ontario, canada":     (43.9206, -80.0855),
    "caledon, ontario, canada":     (43.9206, -80.0855),
    "hamilton, ontario, canada":    (43.2557, -79.8711),
    # Scotland (The Renaissance Club, North Berwick — Genesis Scottish Open)
    "north berwick, scotland":      (56.0546, -2.6612),
    # England (Royal Birkdale, Southport — The Open Championship)
    "southport, england":           (53.6417, -3.0195),
}


def _normalize_location(location: str) -> str:
    """Normalize a location string for lookup."""
    return location.lower().strip()


def _slugify(name: str) -> str:
    """Convert tournament name to slug."""
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def load_schedule() -> dict:
    """Load the PGA schedule database."""
    schedule_path = ROOT / "data" / "pga_schedule_2026.json"
    if schedule_path.exists():
        return json.loads(schedule_path.read_text(encoding="utf-8"))
    return {"tournaments": [], "fall_schedule": []}


def find_tournament(schedule: dict, tournament_name: str) -> dict | None:
    """Find a tournament in the schedule by name (fuzzy match)."""
    slug = _slugify(tournament_name)
    all_tournaments = schedule.get("tournaments", []) + schedule.get("fall_schedule", [])

    for t in all_tournaments:
        if t.get("slug") == slug:
            return t
        if tournament_name.lower() in t.get("name", "").lower():
            return t

    return None


def get_coordinates(location: str) -> tuple[float, float] | None:
    """
    Look up coordinates for a tournament location.

    First checks the built-in VENUE_COORDINATES dict,
    then tries partial matching on city name.
    Returns (lat, lon) or None.
    """
    norm = _normalize_location(location)

    # Direct lookup
    if norm in VENUE_COORDINATES:
        return VENUE_COORDINATES[norm]

    # Partial match: check if any key's city matches
    city_from_input = norm.split(",")[0].strip()
    for key, coords in VENUE_COORDINATES.items():
        city_from_key = key.split(",")[0].strip()
        if city_from_input == city_from_key:
            return coords

    return None


def get_noaa_forecast(lat: float, lon: float) -> dict:
    """
    Get NOAA weather forecast for given coordinates.

    NOAA API docs: https://www.weather.gov/documentation/services-web-api
    """
    # Step 1: Get grid endpoint for coordinates
    points_url = f"https://api.weather.gov/points/{lat},{lon}"
    headers = {"User-Agent": "CosmosGolfBetting/1.0 (tournament weather)"}

    try:
        response = requests.get(points_url, headers=headers, timeout=10)
        response.raise_for_status()
        points_data = response.json()

        # Extract forecast URL
        forecast_url = points_data["properties"]["forecast"]

        # Step 2: Get detailed forecast
        forecast_response = requests.get(forecast_url, headers=headers, timeout=10)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()

        return forecast_data

    except Exception as e:
        print(f"  Warning: Error fetching NOAA forecast: {e}")
        return {}


def format_golf_weather_summary(forecast_data: dict) -> str:
    """Format NOAA forecast into concise golf-relevant summary."""
    if not forecast_data or "properties" not in forecast_data:
        return "Weather forecast unavailable."

    periods = forecast_data["properties"]["periods"]

    if not periods:
        return "Weather forecast unavailable."

    # Get tournament week forecast (next 7-10 days)
    tournament_periods = periods[:8]  # First 4 days (day + night each)

    # Extract key conditions
    temps = []
    wind_speeds = []
    rain_chance = False
    conditions = []

    for period in tournament_periods:
        if period.get("isDaytime"):  # Only daytime periods
            temps.append(period.get("temperature", 0))

            # Parse wind speed (e.g., "5 to 10 mph")
            wind_str = period.get("windSpeed", "0 mph")
            wind_num = int(wind_str.split()[0]) if wind_str.split() else 0
            wind_speeds.append(wind_num)

            # Check for rain
            precip = period.get("probabilityOfPrecipitation", {}).get("value", 0) or 0
            if precip > 30:
                rain_chance = True

            # Track conditions
            conditions.append(period.get("shortForecast", ""))

    # Calculate averages
    avg_temp = sum(temps) / len(temps) if temps else 70
    max_wind = max(wind_speeds) if wind_speeds else 5

    # Determine if mostly sunny
    sunny_count = sum(1 for c in conditions if "Sunny" in c or "Clear" in c)
    mostly_sunny = sunny_count > len(conditions) / 2

    # Build summary
    weather_desc = "Expect sunny skies" if mostly_sunny else "Expect partly cloudy skies"
    temp_desc = f"with highs in the {int(avg_temp)}F range"

    if max_wind <= 10:
        wind_desc = f"and light winds around {max_wind} mph"
        scoring = "ideal scoring conditions"
    elif max_wind <= 15:
        wind_desc = f"and moderate winds around {max_wind} mph"
        scoring = "good scoring opportunities"
    else:
        wind_desc = f"and breezy conditions up to {max_wind} mph"
        scoring = "challenging scoring conditions"

    rain_desc = "No rain is forecast" if not rain_chance else "Some rain is possible"

    summary = f"{weather_desc} {temp_desc} {wind_desc} throughout the week. {rain_desc}, making for {scoring}."

    return summary


def get_openmeteo_forecast(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """Global daily forecast from Open-Meteo (free, no API key). Covers international venues.

    Forecast horizon is ~16 days; returns {} if the dates are out of range or on error.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,weather_code",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "auto",
    }
    if start_date and end_date:
        params["start_date"] = start_date
        params["end_date"] = end_date
    else:
        params["forecast_days"] = 7
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  Warning: Error fetching Open-Meteo forecast: {e}")
        return {}


# WMO weather codes (Open-Meteo): 0/1 = clear/mainly clear; precipitation codes below.
_WMO_SUNNY = {0, 1}
_WMO_RAIN = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}


def format_openmeteo_summary(data: dict) -> tuple[str, list[dict]]:
    """Format Open-Meteo daily data into a golf summary string + raw per-day periods."""
    daily = data.get("daily") or {}
    days = daily.get("time") or []
    if not days:
        return ("Weather forecast unavailable.", [])
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    pprob = daily.get("precipitation_probability_max") or []
    wmax = daily.get("wind_speed_10m_max") or []
    codes = daily.get("weather_code") or []

    highs = [t for t in tmax if t is not None]
    avg_high = sum(highs) / len(highs) if highs else 70
    max_wind = max([w for w in wmax if w is not None], default=5)
    rain_chance = any((p or 0) > 30 for p in pprob)
    sunny_days = sum(1 for c in codes if c in _WMO_SUNNY)
    mostly_sunny = bool(codes) and sunny_days > len(codes) / 2

    weather_desc = "Expect sunny skies" if mostly_sunny else "Expect partly cloudy skies"
    temp_desc = f"with highs in the {int(round(avg_high))}F range"
    if max_wind <= 10:
        wind_desc = f"and light winds around {int(round(max_wind))} mph"
        scoring = "ideal scoring conditions"
    elif max_wind <= 15:
        wind_desc = f"and moderate winds around {int(round(max_wind))} mph"
        scoring = "good scoring opportunities"
    else:
        wind_desc = f"and breezy conditions up to {int(round(max_wind))} mph"
        scoring = "challenging scoring conditions"
    rain_desc = "No rain is forecast" if not rain_chance else "Some rain is possible"
    summary = f"{weather_desc} {temp_desc} {wind_desc} throughout the week. {rain_desc}, making for {scoring}."

    raw = []
    for i, day in enumerate(days):
        raw.append({
            "name": day,
            "temperature": int(round(tmax[i])) if i < len(tmax) and tmax[i] is not None else None,
            "temperatureLow": int(round(tmin[i])) if i < len(tmin) and tmin[i] is not None else None,
            "temperatureUnit": "F",
            "windSpeed": f"{int(round(wmax[i]))} mph" if i < len(wmax) and wmax[i] is not None else "",
            "shortForecast": "Sunny" if (i < len(codes) and codes[i] in _WMO_SUNNY) else ("Rain" if (i < len(codes) and codes[i] in _WMO_RAIN) else "Partly Cloudy"),
            "probabilityOfPrecipitation": pprob[i] if i < len(pprob) else 0,
            "isDaytime": True,
        })
    return summary, raw


# ── AM/PM wind breakdown (links-golf wave read) ─────────────────────────
# Local hours sampled per tournament day. Tunable — the user asked for an
# 8am morning read and a 12pm afternoon read.
WIND_SAMPLE_HOURS = [("am", 8, "8 AM"), ("pm", 12, "12 PM")]

_CARDINALS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def _deg_to_cardinal(deg) -> str:
    """Convert a wind bearing in degrees to a 16-point compass label."""
    if deg is None:
        return ""
    idx = int((float(deg) % 360) / 22.5 + 0.5) % 16
    return _CARDINALS[idx]


def get_openmeteo_hourly_wind(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """Hourly wind (speed/direction/gusts) from Open-Meteo for the tournament window.

    Global + free, so it powers the AM/PM wind breakdown for every venue (US or
    international) regardless of which source produced the daily summary. Returns
    the raw 'hourly' dict, or {} if out of range / on error.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "wind_speed_unit": "mph",
        "timezone": "auto",
    }
    if start_date and end_date:
        params["start_date"] = start_date
        params["end_date"] = end_date
    else:
        params["forecast_days"] = 7
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("hourly") or {}
    except Exception as e:
        print(f"  Warning: Error fetching Open-Meteo hourly wind: {e}")
        return {}


def build_wind_by_day(hourly: dict, start_date: str, end_date: str) -> list[dict]:
    """Extract AM (8am) and PM (12pm) wind for each tournament day.

    Returns a list of {date, weekday, am:{...}, pm:{...}} where each am/pm block is
    {hour, speed_mph, gust_mph, dir, deg} (or None if that hour is unavailable).
    Purely additive — older consumers ignore it, new renderers guard on presence.
    """
    from datetime import timedelta

    times = hourly.get("time") or []
    if not times:
        return []
    speeds = hourly.get("wind_speed_10m") or []
    dirs = hourly.get("wind_direction_10m") or []
    gusts = hourly.get("wind_gusts_10m") or []
    index = {t: i for i, t in enumerate(times)}

    try:
        sd = datetime.strptime(start_date, "%Y-%m-%d").date()
        ed = datetime.strptime(end_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return []

    out: list[dict] = []
    day = sd
    while day <= ed:
        iso = day.strftime("%Y-%m-%d")
        entry: dict = {"date": iso, "weekday": day.strftime("%a")}
        has_any = False
        for key, hour, label in WIND_SAMPLE_HOURS:
            i = index.get(f"{iso}T{hour:02d}:00")
            if i is None:
                entry[key] = None
                continue
            spd = speeds[i] if i < len(speeds) else None
            gst = gusts[i] if i < len(gusts) else None
            dg = dirs[i] if i < len(dirs) else None
            entry[key] = {
                "hour": label,
                "speed_mph": int(round(spd)) if spd is not None else None,
                "gust_mph": int(round(gst)) if gst is not None else None,
                "dir": _deg_to_cardinal(dg),
                "deg": int(round(dg)) if dg is not None else None,
            }
            has_any = True
        if has_any:
            out.append(entry)
        day += timedelta(days=1)
    return out


def format_dates(tournament: dict) -> str:
    """Format tournament dates like 'April 9-12, 2026'."""
    dates = tournament.get("dates", {})
    start_str = dates.get("start", "")
    end_str = dates.get("end", "")

    if not start_str or not end_str:
        return "TBD"

    try:
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end = datetime.strptime(end_str, "%Y-%m-%d")

        if start.month == end.month:
            return f"{start.strftime('%B')} {start.day}-{end.day}, {end.year}"
        else:
            return f"{start.strftime('%B')} {start.day} - {end.strftime('%B')} {end.day}, {end.year}"
    except ValueError:
        return f"{start_str} - {end_str}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch weather forecast for a PGA Tour tournament (NOAA)"
    )
    parser.add_argument(
        "--tournament",
        type=str,
        help="Tournament name (auto-detects from schedule if omitted)"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now().year,
        help="Tournament year (default: current year)"
    )
    args = parser.parse_args()

    # Load schedule
    schedule = load_schedule()

    # Find tournament
    if args.tournament:
        tournament = find_tournament(schedule, args.tournament)
        if not tournament:
            print(f"[WARNING] Tournament '{args.tournament}' not found in schedule.")
            print("         Provide coordinates manually or add to pga_schedule_2026.json.")
            return 1
    else:
        # Auto-detect from schedule (same logic as orchestrator)
        from datetime import timedelta
        today = datetime.now().date()
        week_ahead = today + timedelta(days=7)

        all_tournaments = schedule.get("tournaments", []) + schedule.get("fall_schedule", [])
        candidates = []
        for t in all_tournaments:
            ds = t.get("dates", {}).get("start", "")
            if not ds:
                continue
            try:
                sd = datetime.strptime(ds, "%Y-%m-%d").date()
                ed_str = t.get("dates", {}).get("end", ds)
                ed = datetime.strptime(ed_str, "%Y-%m-%d").date()
                if today <= sd <= week_ahead or sd <= today <= ed:
                    candidates.append((t, sd))
            except ValueError:
                continue

        if candidates:
            candidates.sort(key=lambda x: x[1])
            tournament = candidates[0][0]
        else:
            print("[ERROR] No upcoming tournament found in schedule.")
            print("        Use --tournament to specify one.")
            return 1

    tournament_name = tournament.get("name", "Unknown Tournament")
    location = tournament.get("location", "")
    dates_display = format_dates(tournament)

    print(f"[WEATHER] Fetching weather forecast from NOAA (National Weather Service)...")
    print(f"  Tournament: {tournament_name}")
    print(f"  Location:   {location}")
    print(f"  Dates:      {dates_display}")

    # Look up coordinates
    coords = get_coordinates(location)

    if not coords:
        # Check if this is an international venue (NOAA only covers US)
        loc_lower = location.lower()
        international_indicators = [
            "scotland", "england", "japan", "canada", "mexico",
            "bermuda", "dominican republic", "australia",
        ]
        is_international = any(ind in loc_lower for ind in international_indicators)

        if is_international:
            print(f"  [INFO] {location} is outside NOAA coverage (US-only API).")
            print(f"         Saving placeholder. Consider adding manual weather data.")

            weather_data = {
                "tournament": tournament_name,
                "location": location,
                "dates": dates_display,
                "forecast": f"Weather forecast not available via NOAA for {location}. Check local weather services for the tournament forecast.",
                "source": "N/A (international venue - outside NOAA coverage)",
                "coordinates": None,
                "fetched_at": datetime.now().isoformat()
            }

            output_file = ROOT / "data" / "tournament_weather.json"
            output_file.write_text(json.dumps(weather_data, indent=2), encoding="utf-8")
            print(f"  Saved to {output_file}")
            return 0

        # Unknown US venue - print what we know and fail
        print(f"  [ERROR] No coordinates found for '{location}'.")
        print(f"          Add this venue to VENUE_COORDINATES in fetch_tournament_weather.py")
        print(f"          or check the location in pga_schedule_2026.json.")
        return 1

    lat, lon = coords
    print(f"  Coordinates: {lat}, {lon}")

    loc_lower = location.lower()
    international_indicators = [
        "scotland", "england", "japan", "canada", "mexico", "bermuda",
        "dominican republic", "australia", "ireland", "wales", "france", "spain",
    ]
    is_international = any(ind in loc_lower for ind in international_indicators)

    raw_periods: list[dict] | None = None
    if is_international:
        # NOAA is US-only; use Open-Meteo (free, global) for international venues.
        dts = tournament.get("dates", {})
        print(f"  [INFO] International venue — using Open-Meteo (NOAA is US-only).")
        om = get_openmeteo_forecast(lat, lon, dts.get("start", ""), dts.get("end", ""))
        weather_summary, raw_periods = format_openmeteo_summary(om)
        source = "Open-Meteo (free global forecast)"
        source_note = "Open-Meteo (free global forecast, no API key required)"
    else:
        forecast_data = get_noaa_forecast(lat, lon)
        weather_summary = format_golf_weather_summary(forecast_data)
        source = "NOAA National Weather Service"
        source_note = "NOAA (free government data, no API key required)"
        if forecast_data and "properties" in forecast_data:
            raw_periods = []
            for p in forecast_data["properties"]["periods"][:8]:
                raw_periods.append({
                    "name": p.get("name", ""),
                    "temperature": p.get("temperature", 0),
                    "temperatureUnit": p.get("temperatureUnit", "F"),
                    "windSpeed": p.get("windSpeed", ""),
                    "windDirection": p.get("windDirection", ""),
                    "shortForecast": p.get("shortForecast", ""),
                    "isDaytime": p.get("isDaytime", True),
                    "probabilityOfPrecipitation": p.get("probabilityOfPrecipitation", {}).get("value", 0)
                })
        # Fallback: if NOAA returned nothing, try Open-Meteo before giving up.
        if not weather_summary or weather_summary.startswith("Weather forecast unavailable"):
            dts = tournament.get("dates", {})
            om = get_openmeteo_forecast(lat, lon, dts.get("start", ""), dts.get("end", ""))
            om_summary, om_raw = format_openmeteo_summary(om)
            if om_raw:
                weather_summary, raw_periods = om_summary, om_raw
                source = "Open-Meteo (free global forecast)"
                source_note = "Open-Meteo (NOAA fallback)"

    print(f"\n  Forecast: {weather_summary}")

    # AM/PM wind breakdown for each tournament day (Open-Meteo hourly, global).
    # Additive: powers the links-golf wave read without disturbing existing fields.
    dts = tournament.get("dates", {})
    hourly = get_openmeteo_hourly_wind(lat, lon, dts.get("start", ""), dts.get("end", ""))
    wind_by_day = build_wind_by_day(hourly, dts.get("start", ""), dts.get("end", ""))
    if wind_by_day:
        print(f"  AM/PM wind: captured 8am + 12pm for {len(wind_by_day)} day(s)")
    else:
        print("  [INFO] AM/PM wind unavailable (dates out of hourly range?) — skipping wind table")

    # Save to JSON for use in HTML generation
    weather_data = {
        "tournament": tournament_name,
        "location": location,
        "dates": dates_display,
        "forecast": weather_summary,
        "source": source,
        "coordinates": {"lat": lat, "lon": lon},
        "fetched_at": datetime.now().isoformat()
    }
    if raw_periods:
        weather_data["raw_periods"] = raw_periods
    if wind_by_day:
        weather_data["wind_by_day"] = wind_by_day

    output_file = ROOT / "data" / "tournament_weather.json"
    output_file.write_text(json.dumps(weather_data, indent=2), encoding="utf-8")

    print(f"\n  Saved to {output_file}")
    print(f"  Source: {source_note}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
