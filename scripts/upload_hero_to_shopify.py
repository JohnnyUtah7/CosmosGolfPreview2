#!/usr/bin/env python3
"""
Upload a course hero image to Shopify Files (CDN) and optionally register it
in data/course_hero_images.json so the HTML/email generators pick it up.

Flow: stagedUploadsCreate -> POST file to staged target -> fileCreate ->
poll until the CDN URL is ready -> print URL.

Requires the custom app to have the `write_files` (and `read_files`) scope.

Usage:
    python3 scripts/upload_hero_to_shopify.py --image /path/to/royal_birkdale.jpg \
        --alt "Royal Birkdale Golf Club" \
        --add-mapping "open championship,royal birkdale,british open"

    # upload only, no mapping
    python3 scripts/upload_hero_to_shopify.py --image hero.jpg
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
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
HERO_IMAGES_PATH = PROJECT_ROOT / "data" / "course_hero_images.json"
API_VERSION = "2024-07"


def graphql(client: httpx.Client, store_url: str, token: str, query: str, variables: dict) -> dict:
    resp = client.post(
        f"https://{store_url}/admin/api/{API_VERSION}/graphql.json",
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
        json={"query": query, "variables": variables},
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("errors"):
        raise RuntimeError(f"GraphQL errors: {json.dumps(payload['errors'], indent=2)}")
    return payload["data"]


STAGED_UPLOADS_CREATE = """
mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets { url resourceUrl parameters { name value } }
    userErrors { field message }
  }
}
"""

FILE_CREATE = """
mutation fileCreate($files: [FileCreateInput!]!) {
  fileCreate(files: $files) {
    files { id fileStatus }
    userErrors { field message }
  }
}
"""

FILE_STATUS = """
query fileStatus($id: ID!) {
  node(id: $id) {
    ... on MediaImage {
      fileStatus
      image { url }
    }
  }
}
"""


def upload_image(image_path: Path, alt: str, store_url: str, token: str) -> str:
    """Upload an image to Shopify Files; return the CDN URL."""
    mime = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    size = image_path.stat().st_size

    with httpx.Client(timeout=60.0) as client:
        # 1. Staged upload target
        data = graphql(client, store_url, token, STAGED_UPLOADS_CREATE, {
            "input": [{
                "filename": image_path.name,
                "mimeType": mime,
                "fileSize": str(size),
                "httpMethod": "POST",
                "resource": "FILE",
            }]
        })
        result = data["stagedUploadsCreate"]
        if result["userErrors"]:
            raise RuntimeError(f"stagedUploadsCreate errors: {result['userErrors']}")
        target = result["stagedTargets"][0]

        # 2. POST the file to the staged target (parameter order matters: file last)
        form = [(p["name"], p["value"]) for p in target["parameters"]]
        upload_resp = client.post(
            target["url"],
            data=dict(form),
            files={"file": (image_path.name, image_path.read_bytes(), mime)},
        )
        if upload_resp.status_code not in (200, 201, 204):
            raise RuntimeError(f"Staged upload failed: {upload_resp.status_code} {upload_resp.text[:500]}")

        # 3. Register the file in Shopify Files
        data = graphql(client, store_url, token, FILE_CREATE, {
            "files": [{
                "originalSource": target["resourceUrl"],
                "contentType": "IMAGE",
                "alt": alt,
            }]
        })
        result = data["fileCreate"]
        if result["userErrors"]:
            raise RuntimeError(f"fileCreate errors: {result['userErrors']}")
        file_id = result["files"][0]["id"]

        # 4. Poll until the CDN URL is ready
        for attempt in range(30):
            time.sleep(2)
            data = graphql(client, store_url, token, FILE_STATUS, {"id": file_id})
            node = data.get("node") or {}
            status = node.get("fileStatus")
            if status == "READY" and node.get("image", {}).get("url"):
                return node["image"]["url"]
            if status == "FAILED":
                raise RuntimeError("Shopify reported file processing FAILED")
        raise RuntimeError("Timed out waiting for Shopify CDN URL (60s)")


def add_mapping(keywords: list[str], url: str) -> None:
    data = json.loads(HERO_IMAGES_PATH.read_text())
    # Replace an existing entry that shares any keyword, else append.
    for entry in data["entries"]:
        if set(k.lower() for k in entry.get("keywords", [])) & set(k.lower() for k in keywords):
            entry["keywords"] = keywords
            entry["url"] = url
            break
    else:
        data["entries"].append({"keywords": keywords, "url": url})
    HERO_IMAGES_PATH.write_text(json.dumps(data, indent=2) + "\n")
    print(f"[OK] Mapping saved to {HERO_IMAGES_PATH.name}: {keywords} -> {url}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload a hero image to Shopify Files (CDN)")
    parser.add_argument("--image", type=Path, required=True, help="Local image file to upload")
    parser.add_argument("--alt", default="", help="Alt text (course name)")
    parser.add_argument("--add-mapping", default=None,
                        help="Comma-separated tournament-name keywords to register in course_hero_images.json")
    parser.add_argument("--set-default", action="store_true",
                        help="Set the uploaded image as the default fallback hero")
    args = parser.parse_args()

    store_url = (os.getenv("SHOPIFY_STORE_URL") or "").replace("https://", "").replace("http://", "")
    token = os.getenv("SHOPIFY_ACCESS_TOKEN") or ""
    if not store_url or not token:
        print("❌ Error: set SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN (in .env)")
        return 1
    if not args.image.exists():
        print(f"❌ Error: image not found: {args.image}")
        return 1

    print(f"📤 Uploading {args.image.name} ({args.image.stat().st_size // 1024} KB) to Shopify Files...")
    try:
        url = upload_image(args.image, args.alt, store_url, token)
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return 1

    print(f"✅ CDN URL: {url}")

    if args.add_mapping:
        keywords = [k.strip().lower() for k in args.add_mapping.split(",") if k.strip()]
        add_mapping(keywords, url)
    if args.set_default:
        data = json.loads(HERO_IMAGES_PATH.read_text())
        data["default"] = url
        HERO_IMAGES_PATH.write_text(json.dumps(data, indent=2) + "\n")
        print("[OK] Set as default fallback hero")

    return 0


if __name__ == "__main__":
    sys.exit(main())
