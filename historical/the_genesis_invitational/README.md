# The Genesis Invitational – historical

Tournament-specific scripts and data for The Genesis Invitational. For **this week’s** preview (e.g. Cognizant Classic), use the root pipeline:

```bash
python scripts/weekly_tournament_orchestrator.py
# or: ./run_weekly.sh
```

**Here:**
- **scripts/** — Genesis-specific scripts (e.g. `apply_genesis_countries.py`). Run from **project root** so paths resolve.
- **data/** — Genesis players_data, storylines, recent_form, matchups, insights, and `tournament_results_cache/` (2023–2025).
- **\*.html** — Genesis 2026 preview pages; **tfl-genesis.jpg** — tournament image.
- **\*.md** — Audit notes (e.g. `STORYLINES_AUDIT_GENESIS_2026.md`).
