# Storylines Audit — Genesis Invitational 2026

**Audit date:** 2026-02-17  
**File:** `data/the_genesis_invitational_2026_storylines.json`

## Summary

The Genesis Invitational 2026 storylines were audited for factual accuracy, tone, and clarity. Three factual/consistency issues were corrected in the JSON (including Palisades fire / Torrey relocation for Aberg); the storyline generator script was updated to reduce similar issues in future runs.

---

## What Was Checked

- **Factual accuracy:** Course history (finishes, years), major/title claims, world rankings, tournament names.
- **Consistency:** “Last year” = 2025; “defending champion” only for the actual defender (Ludvig Aberg); “debut” only when the player has no prior starts at the event.
- **Tone:** Professional, specific, betting-preview style; avoiding filler and overused phrases.

---

## Corrections Made

### 1. Max McGreevy — “Debut” vs. course history

- **Issue:** Text said “Making his Genesis Invitational debut after missing the cut in 2023.” If he played in 2023 (and missed the cut), 2026 is not his debut.
- **Change:** Replaced with: “Returning to Riviera after a missed cut in 2023, McGreevy arrives with improved course management skills and a more mature approach to elite competition.”

### 2. Hideki Matsuyama — “Defending champion”

- **Issue:** Hideki won in 2024; the defending champion for 2026 is Ludvig Aberg (2025 winner). The line “defending champions often find extra motivation” was misleading in Hideki’s blurb.
- **Change:** Wording updated to: “past champions often find extra motivation returning to their breakthrough venues.”

### 3. Ludvig Aberg — Palisades fire / Torrey Pines relocation

- **Issue:** Last year's Genesis was held at Torrey Pines after the Palisades fire forced relocation from Riviera; Aberg won there. The original storyline implied he had proven Riviera form.
- **Change:** Rewritten to state that he is defending champion but won last year at Torrey Pines (Palisades fire relocation), and that this week he'll be playing Riviera proper for the first time as titleholder.

---

## Verified as Correct

- **Xander Schauffele:** “Two-time major champion” — correct (2024 PGA Championship + 2024 Open Championship).
- **Ludvig Aberg:** “Genesis victory last year” — correct; event was at Torrey Pines (Palisades fire relocation). Storyline updated to call out the relocation and that this year he plays Riviera proper for the first time as defending champion.
- **J.J. Spaun:** “Reigning U.S. Open champion” — correct (2025 U.S. Open at Oakmont).
- **Hideki Matsuyama:** “2024 Genesis Invitational champion” — correct.
- **Baycurrent Classic:** Correct event name (Xander Schauffele win).
- **BoU Championship:** Correct (Rico Hoey runner-up).
- **OWGR in copy:** Ben Griffin (8), Chris Gotterup (17), Robert MacIntyre (6), etc. — aligned with `the_genesis_invitational_2026_players_data.json`.

---

## Tone & Repetition (No Edits This Pass)

- Phrases like “perfectly suited” and “elite iron play” appear often across players. Content remains accurate and professional; for future generations, the script was updated to encourage varied wording (e.g. “well-suited”, “ideally suited”, “strong iron play”, “precise approach play”).
- Storylines are generally 2–3 sentences, course- and data-specific, and avoid vague filler (“could surprise”, “don’t overlook”).

---

## Generator Updates (`scripts/generate_ai_storylines_claude.py`)

- Do not use “making his debut” when the player has any prior appearance (e.g. a past MC).
- Vary phrasing; avoid repeating “perfectly suited” / “elite iron play” across many players.
- Use “defending champion” only for the actual defending champion of the event.

---

## Recommendation

Storylines read as intelligent and suitable for a professional betting preview. The two corrections above improve accuracy and consistency; the script changes should keep future storylines in the same quality range with less repetition and fewer debut/defending-champion slips.
