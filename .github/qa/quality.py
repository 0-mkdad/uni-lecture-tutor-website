#!/usr/bin/env python3
"""Offline public-site checks. No external requests or dependencies."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://0-mkdad.github.io/uni-lecture-tutor-website/"
PREFIX = urlsplit(BASE).path
LANGS = ("en", "de", "ar")
PAGES = ("index.html", "getting-started.html", "learning-science.html", "privacy.html", "terms.html", "support.html", "legal.html")
VOID = set("area base br col embed hr img input link meta param source track wbr".split())
ERRORS, COUNTS = [], Counter()

def check(condition, message):
    if not condition:
        ERRORS.append(message)

def relpath(lang, page):
    return ("" if lang == "en" else lang + "/") + page

def canonical(lang, page):
    return BASE + relpath(lang, "" if page == "index.html" else page)

class Page(HTMLParser):
    def __init__(self, path, source):
        super().__init__(convert_charrefs=True)
        self.path, self.source = path, source
        self.ids, self.tags, self.stack, self.refs = [], [], [], []
        self.meta, self.alternate, self.headings = {}, {}, []
        self.canonical, self.title, self.html = "", "", {}
        self.in_title, self.ld_buffer = False, None
        self.feed(source)
        self.close()
        check(not self.stack, f"{path}: unclosed elements {self.stack}")

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.tags.append((tag, values))
        check(len(values) == len(attrs), f"{self.path}: duplicate attribute in {tag}")
        if tag not in VOID:
            self.stack.append(tag)
        if tag == "html":
            self.html = values
        if tag == "title":
            self.in_title = True
        if tag == "script" and values.get("type") == "application/ld+json":
            self.ld_buffer = ""
        if tag == "meta":
            key = values.get("name") or values.get("property")
            if key and key != "og:locale:alternate":
                check(key not in self.meta, f"{self.path}: duplicate metadata {key}")
                self.meta[key] = values.get("content", "")
        if tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href", "")
        if tag == "link" and values.get("rel") == "alternate":
            lang = values.get("hreflang")
            check(lang not in self.alternate, f"{self.path}: duplicate hreflang {lang}")
            self.alternate[lang] = values.get("href")
        if "id" in values:
            self.ids.append(values["id"])
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        for key in ("href", "src"):
            if values.get(key):
                self.refs.append((tag, key, values[key], values))
        for key in values:
            check(not key.startswith("on"), f"{self.path}: inline handler {key}")
        check(tag not in ("iframe", "embed", "object"), f"{self.path}: unexpected embedded content")
        if tag == "img":
            check("alt" in values, f"{self.path}: missing image alt attribute")
        if tag == "form":
            check(not values.get("action"), f"{self.path}: form must not send data externally")
        if tag == "input":
            check(values.get("type") != "file", f"{self.path}: website must not upload lecture files")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "script" and self.ld_buffer is not None:
            try:
                json.loads(self.ld_buffer)
            except ValueError as exc:
                ERRORS.append(f"{self.path}: invalid JSON-LD: {exc}")
            self.ld_buffer = None
        if tag in VOID:
            ERRORS.append(f"{self.path}: invalid closing tag {tag}")
        elif not self.stack or self.stack[-1] != tag:
            ERRORS.append(f"{self.path}: mismatched closing tag {tag}; stack {self.stack[-4:]}")
        else:
            self.stack.pop()

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.ld_buffer is not None:
            self.ld_buffer += data

    def class_count(self, cls):
        return sum(cls in attrs.get("class", "").split() for _, attrs in self.tags)

def to_path(url):
    u = urlsplit(url)
    if u.netloc != urlsplit(BASE).netloc or not u.path.startswith(PREFIX):
        return None
    target = unquote(u.path[len(PREFIX):])
    return target + "index.html" if not target or target.endswith("/") else target

def run():
    expected = {relpath(l, p) for l in LANGS for p in PAGES}
    actual = {p.relative_to(ROOT).as_posix() for folder in (ROOT, ROOT / "de", ROOT / "ar") for p in folder.glob("*.html")}
    check(actual == expected | {"404.html"}, f"HTML page set differs: {sorted(actual ^ (expected | {'404.html'}))}")
    parsed = {}
    for path in sorted(actual):
        source = (ROOT / path).read_text(encoding="utf-8")
        page = parsed[path] = Page(path, source)
        COUNTS["pages"] += 1
        check(source.lower().startswith("<!doctype html>"), f"{path}: missing HTML5 doctype")
        check(len(page.ids) == len(set(page.ids)), f"{path}: duplicate ids")
        check(page.headings.count(1) == 1 and page.headings[:1] == [1], f"{path}: invalid H1")
        for a, b in zip(page.headings, page.headings[1:]):
            check(b <= a + 1, f"{path}: skipped heading H{a} to H{b}")
        check(bool(page.title.strip()), f"{path}: missing title")
        check("&#x20;" not in source.lower(), f"{path}: visible editor entity")
        if path == "404.html":
            check("noindex" in page.meta.get("robots", ""), "404 should be excluded from indexing")
            continue
        lang = path.split("/")[0] if "/" in path else "en"
        filename = Path(path).name
        check(page.html.get("lang") == lang, f"{path}: lang mismatch")
        check(page.html.get("dir") == ("rtl" if lang == "ar" else "ltr"), f"{path}: dir mismatch")
        check(page.canonical == canonical(lang, filename), f"{path}: canonical mismatch")
        alt = {l: canonical(l, filename) for l in LANGS}
        alt["x-default"] = canonical("en", filename)
        check(page.alternate == alt, f"{path}: hreflang mismatch")
        for key in ("description", "og:title", "og:description", "og:url", "og:image", "twitter:card", "twitter:title", "twitter:description", "twitter:image"):
            check(bool(page.meta.get(key)), f"{path}: missing {key}")
        check(page.meta.get("og:url") == page.canonical, f"{path}: og:url mismatch")
        check(page.meta.get("og:image") == BASE + "assets/social-preview.png", f"{path}: social image mismatch")
        check(page.meta.get("og:image:width") == "1200" and page.meta.get("og:image:height") == "630", f"{path}: social image dimensions")
        check(page.meta.get("twitter:card") == "summary_large_image", f"{path}: social card type")
        if filename == "index.html":
            check(page.class_count("discipline-icon") == 24, f"{path}: expected 24 profiles")
            check(page.class_count("demo-extras") == 1, f"{path}: missing demo overview")
            for anchor in ("study-modes", "languages-learning", "source-integrity", "learning-progress", "exports"):
                check(anchor in page.ids, f"{path}: missing capability section {anchor}")
            check(page.class_count("export-card") == 8, f"{path}: expected eight export types")
            check(page.class_count("provenance-card") == 5, f"{path}: expected five provenance labels")
            check(page.class_count("discipline-text") == 24, f"{path}: expected 24 discipline explanations")
            check(page.class_count("language-example") == 1, f"{path}: missing multilingual example")
            check("1.1.0" in source, f"{path}: missing development version")
            check("past-exams" in page.ids, f"{path}: missing past-exam section")
            check(page.class_count("exam-step") == 4, f"{path}: missing guided exam demo")
            check(page.class_count("exam-modes") == 1, f"{path}: missing exam study modes")
            COUNTS["profiles"] += page.class_count("discipline-icon")
        if filename == "privacy.html":
            check("public-research" in page.ids, f"{path}: missing public research notice")
        if filename == "learning-science.html":
            check(page.class_count("upgrade-card") == 11, f"{path}: expected 11 strategies")
            COUNTS["strategies"] += page.class_count("upgrade-card")
        if filename == "getting-started.html":
            check(page.class_count("guide-steps") == 1, f"{path}: missing guide")
            check(sum(t == "blockquote" for t, _ in page.tags) == 3, f"{path}: expected three prompts")
    check(len({parsed[p].title for p in expected}) == len(expected), "duplicate page titles")
    check(len({parsed[p].meta.get("description") for p in expected}) == len(expected), "duplicate descriptions")
    for path, page in parsed.items():
        doc_url = page.canonical or BASE + path
        for tag, attr, value, attrs in page.refs:
            if value.startswith(("mailto:", "tel:")):
                continue
            resolved = urljoin(doc_url, value)
            check(urlsplit(resolved).scheme == "https", f"{path}: unsafe URL {value}")
            local = to_path(resolved)
            if local is None:
                check(not (attr == "src" or tag == "link" and attrs.get("rel") in ("stylesheet", "icon", "apple-touch-icon")), f"{path}: remote resource {value}")
                COUNTS["external_references"] += 1
                continue
            COUNTS["internal_references"] += 1
            check((ROOT / local).is_file() and ".." not in Path(local).parts, f"{path}: missing resource {value} -> {local}")
            fragment = unquote(urlsplit(resolved).fragment)
            if fragment and local in parsed:
                COUNTS["fragments"] += 1
                check(fragment in parsed[local].ids, f"{path}: missing anchor {value}")
        for _, attrs in page.tags:
            for attr in ("aria-controls", "aria-labelledby", "aria-describedby", "for"):
                for identifier in attrs.get(attr, "").split():
                    check(identifier in page.ids, f"{path}: unresolved {attr}={identifier}")
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}
    xml = ET.parse(ROOT / "sitemap.xml")
    nodes = xml.findall("s:url", ns)
    locs = [n.findtext("s:loc", namespaces=ns) for n in nodes]
    check(len(locs) == len(expected) and set(locs) == {parsed[p].canonical for p in expected}, "sitemap does not match canonical pages")
    for n in nodes:
        loc = n.findtext("s:loc", namespaces=ns)
        path = to_path(loc)
        check(path in parsed, f"sitemap: unknown page {loc}")
        if path in parsed:
            alt = {x.attrib["hreflang"]: x.attrib["href"] for x in n.findall("x:link", ns)}
            check(alt == parsed[path].alternate, f"sitemap: incorrect alternates {loc}")
    check("Sitemap: " + BASE + "sitemap.xml" in (ROOT / "robots.txt").read_text(), "robots.txt sitemap mismatch")
    image = (ROOT / "assets/social-preview.png").read_bytes()
    check(image[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", image[16:24]) == (1200, 630), "invalid social image")
    check(len(image) < 400_000, "social image size budget exceeded")
    secret = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{30,}")
    trackers = re.compile(r"googletagmanager|google-analytics|connect\.facebook\.net|hotjar|clarity\.ms|segment\.io", re.I)
    for path in sorted(actual | {"site.js", "style.css", "README.md"}):
        source = (ROOT / path).read_text(encoding="utf-8")
        check(not secret.search(source), f"{path}: possible embedded credential")
        check(not trackers.search(source), f"{path}: tracking reference")
    js = (ROOT / "site.js").read_text(encoding="utf-8")
    check(not re.search(r"\b(?:fetch|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage)\s*(?:\(|\.)|document\.cookie", js), "site.js: unexpected network or storage")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    check(not re.search(r"@import|url\(\s*['\"]?https?://", css, re.I), "style.css: unexpected external asset")
    print(json.dumps({"checks": dict(COUNTS), "errors": ERRORS}, ensure_ascii=False, indent=2))
    return bool(ERRORS)

if __name__ == "__main__":
    sys.exit(run())
