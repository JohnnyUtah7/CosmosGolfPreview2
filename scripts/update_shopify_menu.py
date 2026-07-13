#!/usr/bin/env python3
"""
Point the weekly-preview navigation menu item at a new tournament page.

Shopify menus are GraphQL-only. The target item is found via
data/shopify_menu_config.json:
    {
      "menu_handle": "main-menu",
      "item_title": "Weekly Preview",          // exact label match (primary)
      "url_pattern": "^/pages/\\d{4}-"          // fallback: single URL match
    }

menuUpdate REPLACES the full items tree, so this script fetches the menu,
copies every item verbatim, and swaps only the target item's destination.

Requires custom-app scopes: read_online_store_navigation + write_online_store_navigation
(and read_content to resolve the page GID).

Usage:
    python3 scripts/update_shopify_menu.py --list                 # discover menus/items
    python3 scripts/update_shopify_menu.py --handle 2026-the-open-championship --dry-run
    python3 scripts/update_shopify_menu.py --handle 2026-the-open-championship
    python3 scripts/update_shopify_menu.py --handle 2026-the-open-championship --verify
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("❌ Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "data" / "shopify_menu_config.json"
API_VERSION = "2024-07"

ITEM_FIELDS = "id title type url resourceId"
MENUS_QUERY = f"""
query {{
  menus(first: 20) {{
    nodes {{
      id handle title
      items {{
        {ITEM_FIELDS}
        items {{
          {ITEM_FIELDS}
          items {{ {ITEM_FIELDS} }}
        }}
      }}
    }}
  }}
}}
"""

MENU_UPDATE = """
mutation menuUpdate($id: ID!, $title: String!, $items: [MenuItemUpdateInput!]!) {
  menuUpdate(id: $id, title: $title, items: $items) {
    menu { id handle }
    userErrors { field message }
  }
}
"""

PAGE_BY_HANDLE = """
query pageByHandle($query: String!) {
  pages(first: 1, query: $query) {
    nodes { id title handle }
  }
}
"""

# Menu item types that reference a Shopify resource via resourceId
RESOURCE_TYPES = {"PAGE", "COLLECTION", "PRODUCT", "BLOG", "ARTICLE", "CATALOG",
                  "CUSTOMER_ACCOUNT_PAGE", "METAOBJECT", "SHOP_POLICY"}


class MenuClient:
    def __init__(self):
        store_url = (os.getenv("SHOPIFY_STORE_URL") or "").replace("https://", "").replace("http://", "")
        token = os.getenv("SHOPIFY_ACCESS_TOKEN") or ""
        if not store_url or not token:
            print("❌ Error: set SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN (in .env)")
            sys.exit(1)
        self.endpoint = f"https://{store_url}/admin/api/{API_VERSION}/graphql.json"
        self.headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        self.client = httpx.Client(timeout=30.0)

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        resp = self.client.post(self.endpoint, headers=self.headers,
                                json={"query": query, "variables": variables or {}})
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("errors"):
            msgs = json.dumps(payload["errors"], indent=2)
            if "ACCESS_DENIED" in msgs or "access" in msgs.lower():
                print("❌ GraphQL access denied — add read/write_online_store_navigation "
                      "scopes to the custom app (Shopify admin → Settings → Apps and "
                      "sales channels → Develop apps → your app → Configuration).")
            raise RuntimeError(f"GraphQL errors: {msgs}")
        return payload["data"]

    def get_menus(self) -> list[dict]:
        return self.graphql(MENUS_QUERY)["menus"]["nodes"]

    def get_page_gid(self, handle: str) -> str | None:
        nodes = self.graphql(PAGE_BY_HANDLE, {"query": f"handle:{handle}"})["pages"]["nodes"]
        # The query filter can fuzzy-match; require the exact handle.
        for n in nodes:
            if n["handle"] == handle:
                return n["id"]
        return None


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"❌ Error: {CONFIG_PATH} not found. Run with --list first, then create it, e.g.:")
        print(json.dumps({"menu_handle": "main-menu", "item_title": "Weekly Preview",
                          "url_pattern": "^/pages/\\d{4}-"}, indent=2))
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text())


def walk_items(items: list[dict]):
    for item in items:
        yield item
        yield from walk_items(item.get("items") or [])


def find_target(menu: dict, config: dict) -> dict | None:
    """Find the menu item to repoint: exact title match first, then single url-pattern match."""
    title = (config.get("item_title") or "").strip().lower()
    if title:
        matches = [i for i in walk_items(menu["items"]) if (i.get("title") or "").strip().lower() == title]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            print(f"❌ Error: {len(matches)} menu items share the title '{config['item_title']}'")
            return None
    pattern = config.get("url_pattern")
    if pattern:
        rx = re.compile(pattern)
        matches = [i for i in walk_items(menu["items"]) if rx.search(i.get("url") or "")]
        if len(matches) == 1:
            return matches[0]
        print(f"❌ Error: url_pattern '{pattern}' matched {len(matches)} items (need exactly 1)")
    return None


def to_update_input(item: dict, target_id: str, new_page_gid: str, new_url: str) -> dict:
    """Deep-copy a menu item into MenuItemUpdateInput shape, swapping only the target's destination."""
    node = {"id": item["id"], "title": item["title"], "type": item["type"]}
    if item["id"] == target_id:
        if item["type"] == "PAGE":
            node["resourceId"] = new_page_gid
        elif item["type"] in RESOURCE_TYPES:
            # Item currently points at a non-page resource; repoint as PAGE.
            node["type"] = "PAGE"
            node["resourceId"] = new_page_gid
        else:  # HTTP / FRONTPAGE etc. → plain URL swap
            node["type"] = "HTTP"
            node["url"] = new_url
    else:
        if item["type"] in RESOURCE_TYPES and item.get("resourceId"):
            node["resourceId"] = item["resourceId"]
        elif item.get("url") and item["type"] not in ("FRONTPAGE",):
            node["url"] = item["url"]
    children = item.get("items") or []
    if children:
        node["items"] = [to_update_input(c, target_id, new_page_gid, new_url) for c in children]
    return node


def print_menu(menu: dict, indent: int = 0) -> None:
    for item in menu["items"] if indent == 0 else menu:
        pad = "  " * (indent + 1)
        print(f"{pad}- [{item['type']}] '{item['title']}' -> {item.get('url') or item.get('resourceId') or ''}")
        if item.get("items"):
            print_menu(item["items"], indent + 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Swap the weekly-preview nav menu item to a new page")
    parser.add_argument("--handle", help="Target page handle, e.g. 2026-the-open-championship")
    parser.add_argument("--list", action="store_true", help="List all menus and items (discovery)")
    parser.add_argument("--dry-run", action="store_true", help="Show planned change without mutating")
    parser.add_argument("--verify", action="store_true", help="Exit 0 iff the item already points at --handle")
    parser.add_argument("--item-label", default=None, help="Optionally rename the menu item label")
    args = parser.parse_args()

    api = MenuClient()

    if args.list:
        for menu in api.get_menus():
            print(f"\nMenu: '{menu['title']}' (handle={menu['handle']}, id={menu['id']})")
            print_menu(menu)
        return 0

    if not args.handle:
        print("❌ Error: --handle is required (or use --list)")
        return 1

    config = load_config()
    menus = api.get_menus()
    menu = next((m for m in menus if m["handle"] == config.get("menu_handle")), None)
    if not menu:
        print(f"❌ Error: menu handle '{config.get('menu_handle')}' not found. "
              f"Available: {[m['handle'] for m in menus]}")
        return 1

    target = find_target(menu, config)
    if not target:
        return 1

    new_url = f"/pages/{args.handle}"

    if args.verify:
        current = target.get("url") or ""
        if current.rstrip("/").endswith(new_url):
            print(f"✅ Verified: '{target['title']}' points at {new_url}")
            return 0
        print(f"❌ Verify failed: '{target['title']}' points at '{current}', expected {new_url}")
        return 1

    page_gid = api.get_page_gid(args.handle)
    if not page_gid and target["type"] in RESOURCE_TYPES:
        print(f"❌ Error: no Shopify page found with handle '{args.handle}' — deploy the page first")
        return 1

    print(f"Menu: '{menu['title']}' ({menu['handle']})")
    print(f"Target item: [{target['type']}] '{target['title']}' -> {target.get('url') or target.get('resourceId')}")
    print(f"New destination: {new_url}" + (f" (page {page_gid})" if page_gid else ""))

    if args.dry_run:
        print("\n[DRY RUN] No changes made.")
        return 0

    items_input = [to_update_input(i, target["id"], page_gid, new_url) for i in menu["items"]]
    if args.item_label:
        for node in walk_items(items_input):
            if node["id"] == target["id"]:
                node["title"] = args.item_label

    data = api.graphql(MENU_UPDATE, {"id": menu["id"], "title": menu["title"], "items": items_input})
    errors = data["menuUpdate"]["userErrors"]
    if errors:
        print(f"❌ menuUpdate userErrors: {errors}")
        return 1

    print(f"✅ Menu updated: '{target['title']}' now points at {new_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
