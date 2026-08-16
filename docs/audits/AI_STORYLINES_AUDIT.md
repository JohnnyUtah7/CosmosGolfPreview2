# AI Storylines Generation Audit Report

## Date: 2026-01-19

## Summary
Successfully generated AI-powered "Why They Could Win" storylines for all 163 players in The American Express 2026 betting preview using Claude API.

## What Was Completed ✅

### 1. AI Storyline Generation
- **Status**: ✅ COMPLETE
- **Players Processed**: 163/163 (100%)
- **Model Used**: Claude Sonnet 4
- **Output File**: `data/amex_2026_storylines.json`

**Quality Assessment**:
- Storylines are creative, data-driven, and specific
- Each storyline is 2-3 sentences focusing on:
  - Specific course history at The American Express (T8 in 2024, T29 in 2025, etc.)
  - Player strengths that match course demands (iron play, wedge control, putting)
  - Concrete data points (OWGR rankings, odds, historical finishes)
  - Avoids generic phrases like "could surprise"

**Examples of Good Storylines**:
- **Ludvig Aberg**: "The Swedish star has cracked the code at PGA West with a runner-up finish in 2024 and T12 last year, showcasing the accurate iron play that thrives on these target golf layouts..."
- **Russell Henley**: "Henley's consistent excellence at The American Express includes three straight top-15 finishes, highlighted by his T6 in 2023 and T8 last year..."
- **Min Woo Lee**: "Lee's T8 finish in 2024 followed by T29 in 2025 shows he's cracked the code on these desert layouts and their unique demands..."

### 2. Historical Data Fixes
- **Status**: ✅ COMPLETE
- **Fixed**: Min Woo Lee historical data
  - Before: `{}` (empty)
  - After: `{"2025": "T29", "2024": "T8"}`

## What Still Needs Work ⚠️

### 1. Recent Form Data Source
- **Status**: ⚠️ NEEDS ATTENTION
- **Issue**: The `data/amex_2026_recent_form.json` file contains corrupted data:
  - Contains news headlines like "The American Express 2026 odds, predictions, field: PGA Tour picks..."
  - Should contain actual tournament results like "Last start: Sony Open (Jan 2026): T4 — trending"

**Current State**:
- Out of 163 players, most show "—" for recent form analysis
- Only a few players have meaningful recent form data:
  - Robert MacIntyre: "Strong T4 finish at Sony Open shows excellent current form"
  - Nick Taylor: "Currently tied for the lead after 36 holes at the Sony Open"
  - Sungjae Im: "Struggled to a T39 finish at the Genesis Championship in October"

**Root Cause**:
- The `scripts/refresh_recent_form.py` script requires `BALLDONTLIE_API_KEY` to fetch real tournament results
- This API key is not currently configured

**Recommended Fix**:
1. Get BALLDONTLIE_API_KEY from https://balldontlie.io/
2. Add it to environment or `.env` file
3. Run: `python3 scripts/refresh_recent_form.py`
4. Re-generate storylines with updated recent form data

### 2. Integration with HTML Template
- **Status**: ⚠️ NOT YET DONE
- **Next Steps**:
  1. Update the HTML generation script to use the new storylines from `data/amex_2026_storylines.json`
  2. Replace the old generic storylines in the HTML template
  3. Update the "Recent Form" column with the AI-generated analyses (when available)

## Files Modified/Created

### New Files
1. `scripts/generate_ai_storylines.py` - Original Gemini-based generator (had rate limit issues)
2. `scripts/generate_ai_storylines_batch.py` - Gemini with smart batching and retries
3. `scripts/generate_ai_storylines_claude.py` - Claude-based generator (used successfully)
4. `data/amex_2026_storylines.json` - Generated AI storylines and form analyses

### Modified Files
1. `data/amex_2026_players_data.json` - Fixed Min Woo Lee historical data

## API Keys Used

### Gemini API
- **Key**: REDACTED (do not commit API keys)
- **Issue**: Free tier has strict rate limits (5 requests/minute)
- **Result**: Not practical for 163 players (would take 65+ minutes)

### Claude API
- **Key**: sk-ant-REDACTED
- **Model**: claude-sonnet-4-20250514
- **Batch Size**: 10 players per request
- **Total Batches**: 17
- **Result**: ✅ Successfully completed all 163 players

## Next Steps

### High Priority
1. **Fix Recent Form Data**:
   - Obtain BALLDONTLIE_API_KEY
   - Run `refresh_recent_form.py` to get real tournament results
   - Re-generate storylines with proper recent form context

2. **Integrate into HTML**:
   - Update HTML generation script to pull from `amex_2026_storylines.json`
   - Replace existing storylines in `american_express_2026.html`
   - Verify all 163 players display correctly

### Future Enhancements
1. **Hybrid API System** (as user requested):
   - Balance between Gemini (free tier) and Claude API to minimize costs
   - Use Gemini for players with lower odds (less critical)
   - Use Claude for top contenders (more important storylines)
   - Implement smart retry logic and batching

2. **Automated Updates**:
   - Set up scheduled refresh of recent form data
   - Re-generate storylines when significant form changes occur
   - Track player performance and adjust narratives

## Cost Analysis

### Claude API Usage
- **Requests**: 17 batches
- **Input Tokens**: ~170K total (estimate)
- **Output Tokens**: ~80K total (estimate)
- **Estimated Cost**: ~$5-10 (depending on exact token counts)

### Recommendation
For future runs, implement the hybrid system:
- Use Claude for top 50-60 players (~6-7 batches, ~$2-4)
- Use Gemini for remaining players with rate limiting (~30-40 minutes)
- Total cost reduction: ~60-70% while maintaining quality for key players

## Conclusion

✅ Successfully generated creative, data-driven AI storylines for all 163 players
⚠️ Recent form data source needs fixing (corrupted with news headlines)
⚠️ Integration into HTML template still pending
💡 Hybrid API system recommended for future cost optimization
