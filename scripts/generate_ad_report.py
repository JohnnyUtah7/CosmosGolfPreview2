#!/usr/bin/env python3
"""Render a daily Meta (Facebook/Instagram) ad-spend report for Golf in the Cosmos.

This is the rendering half of the `ad-report` skill. The *metrics* are gathered
by the agent via the Meta Ads MCP (ads_get_ad_entities) and written to a JSON
file; this script turns that JSON into:

  * out/ad_report_{date}.html  — Gmail-safe HTML (inline styles, navy/gold brand),
    ready to drop into a Gmail draft via the Gmail MCP.
  * a plaintext TL;DR printed to stdout (for a quick glance / text summary).

Report-only by design: it presents numbers and day-over-day deltas. It does NOT
recommend pausing ads or changing budgets — the human stays in control.

Input JSON schema (all metric fields optional; missing => shown as "—"):
{
  "account_name": "Golf in the Cosmos",
  "report_date": "2026-06-01",        # the day the metrics cover
  "compare_date": "2026-05-31",       # prior day for deltas (optional)
  "currency": "USD",
  "totals":      {"spend":.., "impressions":.., "reach":.., "clicks":..,
                  "ctr":.., "cpc":.., "cpm":.., "conversions":.., "roas":..},
  "totals_prev": { ...same shape... },     # optional, drives deltas
  "campaigns": [ {"name":.., "status":.., "spend":.., "impressions":..,
                  "reach":.., "clicks":.., "ctr":.., "cpc":.., "cpm":..,
                  "conversions":.., "roas":..}, ... ],
  "ads": [ {"name":.., "campaign":.., "spend":.., "impressions":..,
            "ctr":.., "cpc":.., "conversions":..}, ... ]   # optional, top movers
}

Usage:
    python3 scripts/generate_ad_report.py --data /tmp/ad_metrics.json
    python3 scripts/generate_ad_report.py --data /tmp/ad_metrics.json --open
"""
import argparse
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "out"

NAVY = "#0b1437"
NAVY2 = "#16204d"
GOLD = "#d4af37"
INK = "#1a2238"
MUTE = "#6b7280"
GOOD = "#1a7f37"
BAD = "#b42318"
LINE = "#e5e7eb"


# ----------------------------- formatting helpers -----------------------------

def _money(v, cur="$"):
    if v is None:
        return "—"
    return f"{cur}{float(v):,.2f}"


def _int(v):
    if v is None:
        return "—"
    return f"{int(round(float(v))):,}"


def _pct(v):
    if v is None:
        return "—"
    return f"{float(v):.2f}%"


def _dec(v):
    if v is None:
        return "—"
    return f"{float(v):.2f}"


def _roas(v):
    if v is None:
        return "—"
    return f"{float(v):.2f}×"


def _delta(curr, prev, *, good_is_up=True, pct=False, money=False):
    """Return (text, color) describing curr vs prev. good_is_up flips the color
    logic for cost metrics where down is good (CPC, CPM)."""
    if curr is None or prev is None or prev == 0:
        return ("", MUTE)
    diff = float(curr) - float(prev)
    if diff == 0:
        return ("±0", MUTE)
    rel = diff / abs(float(prev)) * 100.0
    up = diff > 0
    arrow = "▲" if up else "▼"
    is_good = up if good_is_up else (not up)
    color = GOOD if is_good else BAD
    if money:
        mag = _money(abs(diff))
    elif pct:
        mag = f"{abs(diff):.2f}pp"
    else:
        mag = f"{abs(rel):.0f}%"
    return (f"{arrow} {mag}", color)


# ------------------------------- HTML rendering -------------------------------

def _metric_card(label, value, delta_text="", delta_color=MUTE):
    delta_html = (
        f'<div style="font:600 12px Arial,sans-serif;color:{delta_color};margin-top:4px">{escape(delta_text)}</div>'
        if delta_text else ""
    )
    return f"""
    <td style="padding:6px" valign="top" width="33%">
      <div style="background:#ffffff;border:1px solid {LINE};border-radius:10px;padding:14px 16px">
        <div style="font:600 11px Arial,sans-serif;letter-spacing:.06em;text-transform:uppercase;color:{MUTE}">{escape(label)}</div>
        <div style="font:700 22px Arial,sans-serif;color:{INK};margin-top:6px">{value}</div>
        {delta_html}
      </div>
    </td>"""


def _totals_grid(t, p, cur):
    """Six headline metric cards with deltas vs prior day."""
    sym = "$" if cur == "USD" else ""
    cells = []

    spend_d = _delta(t.get("spend"), p.get("spend"), good_is_up=True, money=True)
    cells.append(_metric_card("Spend", _money(t.get("spend"), sym), *spend_d))

    reach_d = _delta(t.get("reach"), p.get("reach"))
    cells.append(_metric_card("Reach", _int(t.get("reach")), *reach_d))

    impr_d = _delta(t.get("impressions"), p.get("impressions"))
    cells.append(_metric_card("Impressions", _int(t.get("impressions")), *impr_d))

    ctr_d = _delta(t.get("ctr"), p.get("ctr"), pct=True)
    cells.append(_metric_card("CTR", _pct(t.get("ctr")), *ctr_d))

    cpc_d = _delta(t.get("cpc"), p.get("cpc"), good_is_up=False, money=True)
    cells.append(_metric_card("CPC", _money(t.get("cpc"), sym), *cpc_d))

    conv_d = _delta(t.get("conversions"), p.get("conversions"))
    cells.append(_metric_card("Conversions", _int(t.get("conversions")), *conv_d))

    rows = []
    for i in range(0, len(cells), 3):
        rows.append("<tr>" + "".join(cells[i:i + 3]) + "</tr>")
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 -6px">{"".join(rows)}</table>'


def _campaign_table(campaigns, cur):
    if not campaigns:
        return ""
    sym = "$" if cur == "USD" else ""
    head_cells = ["Campaign", "Status", "Spend", "Reach", "CTR", "CPC", "Conv.", "ROAS"]
    th = "".join(
        f'<th align="{"left" if i == 0 else "right"}" style="font:600 11px Arial,sans-serif;'
        f'text-transform:uppercase;letter-spacing:.05em;color:{MUTE};padding:8px 10px;border-bottom:2px solid {LINE}">{h}</th>'
        for i, h in enumerate(head_cells)
    )
    rows = []
    for c in campaigns:
        status = (c.get("status") or "").upper()
        status_color = GOOD if status == "ACTIVE" else MUTE
        tds = [
            f'<td style="font:600 13px Arial,sans-serif;color:{INK};padding:9px 10px;border-bottom:1px solid {LINE}">{escape(str(c.get("name","—")))}</td>',
            f'<td align="right" style="font:600 11px Arial,sans-serif;color:{status_color};padding:9px 10px;border-bottom:1px solid {LINE}">{escape(status or "—")}</td>',
            f'<td align="right" style="font:400 13px Arial,sans-serif;color:{INK};padding:9px 10px;border-bottom:1px solid {LINE}">{_money(c.get("spend"), sym)}</td>',
            f'<td align="right" style="font:400 13px Arial,sans-serif;color:{INK};padding:9px 10px;border-bottom:1px solid {LINE}">{_int(c.get("reach"))}</td>',
            f'<td align="right" style="font:400 13px Arial,sans-serif;color:{INK};padding:9px 10px;border-bottom:1px solid {LINE}">{_pct(c.get("ctr"))}</td>',
            f'<td align="right" style="font:400 13px Arial,sans-serif;color:{INK};padding:9px 10px;border-bottom:1px solid {LINE}">{_money(c.get("cpc"), sym)}</td>',
            f'<td align="right" style="font:400 13px Arial,sans-serif;color:{INK};padding:9px 10px;border-bottom:1px solid {LINE}">{_int(c.get("conversions"))}</td>',
            f'<td align="right" style="font:400 13px Arial,sans-serif;color:{INK};padding:9px 10px;border-bottom:1px solid {LINE}">{_roas(c.get("roas"))}</td>',
        ]
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return f"""
    <div style="font:700 14px Arial,sans-serif;color:{INK};margin:26px 0 8px">Campaign breakdown</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
      <tr>{th}</tr>
      {"".join(rows)}
    </table>"""


def render_html(d):
    cur = d.get("currency", "USD")
    t = d.get("totals", {}) or {}
    p = d.get("totals_prev", {}) or {}
    report_date = d.get("report_date", "")
    compare_date = d.get("compare_date", "")
    acct = d.get("account_name", "Golf in the Cosmos")

    spent_anything = bool(t.get("spend"))
    if spent_anything:
        body_top = _totals_grid(t, p, cur)
        sub = f"Daily performance · {escape(report_date)}"
        if compare_date:
            sub += f" &nbsp;·&nbsp; deltas vs {escape(compare_date)}"
    else:
        body_top = (
            f'<div style="background:#fffaf0;border:1px solid {GOLD};border-radius:10px;'
            f'padding:18px 20px;font:400 14px Arial,sans-serif;color:{INK}">'
            f'<b>No spend recorded for {escape(report_date)}.</b><br>'
            f'The account is active but no ads delivered on this date. This report will '
            f'fill in automatically once the campaign starts spending.</div>'
        )
        sub = f"Daily performance · {escape(report_date)}"

    campaigns_html = _campaign_table(d.get("campaigns") or [], cur)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6">
<tr><td align="center" style="padding:24px 12px">
  <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)">
    <tr><td style="background:linear-gradient(135deg,{NAVY},{NAVY2});padding:26px 28px">
      <div style="font:700 12px Arial,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:{GOLD}">Golf in the Cosmos · Ad Report</div>
      <div style="font:700 24px Arial,sans-serif;color:#ffffff;margin-top:6px">{escape(acct)}</div>
      <div style="font:400 13px Arial,sans-serif;color:#c7cce0;margin-top:4px">{sub}</div>
    </td></tr>
    <tr><td style="height:3px;background:{GOLD}"></td></tr>
    <tr><td style="padding:22px 22px 28px">
      {body_top}
      {campaigns_html}
      <div style="margin-top:26px;padding-top:16px;border-top:1px solid {LINE};font:400 12px Arial,sans-serif;color:{MUTE}">
        Numbers pulled from the Meta Ads API. Report-only — no budgets or ads were changed.
        Source of truth is Meta Ads Manager; small modeled/attribution lags are normal for the most recent day.
      </div>
    </td></tr>
  </table>
</td></tr></table>
</body></html>"""


# ------------------------------- text summary --------------------------------

def render_text(d):
    cur = d.get("currency", "USD")
    sym = "$" if cur == "USD" else ""
    t = d.get("totals", {}) or {}
    p = d.get("totals_prev", {}) or {}
    lines = [f"Golf in the Cosmos — Ad Report ({d.get('report_date','')})"]
    if not t.get("spend"):
        lines.append("No spend recorded for this date (account active, ads not delivering).")
        return "\n".join(lines)

    def dl(c, pr, **kw):
        txt, _ = _delta(c, pr, **kw)
        return f" ({txt})" if txt else ""

    lines.append(f"Spend:       {_money(t.get('spend'), sym)}{dl(t.get('spend'), p.get('spend'), money=True)}")
    lines.append(f"Reach:       {_int(t.get('reach'))}{dl(t.get('reach'), p.get('reach'))}")
    lines.append(f"Impressions: {_int(t.get('impressions'))}{dl(t.get('impressions'), p.get('impressions'))}")
    lines.append(f"CTR:         {_pct(t.get('ctr'))}{dl(t.get('ctr'), p.get('ctr'), pct=True)}")
    lines.append(f"CPC:         {_money(t.get('cpc'), sym)}{dl(t.get('cpc'), p.get('cpc'), good_is_up=False, money=True)}")
    lines.append(f"Conversions: {_int(t.get('conversions'))}{dl(t.get('conversions'), p.get('conversions'))}")
    if t.get("roas") is not None:
        lines.append(f"ROAS:        {_roas(t.get('roas'))}")
    return "\n".join(lines)


# ----------------------------------- main ------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Render the daily Meta ad report.")
    ap.add_argument("--data", required=True, help="Path to the metrics JSON file.")
    ap.add_argument("--out", help="Output HTML path (default out/ad_report_{date}.html).")
    ap.add_argument("--open", action="store_true", help="Open the HTML when done (macOS).")
    args = ap.parse_args()

    data = json.loads(Path(args.data).read_text())
    OUT_DIR.mkdir(exist_ok=True)
    date_tag = (data.get("report_date") or "latest").replace("/", "-")
    out_path = Path(args.out) if args.out else OUT_DIR / f"ad_report_{date_tag}.html"
    out_path.write_text(render_html(data))

    text = render_text(data)
    print(text)
    print(f"\n[written] {out_path}")

    if args.open:
        import subprocess
        subprocess.run(["open", str(out_path)], check=False)


if __name__ == "__main__":
    main()
