#!/usr/bin/env python3
"""Manual public link audit. A blocked or rate-limited provider is unverified."""
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
ROOT = Path(__file__).resolve().parents[2]

class Links(HTMLParser):
    urls = set()
    def handle_starttag(self, tag, attrs):
        url = dict(attrs).get("href", "")
        if tag == "a" and url.startswith("https://") and urlsplit(url).netloc != "0-mkdad.github.io":
            self.urls.add(url.split("#", 1)[0])

def audit(url):
    try:
        with urlopen(Request(url, headers={"User-Agent": "UniLectureTutor-WebsiteQA/1.0"}), timeout=12) as result:
            return ("OK" if 200 <= result.status < 400 else "UNVERIFIED", url, result.status)
    except HTTPError as e:
        return ("BROKEN" if e.code in (404, 410) else "UNVERIFIED", url, e.code)
    except (URLError, TimeoutError, OSError) as e:
        return ("UNVERIFIED", url, type(e).__name__)

if __name__ == "__main__":
    parser = Links()
    for folder in (ROOT, ROOT / "de", ROOT / "ar"):
        for path in folder.glob("*.html"):
            parser.feed(path.read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(audit, sorted(parser.urls)))
    for status, url, code in results:
        print(f"{status:10} {code} {url}")
    raise SystemExit(any(status == "BROKEN" for status, _, _ in results))
