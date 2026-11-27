#!/usr/bin/env python3
"""Serve the public site under its actual GitHub Pages URL prefix."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
import mimetypes

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "/uni-lecture-tutor-website/"
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        status = 200
        if not path.startswith(PREFIX):
            status = 404
        name = path[len(PREFIX):] if status == 200 else "404.html"
        if not name or name.endswith("/"):
            name += "index.html"
        parts = Path(name).parts
        candidate = ROOT / name
        allowed = (len(parts) == 1 and (name.endswith(".html") or name in ("style.css", "site.js", "robots.txt", "sitemap.xml"))) or (len(parts) == 2 and parts[0] in ("de", "ar") and name.endswith(".html")) or (len(parts) == 2 and parts[0] == "assets" and name.endswith(".png"))
        if not allowed or not candidate.is_file() or ".." in parts:
            candidate, status = ROOT / "404.html", 404
        body = candidate.read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", mimetypes.guess_type(str(candidate))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 4173), Handler).serve_forever()
