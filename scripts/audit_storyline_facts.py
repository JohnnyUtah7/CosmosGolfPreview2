#!/usr/bin/env python3
"""
Fact-verify every numeric claim in the storylines against source data.

Unlike scripts/audit_storylines.py (a pattern lint), this cross-checks each
number in the prose against players_data + the tournament result caches:

  signed decimals  -> strokes-gained / course-fit / course-history values
  N.N%             -> win / top5 / top10 / top20 / make-cut probabilities
  +NNNN            -> win / top5 / top10 prices
  OWGR #N          -> owgr rank
  T## in YYYY      -> data/tournament_results_cache/<this event>_YYYY (venue history)
  T## at <event>   -> data/tournament_results_cache/<event>_2026

Defaults to this week's scheduled tournament; override with --slug/--year.
"""
from __future__ import annotations
import argparse, datetime, json, re, sys, glob, os
from collections import defaultdict

ROOT = "/Users/chrismiller/Documents/CosmosGolfBetting"

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--slug", help="tournament slug (default: this week's scheduled event)")
ap.add_argument("--year", type=int, default=datetime.date.today().year)
args = ap.parse_args()

YEAR = args.year

# schedule gives us canonical event names to look for in prose
sched = json.load(open(f"{ROOT}/data/pga_schedule_{YEAR}.json"))
events = [t["name"] for t in sched["tournaments"]]


def _this_weeks_event() -> dict:
    """The event currently in play, else the next one to start."""
    today = datetime.date.today()
    dated = []
    for t in sched["tournaments"]:
        try:
            start = datetime.date.fromisoformat(t["dates"]["start"])
            end = datetime.date.fromisoformat(t["dates"]["end"])
        except (KeyError, ValueError):
            continue
        dated.append((start, end, t))
    dated.sort(key=lambda d: (d[0], d[1]))
    for start, end, t in dated:
        if start <= today <= end:
            return t
    for start, end, t in dated:
        if start >= today:
            return t
    return dated[-1][2] if dated else {}


_event = next((t for t in sched["tournaments"] if t.get("slug") == args.slug), None) \
    if args.slug else _this_weeks_event()
SLUG = args.slug or (_event or {}).get("slug")
VENUE = ((_event or {}).get("course") or SLUG or "VENUE").upper()
if not SLUG:
    sys.exit("could not determine which tournament to audit — pass --slug")

sl = json.load(open(f"{ROOT}/data/{SLUG}_{YEAR}_storylines.json"))["storylines"]
pd = json.load(open(f"{ROOT}/data/{SLUG}_{YEAR}_players_data.json"))
dg, odds, owgr, hist = pd["datagolf"], pd["odds"], pd.get("owgr", {}), pd.get("historical", {})

# ---- result caches -------------------------------------------------------
caches = {}          # display event name -> {player: finish}
for f in glob.glob(f"{ROOT}/data/tournament_results_cache/*.json"):
    d = json.load(open(f))
    base = os.path.basename(f)[:-5]
    name = d.get("tournament") or base
    yr = base[-4:]
    caches[(name, yr)] = d.get("results", {})
# common prose shorthands -> canonical schedule name
ALIAS = {
    "The Open": "The Open Championship", "the Open": "The Open Championship",
    "Scottish": "Genesis Scottish Open", "the Scottish": "Genesis Scottish Open",
    "Colonial": "Charles Schwab Challenge", "the Memorial": "The Memorial Tournament presented by Workday",
    "Memorial": "The Memorial Tournament presented by Workday",
    "Byron Nelson": "The CJ Cup Byron Nelson", "the U.S. Open": "U.S. Open", "U.S. Open": "U.S. Open",
    "US Open": "U.S. Open", "John Deere": "John Deere Classic", "Corales": "Corales Puntacana Championship",
    "Corales Puntacana": "Corales Puntacana Championship", "Rocket Classic": "Rocket Classic",
    "3M Open": "3M Open", "Travelers": "Travelers Championship", "PGA Championship": "PGA Championship",
    "Masters": "Masters Tournament", "Players": "The Players Championship",
    "Canadian Open": "RBC Canadian Open", "Myrtle Beach": "Myrtle Beach Classic",
    "ISCO": "ISCO Championship", "Barracuda": "Barracuda Championship",
    "Valspar": "Valspar Championship", "Truist": "Truist Championship",
    "Heritage": "RBC Heritage", "Zurich": "Zurich Classic of New Orleans",
    "Houston Open": "Texas Children's Houston Open", "Cognizant": "Cognizant Classic in The Palm Beaches",
    "Genesis": "Genesis Invitational", "Pebble Beach": "AT&T Pebble Beach Pro-Am",
    "Phoenix": "WM Phoenix Open", "American Express": "The American Express",
    "Sony": "Sony Open in Hawaii", "Farmers": "Farmers Insurance Open",
    "Mexico Open": "Mexico Open at VidantaWorld", "Puerto Rico": "Puerto Rico Open",
    "Arnold Palmer": "Arnold Palmer Invitational presented by Mastercard",
    "Bay Hill": "Arnold Palmer Invitational presented by Mastercard",
}

DG_FIELDS = ["sg_total", "sg_ott", "sg_app", "sg_arg", "sg_putt",
             "course_fit", "course_history", "driving_dist", "driving_acc"]
PROB_FIELDS = ["win_prob", "top_5_prob", "top_10_prob", "top_20_prob", "make_cut_prob"]

def close(a, b, tol=0.005):
    return a is not None and b is not None and abs(a - b) <= tol

issues = defaultdict(list)
stats = defaultdict(int)

for name, text in sl.items():
    if not isinstance(text, str):
        continue
    d = dg.get(name, {}) or {}
    o = odds.get(name, {}) or {}
    prices = {v for v in (o.get("odds"), o.get("top5"), o.get("top10")) if v}
    dgvals = [d.get(f) for f in DG_FIELDS if d.get(f) is not None]
    probs = [d.get(f) for f in PROB_FIELDS if d.get(f) is not None]

    # --- 1. prices: +NNN(N) integers, 3+ digits, no decimal point ---------
    for m in re.finditer(r"\+(\d{3,})\b(?!\.\d)", text):
        stats["price_checked"] += 1
        val = int(m.group(1))
        if val not in prices:
            issues[name].append(f"PRICE +{val} is not this player's win/top5/top10 "
                                f"({sorted(prices)})")

    # --- 2. signed decimals -> SG / adjustments --------------------------
    for m in re.finditer(r"([+-]\d+\.\d+)", text):
        stats["sg_checked"] += 1
        val = float(m.group(1))
        if not any(close(val, v) for v in dgvals):
            issues[name].append(f"SG/ADJ {m.group(1)} matches no DG field "
                                f"({ {f: d.get(f) for f in DG_FIELDS if d.get(f) is not None} })")

    # --- 3. percentages -> probabilities ---------------------------------
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*%", text):
        stats["pct_checked"] += 1
        val = float(m.group(1))
        if not any(close(val, p, 0.06) for p in probs):
            issues[name].append(f"PCT {m.group(0)} matches no DG probability "
                                f"({ {f: d.get(f) for f in PROB_FIELDS if d.get(f) is not None} })")

    # --- 4. OWGR ---------------------------------------------------------
    for m in re.finditer(r"OWGR\s*#?(\d+)", text, re.I):
        stats["owgr_checked"] += 1
        want = owgr.get(name)
        if want is not None and int(m.group(1)) != int(want):
            issues[name].append(f"OWGR #{m.group(1)} but data says #{want}")

    # --- 5. venue finishes by year ---------------------------------------
    h = hist.get(name, {}) or {}
    for m in re.finditer(r"(?:a\s+)?(T?\d+(?:st|nd|rd|th)?|MC|missed cut)\s+in\s+(20\d{2})", text, re.I):
        fin_raw, yr = m.group(1), m.group(2)
        if yr not in h:
            continue
        stats["hist_checked"] += 1
        want = str(h[yr])
        got = re.sub(r"(st|nd|rd|th)$", "", fin_raw, flags=re.I)
        norm = lambda x: str(x).upper().lstrip("T").replace("MISSED CUT", "MC")
        if norm(got) != norm(want):
            issues[name].append(f"{VENUE} {yr}: prose says '{fin_raw}', cache says '{want}'")

    # --- 6. other-event finishes -----------------------------------------
    FIN = r"(T?\d+(?:st|nd|rd|th)?|MC|missed(?:\s+the)?\s+cut|runner-up|win|won|winner|victory)"
    for alias, canon in ALIAS.items():
        for m in re.finditer(rf"{FIN}\s+(?:at|of|in)\s+(?:the\s+)?{re.escape(alias)}\b", text, re.I):
            key = (canon, str(YEAR))
            res = caches.get(key)
            if not res or name not in res:
                continue
            stats["event_checked"] += 1
            want, got = str(res[name]), m.group(1).lower()
            if got in ("win", "won", "winner", "victory"):
                ok = want.lstrip("T") == "1"
            elif got == "runner-up":
                ok = want.lstrip("T") == "2"
            elif "cut" in got or got == "mc":
                ok = want.upper() == "MC"
            else:
                g = re.sub(r"(st|nd|rd|th)$", "", got, flags=re.I)
                ok = g.upper().lstrip("T") == want.upper().lstrip("T")
            if not ok:
                issues[name].append(f"{canon} 2026: prose says '{m.group(1)}', cache says '{want}'")

    # --- 7. rank claims: "4th in SG Approach", "11th in the field" --------
    SGMAP = {"total": "sg_total_rank", "approach": "sg_app_rank", "app": "sg_app_rank",
             "off the tee": "sg_ott_rank", "ott": "sg_ott_rank", "putting": "sg_putt_rank",
             "putt": "sg_putt_rank", "around the green": "sg_arg_rank", "arg": "sg_arg_rank"}
    for m in re.finditer(r"\b(\d+)(?:st|nd|rd|th)\s+in\s+(?:the\s+field\s+in\s+)?(?:SG\s+)?"
                         r"(total|approach|app|off the tee|ott|putting|putt|around the green|arg)\b",
                         text, re.I):
        claimed, field = int(m.group(1)), SGMAP[m.group(2).lower()]
        want = d.get(field)
        if want is None:
            continue
        stats["rank_checked"] += 1
        if claimed != int(want):
            issues[name].append(f"RANK '{m.group(0)}' but data says #{want}")

    # --- 8. field-leading superlatives ------------------------------------
    for m in re.finditer(r"(field's best|leads this field|best in the field|highest in this field|"
                         r"top(?:-| )ranked)\s*(?:\w+\s+){0,4}?(SG\s+)?"
                         r"(Total|Approach|Off the Tee|Putting|Around the Green)?", text, re.I):
        lbl = (m.group(3) or "").lower()
        if not lbl:
            continue
        field = SGMAP.get(lbl if lbl in SGMAP else lbl.replace("the ", ""))
        want = d.get(field) if field else None
        if want is None:
            continue
        stats["superlative_checked"] += 1
        if int(want) != 1:
            issues[name].append(f"SUPERLATIVE '{m.group(0).strip()}' but rank is #{want}")

print("=" * 78)
print(f" STORYLINE FACT AUDIT — {(_event or {}).get('name', SLUG)} {YEAR} — {len(sl)} storylines")
print("=" * 78)
print(" claims checked: " + ", ".join(f"{k}={v}" for k, v in sorted(stats.items())))
print("-" * 78)
if not issues:
    print(" ✅ No discrepancies found.")
else:
    for n in sorted(issues):
        print(f"\n {n}")
        for i in issues[n]:
            print(f"   ✗ {i}")
    print("-" * 78)
    print(f" {sum(len(v) for v in issues.values())} discrepancies across {len(issues)} players")
sys.exit(1 if issues else 0)
