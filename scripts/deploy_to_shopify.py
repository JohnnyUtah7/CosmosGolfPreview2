#!/usr/bin/env python3
"""
Deploy HTML preview to Shopify page.

Uploads the generated HTML to a Shopify page (Custom HTML section) via Admin API.

Usage:
  1. Generate: python scripts/generate_tournament_html.py --tournament "WM Phoenix Open" --year 2026 --shopify
  2. Deploy:   python scripts/deploy_to_shopify.py --html wm_phoenix_open_2026_shopify.html --page-handle weekly-preview

  Or copy the contents of wm_phoenix_open_2026_shopify.html into your Shopify page (Custom HTML) by hand.
"""
from __future__ import annotations

import sys
import json
import os
import argparse
from pathlib import Path
from datetime import datetime

try:
    import httpx
except ImportError:
    print("❌ Error: httpx not installed")
    print("Run: pip install httpx")
    sys.exit(1)


class ShopifyClient:
    """Client for Shopify Admin API."""

    def __init__(self, store_url: str, access_token: str):
        """
        Initialize Shopify client.

        Args:
            store_url: Your Shopify store URL (e.g., 'cosmos-golf.myshopify.com')
            access_token: Admin API access token
        """
        self.store_url = store_url.replace('https://', '').replace('http://', '')
        self.access_token = access_token
        self.base_url = f"https://{self.store_url}/admin/api/2024-01"

        self.headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }

        self.client = httpx.Client(timeout=30.0)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.client.close()

    def get_page_by_handle(self, handle: str) -> dict | None:
        """
        Get a page by its handle.

        Args:
            handle: Page handle (URL slug)

        Returns:
            Page object or None if not found
        """
        url = f"{self.base_url}/pages.json"
        params = {"handle": handle}

        response = self.client.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        pages = response.json().get("pages", [])
        return pages[0] if pages else None

    def create_page(self, title: str, handle: str, body_html: str) -> dict:
        """
        Create a new Shopify page.

        Args:
            title: Page title
            handle: URL handle (slug)
            body_html: HTML content

        Returns:
            Created page object
        """
        url = f"{self.base_url}/pages.json"

        data = {
            "page": {
                "title": title,
                "handle": handle,
                "body_html": body_html,
                "published": True
            }
        }

        response = self.client.post(url, headers=self.headers, json=data)
        response.raise_for_status()

        return response.json()["page"]

    def update_page(self, page_id: int, body_html: str, title: str | None = None) -> dict:
        """
        Update an existing Shopify page.

        Args:
            page_id: Shopify page ID
            body_html: New HTML content
            title: New title (optional)

        Returns:
            Updated page object
        """
        url = f"{self.base_url}/pages/{page_id}.json"

        data = {"page": {"body_html": body_html}}
        if title:
            data["page"]["title"] = title

        response = self.client.put(url, headers=self.headers, json=data)
        response.raise_for_status()

        return response.json()["page"]

    def create_or_update_page(self, title: str, handle: str, body_html: str) -> dict:
        """
        Create a new page or update existing one.

        Args:
            title: Page title
            handle: URL handle
            body_html: HTML content

        Returns:
            Page object (created or updated)
        """
        existing_page = self.get_page_by_handle(handle)

        if existing_page:
            print(f"📝 Updating existing page: {existing_page['title']}")
            return self.update_page(existing_page["id"], body_html, title)
        else:
            print(f"✨ Creating new page: {title}")
            return self.create_page(title, handle, body_html)

    def close(self):
        """Close HTTP client."""
        self.client.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy HTML preview to Shopify page"
    )
    parser.add_argument(
        "--html",
        type=Path,
        required=True,
        help="Path to HTML file to upload (use *_shopify.html for Shopify — stays under 64KB page limit)"
    )
    parser.add_argument(
        "--page-handle",
        type=str,
        default="weekly-pga-preview",
        help="Shopify page handle/slug (default: weekly-pga-preview)"
    )
    parser.add_argument(
        "--page-title",
        type=str,
        help="Page title (default: auto-generated from date)"
    )
    parser.add_argument(
        "--store-url",
        type=str,
        help="Shopify store URL (or set SHOPIFY_STORE_URL env var)"
    )
    parser.add_argument(
        "--access-token",
        type=str,
        help="Shopify access token (or set SHOPIFY_ACCESS_TOKEN env var)"
    )

    args = parser.parse_args()

    print("🛍️  Shopify Deployment Tool")
    print("=" * 60)

    # Get credentials
    store_url = args.store_url or os.getenv("SHOPIFY_STORE_URL")
    access_token = args.access_token or os.getenv("SHOPIFY_ACCESS_TOKEN")

    if not store_url or not access_token:
        print("❌ Error: Shopify credentials required")
        print("")
        print("Provide via arguments or environment variables:")
        print("  --store-url YOUR_STORE.myshopify.com")
        print("  --access-token YOUR_ACCESS_TOKEN")
        print("")
        print("Or set environment variables:")
        print("  export SHOPIFY_STORE_URL=YOUR_STORE.myshopify.com")
        print("  export SHOPIFY_ACCESS_TOKEN=YOUR_ACCESS_TOKEN")
        return 1

    # Read HTML file
    if not args.html.exists():
        print(f"❌ Error: HTML file not found: {args.html}")
        return 1

    with open(args.html, 'r') as f:
        html_content = f.read()

    print(f"📄 Loaded HTML file: {args.html} ({len(html_content)} bytes)")

    # Generate title if not provided
    page_title = args.page_title
    if not page_title:
        date_str = datetime.now().strftime("%B %d, %Y")
        page_title = f"Weekly PGA Preview - {date_str}"

    # Deploy to Shopify
    try:
        with ShopifyClient(store_url, access_token) as shopify:
            print(f"\n🔗 Connecting to Shopify: {store_url}")

            page = shopify.create_or_update_page(
                title=page_title,
                handle=args.page_handle,
                body_html=html_content
            )

            print("\n✅ Deployment successful!")
            print(f"   Page ID: {page['id']}")
            print(f"   Title: {page['title']}")
            print(f"   Handle: {page['handle']}")
            print(f"   URL: https://{store_url.replace('.myshopify.com', '')}.com/pages/{page['handle']}")
            print(f"   Updated: {page['updated_at']}")

            return 0

    except httpx.HTTPStatusError as e:
        print(f"\n❌ Shopify API error: {e.response.status_code}")
        print(f"   {e.response.text}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
