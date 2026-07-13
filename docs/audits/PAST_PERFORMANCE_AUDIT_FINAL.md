# WM Phoenix Open – Past Player Performance Audit (Final)

**Audit date:** February 2, 2026  
**Source of truth:** `WM Past perf.pdf`  
**Data checked:** `data/wm_phoenix_open_2026_players_data.json` → `historical`  
**Display:** `wm_phoenix_open_2026.html` (2025, 2024, 2023 columns)

---

## Scope

- **2025** WM Phoenix: full leaderboard + cuts + WD vs our `historical[*].2025`
- **2024** WM Phoenix: sample of positions vs our `historical[*].2024`
- **2023** WM Phoenix: where we have data (e.g. Scheffler 1) vs PDF
- **JSON → HTML:** historical values in JSON match the rendered result cells

---

## 1. 2025 results (PDF vs JSON)

### 1.1 Top finishers and made cuts

| PDF 2025 (abbrev) | Pos | Our data (full name) | Our 2025 | Match |
|-------------------|-----|----------------------|----------|--------|
| T. Detry | 1 | Thomas Detry | 1 | ✓ |
| M. Kim, D. Berger | T2 | Michael Kim, Daniel Berger | T2 | ✓ |
| J. Spieth, C. Bezuidenhout | T4 | Jordan Spieth, Christiaan Bezuidenhout | T4 | ✓ |
| J. Thomas, W. Chandler, R. MacIntyre | T6 | Justin Thomas, Will Chandler, Robert MacIntyre | T6 | ✓ |
| M. McNealy, T. Moore, A. Hadwin | T9 | Maverick McNealy, Taylor Moore, Adam Hadwin | T9 | ✓ |
| R. Højgaard, M.W. Lee, C. Young | T12 | Rasmus Hojgaard, Min Woo Lee, Cameron Young | T12 | ✓ |
| J. Straka | 15 | Sepp Straka | 15 | ✓ |
| B. Silverman … W. Clark | T16 | Ben Silverman … Wyndham Clark | T16 | ✓ |
| B. Cauley … A. Smalley | T21 | Bud Cauley … Alex Smalley | T21 | ✓ |
| N. Taylor … K. Mitchell | T25 | Nick Taylor … Keith Mitchell | T25 | ✓ |
| T. Mullinax … A. Bhatia | T32 | Trey Mullinax … Akshay Bhatia | T32 | ✓ |
| S. Power … A. Svensson | T36 | Seamus Power … Adam Svensson | T36 | ✓ |
| S. Stevens … T. Kim | T44 | Sam Stevens … Tom Kim | T44 | ✓ |
| D. Skinns … D. Ghim | T49 | David Skinns … Doug Ghim | T49 | ✓ |
| C. Young, N. Dunlap … C.T. Pan | T57 | Charley Young, Nick Dunlap … C.T. Pan | T57 | ✓ |
| J. Svensson … M. Pavon | T63 | Jesper Svensson … Matthieu Pavon | T63 | ✓ |
| B. Snedeker | 66 | Brandt Snedeker | 66 | ✓ |
| K.H. Lee, B. Garnett | T67 | K.H. Lee, Brice Garnett | T67 | ✓ |
| W. Gordon, T. Montgomery | T69 | Will Gordon, Taylor Montgomery | T69 | ✓ |
| V. Norman, K. Streelman | T71 | Vincent Norman, Kevin Streelman | T71 | ✓ |
| B.H. An | 73 | Byeong Hun An | 73 | ✓ |
| C. Conners, M. Thorbjornsen | T74 | Corey Conners, Michael Thorbjornsen | T74 | ✓ |
| E. Grillo | 76 | Emiliano Grillo | 76 | ✓ |
| R. Palmer | 77 | Ryan Palmer | 77 | ✓ |

**Conclusion:** All 2025 made-cut positions in our data match the PDF.

### 1.2 2025 missed cuts (PDF Cut list vs JSON)

PDF 2025 Cut list includes (among others):  
B. Kohles, L. Clanton, N. Hardy, L. Griffin, B. Martin, R. Hisatsune, A. Novak, H. Hall, **W. Simpson**, M. Fitzpatrick, P. Fishburn, L. Glover, J. Highsmith, M. McGreevy, C. Gotterup, N. Lashley, M. Meissner, K. Kisner, **R. Campos**, P. Kizzire, E. van Rooyen, B. Horschel, A. Eckroat, J. Dahmen, J. Bridgeman, S. Välimäki, M. Hubbard, C. Reavie, N. Echavarria, R. Hoey, V. Perez, H. Norlander, P. Waring, D. Lipsky, M. McCarty, M. Homa, S. Fisk, M. Schmid, C. Hoffman, V. Whaley, C. Kirk, C. Kim, H. Springer, J. Ballester, C. Ramey, E. Cole, P. Rodgers, D. Riley, F. Capan, J. Mueller, T. Hoge, T. Lawrence, B. Todd.

| Player (PDF abbrev) | Our name | JSON 2025 before audit | PDF 2025 | Action |
|---------------------|----------|------------------------|----------|--------|
| W. Simpson | Webb Simpson | NA | Cut | **Corrected to MC** |
| R. Campos | Rafael Campos | NA | Cut | **Corrected to MC** |
| M. Fitzpatrick | Matt Fitzpatrick | MC | Cut | ✓ |
| C. Gotterup | Chris Gotterup | MC | Cut | ✓ |
| A. Novak | Andrew Novak | MC | Cut | ✓ |
| H. Hall | Harry Hall | MC | Cut | ✓ |
| P. Kizzire | Patton Kizzire | MC | Cut | ✓ |
| B. Horschel | Billy Horschel | MC | Cut | ✓ |
| J. Dahmen | Joel Dahmen | MC | Cut | ✓ |
| J. Bridgeman | Jacob Bridgeman | MC | Cut | ✓ |
| M. McCarty | Matt McCarty | MC | Cut | ✓ |
| M. Homa | Max Homa | MC | Cut | ✓ |
| T. Hoge | Tom Hoge | MC | Cut | ✓ |
| (others in field) | … | MC or NA (not in 2025 field) | Cut / N/A | ✓ |

**Discrepancies found and fixed:**  
- **Webb Simpson:** was `"2025": "NA"`; PDF shows Cut → set to `"2025": "MC"`.  
- **Rafael Campos:** was `"2025": "NA"`; PDF shows Cut → set to `"2025": "MC"`.

### 1.3 2025 WD

| PDF | Our data | Match |
|-----|----------|--------|
| J. J. Spaun | J.J. Spaun WD | ✓ |
| R. Fowler | Rickie Fowler WD | ✓ |

---

## 2. 2024 results (PDF vs JSON)

Sample check (from PDF 2024 leaderboard):

| PDF 2024 | Our data (sample) | Match |
|----------|-------------------|--------|
| 1 N. Taylor | Nick Taylor 1 | ✓ |
| 2 C. Hoffman | Charley Hoffman 2 | ✓ |
| T3 S. Scheffler, S. Burns | Scottie Scheffler T3, Sam Burns T3 | ✓ |
| 5 S. Theegala | Sahith Theegala 5 | ✓ |
| T6 J. Spieth, M. McNealy | Jordan Spieth T6, Maverick McNealy T6 | ✓ |
| T8 A. Novak, K. Kitayama, C. Young, A. Scott | Andrew Novak T8, Kurt Kitayama T8, Cameron Young T8, Adam Scott T8 | ✓ |
| T12 J. Thomas, S.W. Kim, D. Ghim | Justin Thomas T12, Si Woo Kim T12, Doug Ghim T12 | ✓ |
| T15 D. Thompson, M. Fitzpatrick | Davis Thompson T15, Matt Fitzpatrick T15 | ✓ |
| T17 A. Schenk, T. Kim, H. English, T. Hoge, K. Mitchell | Adam Schenk T17, Tom Kim T17, Harris English T17, Tom Hoge T17, Keith Mitchell T17 | ✓ |
| T22 E. Grillo, H. Matsuyama, D. McCarthy, J. Vegas, … | Emiliano Grillo T22, Hideki Matsuyama T22, Denny McCarthy T22, Jhonattan Vegas T22 | ✓ |
| T28 B. Griffin, S. Stevens, J. Knapp, T. Detry, C. Conners, … | Ben Griffin T28, Sam Stevens T28, Jake Knapp T28, Thomas Detry T28, Corey Conners T28 | ✓ |
| 65 B. Cauley | Bud Cauley 65 | ✓ |
| T71 M.W. Lee | Min Woo Lee T71 | ✓ |

**Conclusion:** 2024 sample matches PDF. No 2024 corrections applied.

---

## 3. 2023 results

- PDF includes 2023; our JSON uses `"2023": "1"` for Scheffler and `"2023": "NA"` where no finish.
- Scheffler 2023 win (1) matches PDF.

**Conclusion:** No 2023 discrepancies.

---

## 4. JSON → HTML

- `assemble_wm_phoenix_html.py` reads `data["historical"][name]["2025"|"2024"|"2023"]` and renders in result cells.
- Spot-check: Scheffler (T25, T3, 1), Cameron Young (T12, T8, NA), Ben Griffin (T36, T28, NA), Matt Fitzpatrick (MC, T15, NA), Jake Knapp (T44, T28, NA) — HTML matches JSON.

**Conclusion:** Display is consistent with JSON.

---

## 5. Summary

| Check | Status | Notes |
|-------|--------|--------|
| 2025 made-cut positions | ✓ | All match PDF |
| 2025 missed cuts | ✓ (after fix) | Webb Simpson, Rafael Campos set to MC |
| 2025 WD | ✓ | J.J. Spaun, Rickie Fowler |
| 2024 sample | ✓ | No changes |
| 2023 | ✓ | No changes |
| JSON → HTML | ✓ | Values match |

**Files updated:**  
- `data/wm_phoenix_open_2026_players_data.json`: `historical["Webb Simpson"]["2025"]` = `"MC"`, `historical["Rafael Campos"]["2025"]` = `"MC"`.

**Recommended next step:** Re-run `python3 scripts/assemble_wm_phoenix_html.py` so the HTML shows MC for Webb Simpson and Rafael Campos in the 2025 column.
