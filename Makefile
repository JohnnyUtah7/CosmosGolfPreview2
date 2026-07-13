# Cosmos Golf Betting - convenience targets

# Generate this week's tournament preview (run on Monday or Tuesday).
# Requires: data/pga_schedule_2026.json, Data Golf API key.
weekly:
	python3 scripts/weekly_tournament_orchestrator.py

# Dry-run: show what the orchestrator would do without executing.
weekly-dry:
	python3 scripts/weekly_tournament_orchestrator.py --dry-run

.PHONY: weekly weekly-dry
