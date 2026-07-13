# Deploy Full Preview to Shopify (All Features)

Shopify page body is limited to **64 KB**. The full preview is ~1 MB, so we use an **iframe**: the page stores a tiny snippet that loads the full preview from a URL. You keep the full design (exec summary, 4-column table, dropdowns, matchups, all players).

**Single source of truth:** The main preview is produced only by **generate_tournament_html.py**. Do not use **assemble_wm_phoenix_html.py** output for Shopify (that script writes the flat cheatsheet to `*_cheatsheet.html`).

## Steps

### 1. Generate the preview

```bash
python3 scripts/generate_tournament_html.py --tournament "WM Phoenix Open" --year 2026 --output wm_phoenix_open_2026.html --shopify
```

This creates:

- **wm_phoenix_open_2026.html** — full preview (4-col, dropdowns, exec summary). Use this as the file you upload to Files.
- **wm_phoenix_open_2026_shopify.html** — same design but ~204 KB (still over 64 KB; do not paste into page body).
- **wm_phoenix_open_2026_shopify_embed.html** — small iframe snippet (in repo). Paste into Shopify after replacing the URL placeholder.

### 2. Host the full preview and get a URL

**Option A — Shopify Files**

1. In Shopify: **Settings → Files → Upload files**
2. Upload **wm_phoenix_open_2026.html**
3. Click the file and copy its URL (e.g. `https://cdn.shopify.com/s/files/1/0775/8928/3061/files/wm_phoenix_open_2026.html?vid=...`)

If the iframe is blank, Shopify’s CDN may block embedding. Use Option B.

**Option B — GitHub Pages / Netlify / your site**

1. Host **wm_phoenix_open_2026.html** on a site that allows iframes (e.g. GitHub Pages, Netlify, your domain).
2. Use that page URL (e.g. `https://yourusername.github.io/CosmosGolfBetting/wm_phoenix_open_2026.html`).

### 3. Point the embed at that URL

1. Open **wm_phoenix_open_2026_shopify_embed.html**
2. Replace `REPLACE_WITH_PREVIEW_URL` with the URL from step 2 (no quotes)
3. Save the file

### 4. Put the embed on Shopify

**Paste**

1. In Shopify: **Online Store → Pages → (your preview page) → Show HTML**
2. Paste the **entire** contents of **wm_phoenix_open_2026_shopify_embed.html**
3. Save

**Or deploy via script**

```bash
python3 scripts/deploy_to_shopify.py --html wm_phoenix_open_2026_shopify_embed.html --page-handle weekly-preview
```

(Requires `SHOPIFY_STORE_URL` and `SHOPIFY_ACCESS_TOKEN`.)

---

Result: the Shopify page shows the full preview in an iframe — exec summary, 4-column table, search, dropdowns, matchups, and full player table with no 64 KB truncation.

**If you still see an old layout:** Hard refresh (Ctrl+Shift+R / Cmd+Shift+R) or open in incognito; ensure the file you uploaded to Files is the current **wm_phoenix_open_2026.html** from step 1.
