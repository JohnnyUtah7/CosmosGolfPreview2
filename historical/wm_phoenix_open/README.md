# WM Phoenix Open – historical

Tournament-specific scripts and data for the WM Phoenix Open. For **this week’s** preview (e.g. Genesis), use the root pipeline:

```bash
python scripts/weekly_tournament_orchestrator.py
# or: ./run_weekly.sh
```

**Here:**
- **scripts/** — WM-specific assembly (e.g. `assemble_wm_phoenix_html.py`, `inject_wm_recent_form_dropdown.py`). Run from **project root** so paths resolve.
- **data/** — WM players_data, storylines, recent_form, matchups, insights.
- **reference/** — WM Past perf PDF, Waste Management Open Deep Research PDF (reference only).
- **\*.md** — WM audit notes; main deploy steps are in `docs/DEPLOY_FULL_PREVIEW_TO_SHOPIFY.md`.
