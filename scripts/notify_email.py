#!/usr/bin/env python3
"""
Send the weekly review/status email directly through Gmail (free — no Zapier).

Auth: a Google "app password" for the sender account, stored in .env:
    GMAIL_SENDER=realchrismiller@gmail.com
    GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   (Google Account → Security →
                                              2-Step Verification → App passwords)
    NOTIFY_RECIPIENTS=realchrismiller@gmail.com,reefpointcap@gmail.com

Falls back to a Zapier Catch-Hook webhook (ZAPIER_NOTIFY_WEBHOOK_URL) if the
Gmail password is not set — otherwise prints a warning and exits 1.

Usage:
    python3 scripts/notify_email.py --subject "..." --body "plain text" \
        --newsletter-file the_open_championship_2026_email.html
"""

from __future__ import annotations

import argparse
import html
import os
import re
import smtplib
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEFAULT_RECIPIENTS = "realchrismiller@gmail.com,reefpointcap@gmail.com"


def strip_liquid(html_src: str) -> str:
    """Remove Shopify Email Liquid tags ({{ unsubscribe_link }} etc.) for the
    review-copy render in a normal inbox."""
    html_src = re.sub(r"<a[^>]*\{\{\s*unsubscribe_link\s*\}\}[^>]*>(.*?)</a>", r"\1", html_src, flags=re.DOTALL)
    return re.sub(r"\{\{[^}]*\}\}", "", html_src)


def build_body(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if args.body_html_file and args.body_html_file.exists():
        parts.append(args.body_html_file.read_text())
    if args.body:
        parts.append(f"<pre style=\"font-family:monospace;font-size:13px\">{html.escape(args.body)}</pre>")
    if args.newsletter_file and args.newsletter_file.exists():
        parts.append("<hr><h3>📧 Newsletter preview (this is the review/test copy — "
                     "the real send is from Shopify Email)</h3>")
        parts.append(strip_liquid(args.newsletter_file.read_text()))
    return "\n".join(parts) or "<p>(no body)</p>"


def send_gmail(subject: str, body_html: str, sender: str, password: str, recipients: list[str]) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Cosmos Golf Bot <{sender}>"
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body_html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as server:
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())


def send_zapier(subject: str, body_html: str, webhook: str) -> bool:
    import httpx
    resp = httpx.post(webhook, json={"subject": subject, "body_html": body_html}, timeout=30.0)
    return resp.status_code in (200, 201)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send review/status email (Gmail app password)")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body", default=None, help="Plain-text body (rendered as <pre>)")
    parser.add_argument("--body-html-file", type=Path, default=None, help="HTML body file")
    parser.add_argument("--newsletter-file", type=Path, default=None,
                        help="Newsletter HTML to append inline as the review/test copy")
    args = parser.parse_args()

    body_html = build_body(args)

    sender = os.getenv("GMAIL_SENDER", "realchrismiller@gmail.com")
    password = (os.getenv("GMAIL_APP_PASSWORD") or "").replace(" ", "")
    recipients = [r.strip() for r in os.getenv("NOTIFY_RECIPIENTS", DEFAULT_RECIPIENTS).split(",") if r.strip()]

    if password:
        try:
            send_gmail(args.subject, body_html, sender, password, recipients)
            print(f"✅ Review email sent via Gmail to {', '.join(recipients)}: {args.subject}")
            return 0
        except Exception as e:
            print(f"❌ Gmail send failed: {e}")
            # fall through to webhook if configured

    webhook = os.getenv("ZAPIER_NOTIFY_WEBHOOK_URL", "")
    if webhook:
        if send_zapier(args.subject, body_html, webhook):
            print(f"✅ Notification sent via Zapier webhook: {args.subject}")
            return 0
        print("❌ Zapier webhook failed")
        return 1

    if not password:
        print("⚠️  GMAIL_APP_PASSWORD not set in .env — skipping email notification")
        print("   (Google Account → Security → 2-Step Verification → App passwords)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
