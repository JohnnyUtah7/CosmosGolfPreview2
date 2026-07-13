#!/usr/bin/env bash
# Weekly tournament preview generation - single entry point.
# Run on Monday (or Tuesday) to generate this week's preview.
#
# Prerequisites:
#   - data/pga_schedule_2026.json is up to date (source of "this week")
#   - Data Golf API key (and optional ANTHROPIC_API_KEY for storylines)
#
# Usage:
#   ./run_weekly.sh                         # Auto-detect tournament from schedule
#   ./run_weekly.sh "WM Phoenix Open"       # Override tournament
#   ./run_weekly.sh --dry-run               # Show steps without running
set -e
cd "$(dirname "$0")"
args=()
if [[ -n "$1" && "$1" != --* ]]; then
  args=(--tournament "$1")
  shift
fi
python3 scripts/weekly_tournament_orchestrator.py "${args[@]}" "$@"
