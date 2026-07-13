# AMEX 2026 Odds + History Audit
- Generated: `2026-01-19T19:22:08.997153+00:00`
- Win odds source: `https://dknetwork.draftkings.com/2026/01/18/2026-the-american-express-odds-full-field/`
- Past results source:
  - 2025: `https://www.pgatour.com/tournaments/2025/the-american-express/R2025002/past-results`
  - 2024: `https://www.pgatour.com/tournaments/2024/the-american-express/R2024002/past-results`
  - 2023: `https://www.pgatour.com/tournaments/2023/the-american-express/R2023002/past-results`

## Per-player diffs (generator fallback → audited)
| Player | Win Odds | 2025 | 2024 | 2023 |
|---|---:|---:|---:|---:|
| Scottie Scheffler | **+280 → +240** | NA | **NA → T17** | **NA → T11** |
| Ludvig Aberg | **+2200 → +2000** | **T12 → NA** | **T2 → NA** | NA |
| Patrick Cantlay | +2200 | **T18 → T5** | **T7 → T52** | **T15 → T26** |
| Russell Henley | +2200 | **T8 → NA** | **T14 → NA** | **T6 → NA** |
| Sam Burns | **+2200 → +2000** | **T22 → T29** | **MC → T6** | **T3 → T11** |
| Robert MacIntyre | **+2500 → +2800** | **T15 → NA** | **T28 → MC** | NA |
| Matt Fitzpatrick | **+2800 → +3000** | **T19 → NA** | **T11 → NA** | NA |
| Ben Griffin | +1800 | **T5 → T7** | **MC → T9** | **T42 → T32** |
| Harry Hall | **+3250 → +3000** | **T31 → T21** | **T3 → MC** | **T18 → T41** |
| Si Woo Kim | **+3250 → +5000** | **T9 → T51** | **T16 → T25** | **T11 → T22** |
| Sepp Straka | +3500 | **WIN → 1** | **T24 → NA** | **T19 → NA** |
| Justin Thomas | +3500 | **T45 → 2** | **MC → T3** | **T8 → NA** |
| Keegan Bradley | +4000 | **T16 → NA** | **T12 → NA** | **T21 → NA** |
| Nick Taylor | **+4500 → +7000** | **T20 → T12** | **T6 → MC** | **T35 → MC** |
| Max Homa | **+4500 → +10000** | **T27 → NA** | **MC → NA** | **T13 → NA** |
| Sungjae Im | +5000 | **T13 → MC** | **T29 → T25** | **2 → T18** |
| Tom Kim | **+5000 → +30000** | **T24 → MC** | **T10 → MC** | **NA → T6** |
| Denny McCarthy | **+5500 → +7500** | **T11 → NA** | **T14 → NA** | **T9 → T50** |
| J.T. Poston | **+6000 → +7000** | **T30 → T12** | **T13 → T11** | **T44 → T6** |
| Taylor Moore | **+6500 → +30000** | **T23 → T7** | **T5 → NA** | MC |
| Rickie Fowler | **+7000 → +5000** | **MC → T21** | **T23 → MC** | **T17 → T54** |
| Stephan Jaeger | **+7500 → +20000** | **T21 → NA** | **T9 → T52** | **T26 → T36** |
| K.H. Lee | +8000 | **T17 → MC** | **T18 → T25** | **T22 → MC** |
| Andrew Putnam | **+9000 → +50000** | **T28 → MC** | **T19 → T47** | **T30 → T36** |
| Chad Ramey | **+10000 → +50000** | **T41 → MC** | MC | **T12 → NA** |
| Harris English | **+11000 → +4500** | **T32 → T43** | **T20 → NA** | **T16 → MC** |
| Erik van Rooyen | **+12000 → +30000** | **T26 → MC** | **T8 → T25** | **MC → T6** |
| Austin Eckroat | **+12500 → +18000** | **T29 → NA** | **NA → T25** | **NA → MC** |
| Cameron Young | +13000 | **T38 → MC** | **T25 → NA** | **NA → T26** |
| Michael Kim | **+15000 → +10000** | **T44 → T43** | **MC → T6** | **T16 → MC** |
| Byeong Hun An | +18000 | **T36 → NA** | **T21 → NA** | **T40 → T41** |
| Carl Yuan | +25000 | NA | **NA → MC** | **NA → MC** |

## Summary
- Players audited: **32**
- Win odds updated from source: **21** players
- Historical finish cells changed: **89** cells

## Multi-book odds audit (The Odds API)
- Status: **SKIPPED** (Odds API not configured or request failed)
- Error: `ValueError: ODDS_API_KEY is required. Set it in .env file.`
- Fix: ensure `ODDS_API_KEY` is set in your local `.env`, then rerun.

## Next step
- Run `python3 scripts/generate_american_express.py` to regenerate `american_express_2026.html` using the audited data.
