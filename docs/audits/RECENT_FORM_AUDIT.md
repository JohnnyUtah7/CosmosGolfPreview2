# WM Phoenix Open 2026 – Recent Form Audit (Web-Verified)

**Audit date:** February 2, 2026  
**Source:** `data/wm_phoenix_open_2026_recent_form.json`  
**Method:** Internet search verification of key events (American Express 2026, Sony Open 2026, etc.)  
**Display:** “Recent Form” column in `wm_phoenix_open_2026.html`

---

## 1. Why this audit

Recent form describes **other events** (AmEx, Sony, RSM, etc.), not WM Phoenix history. Errors found:

- **Scottie Scheffler** was listed as “Sony Open (Jan 2026): T2” but **he did not play** the Sony Open 2026. His 2026 starts were American Express, WM Phoenix, and AT&T Pebble Beach.
- Several Sony Open 2026 finishes in our data did not match published final leaderboards.

This document records web-verified results and corrections.

---

## 2. Reference results (web-verified)

### 2.1 Scottie Scheffler 2026 schedule

- **Source:** PGA Tour, GolfMagic, etc.
- **Fact:** Scheffler’s 2026 season debut was **The American Express** (Jan 22–25). He did **not** play the Sony Open in Hawaii (Jan 15–18).
- **Reported schedule:** American Express → WM Phoenix → AT&T Pebble Beach.
- **Conclusion:** Any “Sony Open (Jan 2026)” result for Scottie Scheffler is wrong. Remove it.

### 2.2 American Express 2026 (Jan 22–25, La Quinta)

- **Winner:** Scottie Scheffler, -27 (20th PGA Tour title).
- **T2 (-23):** Jason Day, Ryan Gerard, Matt McCarty, Andrew Putnam.
- **Our data:** Scheffler 1st ✓, Matt McCarty T2 ✓. Si Woo Kim led after 54 holes; final position not re-checked here.

### 2.3 Sony Open in Hawaii 2026 (Jan 15–18, Waialae)

- **Winner:** Chris Gotterup, -16 (3rd PGA Tour title).
- **2nd:** Ryan Gerard, -14.
- **3rd:** Patrick Rodgers, -13.
- **T4 (-12):** Robert MacIntyre, Jacob Bridgeman.
- **T6 (-11):** Taylor Pendrith, Lee Hodges, Harry Hall, Daniel Berger, Davis Riley.

Sources: PGA Tour, CBS Sports, GolfMagic, Sportskeeda, Golfweek.

**Note on Daniel Berger:** One source (CBS Sports player results) stated Berger missed the cut at the 2026 Sony Open. Multiple tournament recap sources listed him in the T6 group (e.g. GolfMagic). This audit uses **T6** to align with the published final leaderboard; if a definitive source later shows MC, update to MC.

---

## 3. Errors found and corrections

| Player | Our data (before) | Verified / correct | Action |
|--------|-------------------|---------------------|--------|
| **Scottie Scheffler** | AmEx 1st • **Sony Open T2** • Hero 1st • DP World T8 | Did not play Sony Open | **Remove** “Sony Open (Jan 2026): T2” |
| **Davis Riley** | Sony Open (Jan 2026): **T23** | T6 | **T23 → T6** |
| **Patrick Rodgers** | Sony Open (Jan 2026): **T33** | 3rd | **T33 → 3rd** (or T3) |
| **Jacob Bridgeman** | American Express (Jan 2026): T13 only | Sony Open T4 | **Add** “Sony Open (Jan 2026): T4” |
| **Harry Hall** | Sony Open (Jan 2026): **T27** | T6 | **T27 → T6** |
| **Daniel Berger** | Sony Open (Jan 2026): **T23** | T6 (see note above) | **T23 → T6** |

---

## 4. Corrected recent-form text (snippets)

- **Scottie Scheffler:**  
  `American Express (Jan 2026): 1st • Hero World Challenge (Dec 2025): 1st • DP World Tour Championship (Nov 2025): T8`  
  (No Sony Open.)

- **Davis Riley:**  
  … `Sony Open (Jan 2026): T6` …

- **Patrick Rodgers:**  
  … `Sony Open (Jan 2026): 3rd` …

- **Jacob Bridgeman:**  
  `American Express (Jan 2026): T13 • Sony Open (Jan 2026): T4`

- **Harry Hall:**  
  … `Sony Open (Jan 2026): T6` …

- **Daniel Berger:**  
  … `Sony Open (Jan 2026): T6` …

---

## 5. Spot-check – other Sony Open 2026 mentions

From our JSON, these players had a Sony Open (Jan 2026) result. Cross-check with verified leaderboard:

| Player | Our value | Verified | Status |
|--------|-----------|--------|--------|
| Chris Gotterup | Won | 1st | ✓ |
| Cameron Young | T35 | (not in top 6; not verified) | — |
| Si Woo Kim | T34 | (not in top 6; not verified) | — |
| Sam Burns | T15 | (not in top 6; not verified) | — |
| Collin Morikawa | MC | (not verified) | — |
| Matt McCarty | T17 | (not in top 6; not verified) | — |
| Patrick Rodgers | T33 | 3rd | **Fixed to 3rd** |
| Davis Riley | T23 | T6 | **Fixed to T6** |
| Harry Hall | T27 | T6 | **Fixed to T6** |
| Daniel Berger | T23 | T6 | **Fixed to T6** |
| Jacob Bridgeman | (none) | T4 | **Added T4** |

No other top-6 Sony finishers in our field were found with wrong positions in the sampled set.

---

## 6. How the error likely happened

- **Scottie Scheffler Sony T2:** Scheffler did not play Sony Open. “T2” may have been confused with his AmEx win and/or another player’s Sony result (e.g. Ryan Gerard 2nd, or Matt McCarty T2 at AmEx), or pasted from a template.
- **Sony Open positions (T23, T27, T33):** Possible mix-up of player names, wrong event year, or use of an incomplete/incorrect leaderboard when building the cache or fallback.

**Recommendation:** When populating recent form (cache or scripts), prefer official PGA Tour leaderboards and player-by-player result lookups. For stars (e.g. Scheffler), confirm they actually played the event before adding a result.

---

## 7. Files updated

- **`data/wm_phoenix_open_2026_recent_form.json`:** Applied all six corrections above.
- **Optional:** Update `data/player_recent_form_cache.json` with the same text for these players so future runs of `generate_wm_phoenix_recent_form.py` do not overwrite with old data.
- **Regenerate HTML:** Run `python3 scripts/assemble_wm_phoenix_html.py` so the “Recent Form” column reflects the fixes.

---

## 8. Summary

| Check | Result |
|-------|--------|
| Scottie Scheffler Sony Open | **Error** – did not play; removed Sony T2 |
| Sony Open 2026 top 6 vs our data | **6 fixes** – Davis Riley, Patrick Rodgers, Jacob Bridgeman, Harry Hall, Daniel Berger, plus Scheffler removal |
| American Express 2026 | Spot-check: Scheffler 1st, Matt McCarty T2 ✓ |
| Other recent form | No full event-by-event audit; recommend periodic web verification of key events |

**Root cause:** Scheffler was given a Sony Open result despite not playing; several Sony finishes were wrong (wrong position or missing). Aligning with web-verified leaderboards and correcting the JSON (and optionally the cache) prevents these from reappearing in the preview.
