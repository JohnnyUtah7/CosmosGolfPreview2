#!/usr/bin/env python3
"""
Fact-check AI-generated storylines + insights against the actual tournament data.

Catches the class of hallucination where the model invents tournament history:
  - calling a PAST winner the "defending champion" (defending = last year's winner)
  - claiming a player "won this event" / "X-time champion here" when the result
    caches show no such win
  - stating a specific-year finish that contradicts the result cache
  - naming a course/venue that isn't this week's scheduled venue

Data sources (all local, no network):
  - data/{slug}_{year}_storylines.json        (AI storylines)
  - data/{slug}_{year}_insights.json          (AI exec summary + insight cards)
  - data/{slug}_{year}_players_data.json      (history_YYYY per player)
  - data/tournament_results_cache/{slug}_*.json  (authoritative finishes/winners)
  - data/pga_schedule_{year}.json             (scheduled venue)

Exits 1 if any hard ERROR is found (wire into the weekly orchestrator so a bad
build fails loudly instead of shipping). Use --strict to also fail on warnings.

Usage:
    python scripts/audit_tournament_content.py --tournament "RBC Canadian Open" --year 2026 --slug rbc_canadian_open
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _slugify(name: str) -> str:
    s = name.lower().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower().replace(".", "").replace("'", "").replace("-", " ")).strip()


def name_variants(n: str) -> set[str]:
    n = (n or "").strip()
    out = {norm(n)}
    if "," in n:  # "Last, First" -> "First Last"
        a, b = [x.strip() for x in n.split(",", 1)]
        out.add(norm(f"{b} {a}"))
    return out


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _win(fin) -> bool:
    return str(fin or "").replace("T", "").strip() == "1"


def main() -> int:
    ap = argparse.ArgumentParser(description="Fact-check storylines/insights vs tournament data")
    ap.add_argument("--tournament", required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--slug", default=None)
    ap.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    a = ap.parse_args()

    slug = a.slug or _slugify(a.tournament)
    year = a.year
    dd = ROOT / "data"

    storylines = (load_json(dd / f"{slug}_{year}_storylines.json") or {}).get("storylines", {})
    insights = load_json(dd / f"{slug}_{year}_insights.json") or {}
    sched = load_json(dd / f"pga_schedule_{year}.json") or {}

    # Scheduled venue
    venue = None
    for t in sched.get("tournaments", []) + sched.get("fall_schedule", []):
        if t.get("slug") == slug or a.tournament.lower() in (t.get("name", "") or "").lower():
            venue = t.get("course")
            break

    # Result caches -> per-year finishes + winners
    cache_years: dict[int, dict] = {}
    for f in sorted((dd / "tournament_results_cache").glob(f"{slug}_*.json")):
        m = re.search(rf"{re.escape(slug)}_(\d{{4}})\.json$", f.name)
        if m:
            cache_years[int(m.group(1))] = (load_json(f) or {}).get("results", {})

    winners = {y: next((nm for nm, fin in res.items() if _win(fin)), None) for y, res in cache_years.items()}
    prior = sorted([y for y in cache_years if y < year])
    defending_year = prior[-1] if prior else None
    defending_champ = winners.get(defending_year) if defending_year else None

    def finish(player: str, y: int):
        vs = name_variants(player)
        for nm, fin in cache_years.get(y, {}).items():
            if name_variants(nm) & vs:
                return fin
        return None

    def won_years(player: str):
        return [y for y in cache_years if _win(finish(player, y))]

    def is_defending(player: str) -> bool:
        return bool(defending_champ) and bool(name_variants(player) & name_variants(defending_champ))

    errors: list[str] = []
    warns: list[str] = []

    VENUE_RE = re.compile(
        r"\bat ([A-Z][A-Za-z&.''-]+(?: [A-Z&0-9][A-Za-z&.''-]+){0,4}"
        r"(?: (?:Golf|Country|Club|G&CC|GC|Links|National|Course)))"
    )

    def check(player: str | None, text: str, where: str):
        if not isinstance(text, str) or not text.strip():
            return
        low = text.lower()

        # 1) "defending champion"
        if "defending champ" in low:
            if player:
                if not is_defending(player):
                    errors.append(
                        f"[{where}] {player}: called \"defending champion\", but the {defending_year} "
                        f"winner (defending champ) was {defending_champ or 'unknown'}."
                    )
            elif defending_champ and norm(defending_champ).split()[-1] not in low:
                warns.append(f"[{where}] mentions 'defending champion' but not {defending_champ} (the {defending_year} winner).")

        # 2) won / champion-at-this-event claims (player-attributed only)
        if player and (
            re.search(r"\b(champion of this event|won (this event|here|this tournament)|winner here|"
                      r"\d+-time[^.]*?(?:this event|here|champion)|two-time defending)\b", low)
            or re.search(r"\b(19|20)\d\d champion\b", low)
        ):
            wy = won_years(player)
            if not wy:
                errors.append(
                    f"[{where}] {player}: claims a win/championship at this event, but has NO winning "
                    f"finish in the result caches (years on file: {sorted(cache_years) or 'none'})."
                )
            # A win-word attributes a win to year `ym` only when the span between them
            # crosses neither another 4-digit year NOR a finish token. Finish tokens
            # (T2, MC, WD, runner-up, 2nd/3rd, solo) bind a year to a NON-win result, so
            # "2023 champion ... a T2 in 2025" must not read as a 2025 win, and "2024
            # champion ... runner-up in 2023" must not read as a 2023 win. Without the
            # finish-token guard, a legitimately-worded past champion with other years
            # cited in the same sentence trips false "claims a YYYY win" errors.
            gap = r"(?:(?!\b20\d\d\b)(?!\bt\d)(?!\b(?:mc|wd|runner|2nd|3rd|solo)\b)[^.]){0,40}"
            for ym in re.findall(r"\b(20\d\d)\b", text):
                yi = int(ym)
                if yi in cache_years and re.search(
                    rf"(champion|won|winner|title){gap}{ym}"
                    rf"|{ym}{gap}(champion|won|winner|title)", low
                ) and not _win(finish(player, yi)):
                    errors.append(f"[{where}] {player}: claims a {ym} win here, but cache finish = {finish(player, yi)}.")

        # 3) explicit venue-anchored finish claim vs cache (catches wrong finishes).
        # Require the finish token to sit DIRECTLY beside "here/this event" so we
        # don't grab stray numbers (SG like +0.34, prices, OWGR) from the sentence.
        # Matches: "T6 here in 2023", "runner-up here in 2025", "T4 at this event in 2024".
        if player:
            fin_tok = r"(T?\d{1,3}|MC|WD|runner-?up|2nd|solo \d+|won|winner)"
            anchor = r"(?:here|at this event|at this venue|at this tournament)"
            pat = re.compile(
                rf"\b{fin_tok}\s+(?:finish\s+)?{anchor}\s+in\s+(20\d\d)\b"
                rf"|\b{fin_tok}\s+in\s+(20\d\d)\s+{anchor}\b",
                re.I,
            )

            def _canon(tok: str) -> str:
                t = re.sub(r"[^a-z0-9]", "", tok.lower())
                if t in ("runnerup", "2nd", "solo2"):
                    return "2"
                return t.lstrip("t")

            for m in pat.finditer(text):
                fin_txt = m.group(1) or m.group(3)
                ym = m.group(2) or m.group(4)
                yi = int(ym)
                if yi not in cache_years:
                    continue
                actual = finish(player, yi)
                if actual is None:
                    continue
                claim, act = _canon(fin_txt), _canon(str(actual))
                ok = (claim == act) or (fin_txt.lower() in ("won", "winner") and _win(actual))
                if not ok:
                    warns.append(f"[{where}] {player}: claims '{fin_txt} ... in {ym}' but cache finish = {actual}.")

        # 4) venue mentions that aren't the scheduled course
        if venue:
            vtok = set(norm(venue).split())
            for m in VENUE_RE.finditer(text):
                cand = m.group(1)
                # Skip sentence-boundary false positives like "T55 at Travelers. Course
                # fit ..." where a period+space sits directly before the venue keyword
                # (i.e. the keyword starts a new sentence, e.g. "Course fit"). Real
                # abbreviated venues ("St. Simons Island Club") keep the period earlier
                # in the name, not immediately before the keyword, so they're preserved.
                if re.search(r"\.\s+(?:Golf|Country|Club|G&CC|GC|Links|National|Course)\b", cand):
                    continue
                if not (set(norm(cand).split()) & vtok):
                    warns.append(f"[{where}] mentions venue '{cand}', but scheduled venue is '{venue}'.")

    # Run checks
    for player, txt in storylines.items():
        check(player, txt, f"storyline:{player}")

    check(None, insights.get("executive_summary", ""), "insights:exec_summary")
    for card in insights.get("insights", []):
        blob = f"{card.get('title','')} {card.get('insight','')}"
        plist = card.get("players") or [None]
        for pl in plist:
            check(pl, blob, f"insight:{card.get('title','?')[:40]}")

    # Report
    print("=" * 70)
    print(f" CONTENT AUDIT — {a.tournament} {year}")
    print("=" * 70)
    print(f" Venue (schedule): {venue or 'UNKNOWN'}")
    print(f" Result-cache years: {sorted(cache_years) or 'none'}")
    print(f" Winners: " + ", ".join(f"{y}={winners[y]}" for y in sorted(winners)) if winners else " Winners: none")
    print(f" Defending champion ({defending_year}): {defending_champ or 'unknown'}")
    print("-" * 70)
    if errors:
        print(f" ❌ {len(errors)} ERROR(S):")
        for e in errors:
            print("   " + e)
    if warns:
        print(f" ⚠️  {len(warns)} WARNING(S):")
        for w in warns:
            print("   " + w)
    if not errors and not warns:
        print(" ✅ No factual issues found in storylines/insights.")
    print("=" * 70)

    if errors or (a.strict and warns):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
