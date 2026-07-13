#!/usr/bin/env python3
"""
Local preview server for testing HTML files.

This starts a simple HTTP server so you can view your HTML previews
in a browser before deploying to Shopify.

Usage:
    python scripts/preview_server.py [--port 8000]
"""
import sys
import argparse
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
from threading import Timer
from typing import Optional


def _pick_default_html(project_root: Path) -> Optional[str]:
    """
    Pick the "current" preview file.

    Heuristics:
    - Prefer the most recently modified HTML in project root
    - Exclude obvious non-preview helper files
    """
    exclude = set()
    html_files = [p for p in project_root.glob("*.html") if p.is_file() and p.name not in exclude]
    if not html_files:
        return None
    html_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return html_files[0].name


class PreviewHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Custom request handler that serves from project root."""

    def __init__(self, *args, default_html: Optional[str] = None, **kwargs):
        # Change to project root directory
        self._default_html = default_html
        super().__init__(*args, directory=str(Path(__file__).parent.parent), **kwargs)

    def do_GET(self):
        # Redirect root to the selected "current" preview file
        if self.path in {"/", ""} and self._default_html:
            self.send_response(302)
            self.send_header("Location", f"/{self._default_html}")
            self.end_headers()
            return
        return super().do_GET()

    def log_message(self, format, *args):
        """Custom logging to show which file was accessed."""
        message = format % args
        if '.html' in message or message.startswith('GET / '):
            print(f"📄 {message}")
        elif not any(ext in message for ext in ['.png', '.jpg', '.css', '.js', '.ico']):
            print(f"   {message}")


def open_browser(url):
    """Open browser after a short delay."""
    webbrowser.open(url)


def main():
    """Start the preview server."""
    parser = argparse.ArgumentParser(
        description="Local preview server for HTML files"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run server on (default: 8000)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't automatically open browser"
    )
    parser.add_argument(
        "--default",
        type=str,
        default=None,
        help="Default HTML file to open/redirect to (optional).",
    )

    args = parser.parse_args()

    # Check if any HTML files exist
    project_root = Path(__file__).parent.parent
    html_files = list(project_root.glob("*.html"))
    default_html = args.default or _pick_default_html(project_root)

    print("🏌️  COSMOS Golf Preview Server")
    print("=" * 60)
    print(f"📂 Serving from: {project_root}")
    print(f"🌐 Server: http://localhost:{args.port}")
    print("")

    if default_html:
        print("⭐ Recommended (current build):")
        print(f"   - http://localhost:{args.port}/{default_html}")
        print(f"   - http://localhost:{args.port}/  (redirects)")
        print("")

    if html_files:
        print("📄 Available HTML files:")
        for html_file in html_files:
            print(f"   - http://localhost:{args.port}/{html_file.name}")
    else:
        print("⚠️  No HTML files found in project root")

    # Check for previews directory
    previews_dir = project_root / "previews"
    if previews_dir.exists():
        preview_html = list(previews_dir.glob("*.html"))
        if preview_html:
            print("")
            print("📄 Preview files:")
            for html_file in preview_html:
                print(f"   - http://localhost:{args.port}/previews/{html_file.name}")

    print("")
    print("=" * 60)
    print("🔥 Server starting...")
    print("   Press Ctrl+C to stop")
    print("")

    # Start server
    try:
        def handler(*h_args, **h_kwargs):
            return PreviewHTTPRequestHandler(*h_args, default_html=default_html, **h_kwargs)

        server = HTTPServer(('localhost', args.port), handler)

        # Open browser after 1 second delay
        if not args.no_browser and default_html:
            url = f"http://localhost:{args.port}/"
            Timer(1.0, open_browser, [url]).start()

        print(f"✅ Server running at http://localhost:{args.port}")
        print("")
        server.serve_forever()

    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped")
        server.socket.close()
        return 0
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"\n❌ Error: Port {args.port} is already in use")
            print(f"   Try a different port: --port 8001")
        else:
            print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
