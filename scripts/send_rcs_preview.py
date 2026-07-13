#!/usr/bin/env python3
"""Build (and optionally send) a branded RCS preview of the weekly betting board.

Turns the already-generated AI content into a "Golf in the Cosmos" RCS message:
an opener text bubble, a hero card, and a swipeable carousel of top-story cards
with automated player headshots and a button to the full preview.

USAGE
  # Free, no account needed — writes a local phone-style HTML mockup you can open:
  python scripts/send_rcs_preview.py --dry-run

  # Real send (requires a registered Sinch RCS agent + test devices in .env):
  python scripts/send_rcs_preview.py --send --to +19498874199

NOTES
  * --dry-run is the default. It NEVER hits the network for sending; it only
    builds the payload + an HTML preview. (It may call DataGolf once to resolve
    player headshots, then caches them — use --no-network to skip even that.)
  * Branded RCS can only ORIGINATE through a partner-registered agent. Sending
    to registered TEST DEVICES is free; a blast to a real list is paid per
    message via the carrier, regardless of this custom code.
"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import re
import sys
import time
import uuid
from datetime import datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception:  # pragma: no cover - dotenv optional
    pass

# --- Brand constants (reused from generate_tournament_html.py) ---------------
LOGO_URL = "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/COSMOS_Golf-Dec-Logo_001.png"
DEFAULT_COURSE_IMAGE = (
    "https://cdn.shopify.com/s/files/1/0775/8928/3061/files/charles.avif?v=1779751996"
)
DEFAULT_LINK = "https://cosmos-golf.com/pages/weekly-preview"
AGENT_NAME = "Golf in the Cosmos"
# Wikimedia asks for a descriptive User-Agent with contact info, else it 429s.
WIKI_UA = "GolfInTheCosmos/1.0 (https://cosmos-golf.com; realchrismiller@gmail.com)"

# Category -> (emoji, label, accent color) for card styling.
CATEGORY_STYLE = {
    "favorite": ("\U0001F3AF", "TOP DOG", "#0a7a3f"),
    "value": ("\U0001F4B0", "VALUE", "#005bbb"),
    "longshot": ("\U0001F680", "LONGSHOT", "#b07d00"),
    "course_fit": ("\U0001F3CC", "COURSE FIT", "#005bbb"),
    "form": ("\U0001F4C8", "IN FORM", "#0a7a3f"),
    "avoid": ("⛔", "FADE", "#b00020"),
}
DEFAULT_STYLE = ("⛳", "PICK", "#0B3D91")


def _slugify(name: str) -> str:
    """Convert tournament name to slug (matches generate_tournament_html._slugify)."""
    slug = name.lower().replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _trim(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


# --- Player headshot resolution ----------------------------------------------
def _wikipedia_photo(name: str) -> str:
    """Best-effort free headshot via Wikipedia search + pageimages (no API key).

    Searches '<name> golfer', takes the top page, returns its thumbnail. Handles
    diacritics (e.g. 'Ludvig Aberg' -> 'Ludvig Åberg') because it goes through
    search rather than an exact title.
    """
    try:
        import httpx
    except ImportError:
        return ""
    params = {
        "action": "query",
        "format": "json",
        "prop": "pageimages",
        "piprop": "thumbnail",
        "pithumbsize": "400",
        "generator": "search",
        "gsrsearch": f"{name} golfer",
        "gsrlimit": "1",
        "redirects": "1",
    }
    try:
        resp = httpx.get(
            "https://en.wikipedia.org/w/api.php",
            params=params,
            headers={"User-Agent": WIKI_UA},
            timeout=15,
        )
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            thumb = (page.get("thumbnail") or {}).get("source")
            if thumb:
                return thumb
    except Exception:
        pass
    return ""


def resolve_photos(
    player_names: list[str],
    cache_path: Path,
    use_network: bool,
) -> dict[str, str]:
    """Return {player_name: headshot_url}, cached to disk so we fetch once.

    DataGolf's player list on this plan has no espn_id, so photos are sourced
    by name from Wikipedia (free, no key). Cache values: a URL, or "" if a
    lookup was attempted and found nothing (so we don't retry every run).
    """
    cache: dict[str, str] = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text())
        except Exception:
            cache = {}

    dirty = False
    for name in player_names:
        if name in cache:
            continue
        if not use_network:
            cache[name] = ""
            continue
        cache[name] = _wikipedia_photo(name)
        dirty = True

    if dirty:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False))

    return {name: cache.get(name, "") for name in player_names}


# --- Payload construction (provider-agnostic) --------------------------------
def build_payload(
    insights: dict,
    photos: dict[str, str],
    link: str,
    course_image: str,
    max_cards: int,
) -> dict:
    """Build a provider-agnostic message bundle: opener + hero + carousel."""
    tournament = insights.get("tournament", "This Week")
    summary = insights.get("executive_summary", "")
    cards_in = insights.get("insights", [])[:max_cards]

    opener = f"⛳ {tournament} is live — here's the COSMOS board. Top plays →"

    hero = {
        "title": tournament,
        "description": _trim(summary, 900),
        "media_url": course_image,
        "button": {"text": "View Full Board", "url": link},
    }

    cards = []
    for ins in cards_in:
        players = ins.get("players", [])
        primary = players[0] if players else ""
        emoji, label, color = CATEGORY_STYLE.get(
            ins.get("category", ""), DEFAULT_STYLE
        )
        photo = photos.get(primary, "")
        cards.append(
            {
                "title": _trim(ins.get("title", ""), 100),
                "description": _trim(ins.get("insight", ""), 480),
                "media_url": photo or LOGO_URL,
                "has_photo": bool(photo),
                "player": primary,
                "label": label,
                "label_emoji": emoji,
                "accent": color,
                "button": {"text": "Read more", "url": link},
            }
        )

    return {
        "agent": AGENT_NAME,
        "logo": LOGO_URL,
        "tournament": tournament,
        "link": link,
        "opener": opener,
        "hero": hero,
        "cards": cards,
        "suggestions": [
            {"text": "Full board", "url": link},
            {"text": "Crew picks", "url": link},
        ],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


# --- Local HTML mockup (phone-style preview) ---------------------------------
def _image_data_uri(url: str) -> str:
    """Download an image and return a base64 data URI ("" on failure)."""
    if not url or url.startswith("data:"):
        return url
    try:
        import httpx
    except ImportError:
        return ""
    for attempt in range(3):
        try:
            r = httpx.get(
                url, headers={"User-Agent": WIKI_UA}, timeout=20, follow_redirects=True
            )
            if r.status_code == 200:
                ctype = r.headers.get("content-type", "image/jpeg").split(";")[0]
                b64 = base64.b64encode(r.content).decode("ascii")
                return f"data:{ctype};base64,{b64}"
        except Exception:
            pass
        time.sleep(1.5 * (attempt + 1))
    return ""


def embed_preview_images(payload: dict) -> dict:
    """Return a copy of payload with image URLs inlined as data URIs so the
    local HTML always renders (independent of browser-side rate limits).
    Falls back to the remote URL if a download fails."""
    p = copy.deepcopy(payload)
    for card in [p["hero"]] + p["cards"]:
        inlined = _image_data_uri(card["media_url"])
        if inlined:
            card["media_url"] = inlined
        time.sleep(0.3)
    return p


def render_preview_html(payload: dict) -> str:
    def card_html(c: dict, hero: bool = False) -> str:
        img_style = "object-fit:cover;" if (hero or c.get("has_photo")) else "object-fit:contain;padding:18px;background:#0B3D91;"
        badge = ""
        if not hero and c.get("label"):
            badge = (
                f'<span class="badge" style="background:{c["accent"]}">'
                f'{escape(c["label_emoji"])} {escape(c["label"])}</span>'
            )
        sub = ""
        if not hero and c.get("player"):
            sub = f'<div class="card-player">{escape(c["player"])}</div>'
        return f"""
        <div class="card{' hero' if hero else ''}">
          <div class="card-img-wrap">{badge}
            <img src="{escape(c['media_url'])}" alt="" style="{img_style}"
                 onerror="this.onerror=null;this.src='{escape(payload['logo'])}';this.style.objectFit='contain';this.style.padding='18px';this.style.background='#0B3D91';">
          </div>
          <div class="card-body">
            {sub}
            <div class="card-title">{escape(c['title'])}</div>
            <div class="card-desc">{escape(c['description'])}</div>
            <a class="card-btn" href="{escape(c['button']['url'])}" target="_blank">{escape(c['button']['text'])}</a>
          </div>
        </div>"""

    carousel = "".join(card_html(c) for c in payload["cards"])
    suggestions = "".join(
        f'<a class="chip" href="{escape(s["url"])}" target="_blank">{escape(s["text"])}</a>'
        for s in payload["suggestions"]
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RCS Preview — {escape(payload['tournament'])}</title>
<style>
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:#1c1c1e; font-family:-apple-system,Segoe UI,Roboto,sans-serif; color:#111; padding:24px 0; }}
  .phone {{ max-width:420px; margin:0 auto; background:#e9edf2; border-radius:32px; overflow:hidden; box-shadow:0 12px 40px rgba(0,0,0,.5); border:10px solid #000; }}
  .agent-bar {{ display:flex; align-items:center; gap:10px; padding:14px 16px; background:#fff; border-bottom:1px solid #dde2e8; }}
  .agent-bar img {{ width:38px; height:38px; border-radius:50%; object-fit:contain; background:#0B3D91; padding:3px; }}
  .agent-name {{ font-weight:700; font-size:15px; display:flex; align-items:center; gap:5px; }}
  .verified {{ color:#1a73e8; font-size:13px; }}
  .agent-sub {{ font-size:11px; color:#6c757d; }}
  .convo {{ padding:16px 12px 22px; min-height:300px; background:linear-gradient(#eef1f5,#e4e9f0); }}
  .bubble {{ background:#fff; border-radius:18px 18px 18px 4px; padding:11px 14px; font-size:14px; line-height:1.4; max-width:80%; margin-bottom:14px; box-shadow:0 1px 1px rgba(0,0,0,.08); }}
  .carousel {{ display:flex; gap:12px; overflow-x:auto; padding:2px 2px 12px; scroll-snap-type:x mandatory; }}
  .card {{ flex:0 0 230px; scroll-snap-align:start; background:#fff; border-radius:16px; overflow:hidden; box-shadow:0 2px 6px rgba(0,0,0,.14); }}
  .card.hero {{ flex-basis:100%; margin-bottom:16px; }}
  .card-img-wrap {{ position:relative; }}
  .card-img-wrap img {{ width:100%; height:150px; display:block; background:#0B3D91; }}
  .card.hero .card-img-wrap img {{ height:160px; }}
  .badge {{ position:absolute; top:8px; left:8px; color:#fff; font-size:10px; font-weight:800; letter-spacing:.5px; padding:3px 8px; border-radius:20px; }}
  .card-body {{ padding:12px 13px 14px; }}
  .card-player {{ font-size:11px; color:#6c757d; font-weight:600; margin-bottom:3px; }}
  .card-title {{ font-weight:800; font-size:14px; line-height:1.25; margin-bottom:6px; color:#0B3D91; }}
  .card-desc {{ font-size:12px; line-height:1.4; color:#333; margin-bottom:12px; }}
  .card-btn {{ display:block; text-align:center; text-decoration:none; font-weight:700; font-size:13px; color:#0B3D91; border:1px solid #0B3D91; border-radius:20px; padding:8px; }}
  .card.hero .card-btn {{ background:#0B3D91; color:#fff; }}
  .chips {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:4px; }}
  .chip {{ text-decoration:none; font-size:13px; font-weight:600; color:#0B3D91; background:#fff; border:1px solid #b9c6da; border-radius:20px; padding:7px 14px; }}
  .note {{ max-width:420px; margin:14px auto 0; color:#aab; font-size:12px; text-align:center; line-height:1.5; }}
  .note b {{ color:#fff; }}
</style></head>
<body>
  <div class="phone">
    <div class="agent-bar">
      <img src="{escape(payload['logo'])}" alt="logo">
      <div>
        <div class="agent-name">{escape(payload['agent'])} <span class="verified">✔ verified</span></div>
        <div class="agent-sub">Business · RCS</div>
      </div>
    </div>
    <div class="convo">
      <div class="bubble">{escape(payload['opener'])}</div>
      {card_html(payload['hero'], hero=True)}
      <div class="carousel">{carousel}</div>
      <div class="chips">{suggestions}</div>
    </div>
  </div>
  <div class="note">Local mockup of the branded RCS message · {len(payload['cards'])} story cards<br>
  <b>{escape(payload['agent'])}</b> · generated {escape(payload['generated_at'])}</div>
</body></html>"""


# --- Sinch RCS send (guarded; requires registered agent + creds) -------------
def to_sinch_messages(payload: dict, to: str) -> list[dict]:
    """Map the provider-agnostic payload to Sinch RCS API message bodies.

    NOTE: exact endpoint/fields depend on your Sinch RCS agent + region; confirm
    against your account. This builds an opener text + a carousel_card message.
    """
    opener = {
        "to": [to],
        "message_id": str(uuid.uuid4()),
        "message": {"text_message": {"message": payload["opener"]}},
    }
    card_contents = []
    for c in [payload["hero"]] + payload["cards"]:
        card_contents.append(
            {
                "title": c["title"],
                "description": c["description"],
                "media": {
                    "height": "MEDIUM",
                    "content_info": {"file_url": c["media_url"], "force_refresh": False},
                },
                "suggestions": [
                    {
                        "action": {
                            "text": c["button"]["text"],
                            "post_back_data": "open_link",
                            "open_url_action": {"url": c["button"]["url"]},
                        }
                    }
                ],
            }
        )
    carousel = {
        "to": [to],
        "message_id": str(uuid.uuid4()),
        "message": {
            "carousel_card": {"card_width": "MEDIUM", "card_contents": card_contents}
        },
    }
    return [opener, carousel]


def send_via_sinch(payload: dict, recipients: list[str]) -> int:
    import os

    bot_id = os.environ.get("SINCH_RCS_BOT_ID")
    token = os.environ.get("SINCH_RCS_TOKEN")
    region = os.environ.get("SINCH_RCS_REGION", "us")
    if not bot_id or not token:
        print(
            "✗ Cannot send: SINCH_RCS_BOT_ID and SINCH_RCS_TOKEN must be set in .env.\n"
            "  Set up a (free) Sinch RCS agent, register your test devices, then add creds.\n"
            "  Until then, use --dry-run to preview the message for free."
        )
        return 1
    try:
        import httpx
    except ImportError:
        print("✗ httpx is required to send. pip install httpx")
        return 1

    base = f"https://{region}.rcs.api.sinch.com/rcs/v1/{bot_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    sent = 0
    with httpx.Client(timeout=30) as client:
        for to in recipients:
            for body in to_sinch_messages(payload, to):
                resp = client.post(base, headers=headers, json=body)
                if resp.status_code < 300:
                    sent += 1
                    print(f"  ✓ sent {body['message']and list(body['message'])[0]} to {to}")
                else:
                    print(f"  ✗ {to}: HTTP {resp.status_code} {resp.text[:200]}")
    print(f"Done: {sent} message(s) accepted by Sinch.")
    return 0 if sent else 1


# --- main --------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tournament", default="Charles Schwab Challenge")
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--out-dir", default=str(ROOT / "out"))
    ap.add_argument("--link", default=DEFAULT_LINK, help="Full-preview URL the buttons open")
    ap.add_argument("--course-image", default=DEFAULT_COURSE_IMAGE)
    ap.add_argument("--max-cards", type=int, default=8)
    ap.add_argument("--no-network", action="store_true", help="Skip DataGolf headshot lookup")
    ap.add_argument("--send", action="store_true", help="Actually send via Sinch (needs creds + agent)")
    ap.add_argument("--to", nargs="*", default=[], help="Recipient numbers in E.164, e.g. +19498874199")
    ap.add_argument("--dry-run", action="store_true", help="Build payload + HTML only (default)")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    slug = _slugify(args.tournament)
    base = f"{slug}_{args.year}"

    insights_path = data_dir / f"{base}_insights.json"
    if not insights_path.exists():
        print(f"✗ Missing {insights_path}. Run generate_ai_insights.py first.")
        return 1

    insights = json.loads(insights_path.read_text())

    # Players we need photos for = the lead player of each card.
    lead_players = [
        (ins.get("players") or [""])[0]
        for ins in insights.get("insights", [])[: args.max_cards]
    ]
    photos = resolve_photos(
        [p for p in lead_players if p],
        data_dir / "player_photo_cache.json",
        use_network=not args.no_network,
    )

    payload = build_payload(
        insights, photos, args.link, args.course_image, args.max_cards
    )

    # Default behaviour is dry-run unless --send is explicitly given.
    if args.send:
        return send_via_sinch(payload, args.to or [])

    out_dir.mkdir(parents=True, exist_ok=True)
    payload_path = out_dir / f"{base}_rcs_payload.json"
    html_path = out_dir / f"{base}_rcs_preview.html"
    payload_path.write_text(json.dumps(payload, indent=2))
    # Inline images for the preview only; payload JSON keeps real remote URLs.
    preview_payload = payload if args.no_network else embed_preview_images(payload)
    html_path.write_text(render_preview_html(preview_payload))
    photo_n = sum(1 for c in payload["cards"] if c["has_photo"])
    print(f"✓ Built {len(payload['cards'])} story cards ({photo_n} with player photos).")
    print(f"  payload: {payload_path}")
    print(f"  preview: {html_path}")
    print(f"  open it:  open {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
