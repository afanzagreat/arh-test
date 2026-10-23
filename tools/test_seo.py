#!/usr/bin/env python3
"""Static SEO and localization regression tests for the twelve generated pages."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup, Doctype
if __package__:
    from .test_pointer_tracker import remove_tracker_markup, strip_tracker_css
else:
    from test_pointer_tracker import remove_tracker_markup, strip_tracker_css

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://arhdesign.tech"
LANGS = ("en", "ar", "fr", "hi")
KINDS = ("home", "works", "privacy")
OG_LOCALES = {"en": "en_US", "ar": "ar_SA", "fr": "fr_FR", "hi": "hi_IN"}
BASELINE = "812edc8"
ALLOWED_CATALOG_METADATA = {"pageTitle", "ogTitle", "twitterTitle", "ogLocale"}
FALLBACK_STYLE = "html:not(.arh-js-ready) .reveal{opacity:1;transform:none}"


def route(lang: str, kind: str) -> str:
    return ("/" if lang == "en" else f"/{lang}/") + {"home": "", "works": "works.html", "privacy": "privacy.html"}[kind]


def file_for(lang: str, kind: str) -> Path:
    p = route(lang, kind).lstrip("/")
    return ROOT / ("index.html" if not p else (p + "index.html" if p.endswith("/") else p))


def read_catalog(kind: str, ref: str | None = None) -> dict:
    name = f"{kind}-locales.js"
    if ref:
        raw = subprocess.check_output(["git", "show", f"{ref}:assets/{name}"], cwd=ROOT, text=True)
    else:
        raw = (ROOT / "assets" / name).read_text()
    return json.loads(re.search(r"=\s*({.*})\s*;", raw, re.S).group(1))


def soup(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(), "html.parser")


def compact_html(value: str) -> str:
    fragment = BeautifulSoup(value, "html.parser")
    for tag in fragment.find_all(True):
        tag.attrs = dict(sorted(tag.attrs.items()))
    return re.sub(r"\s+", " ", fragment.decode_contents()).replace("<br/>", "<br>").strip()


def local_target(value: str, current: Path) -> tuple[Path | None, str | None]:
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return None, parsed.fragment
    path = parsed.path or current.name
    if path.startswith("/"):
        target = ROOT / path.lstrip("/")
    else:
        target = (current.parent / path).resolve()
    if path.endswith("/"):
        target = target / "index.html"
    if target == ROOT:
        target = ROOT / "index.html"
    return target, parsed.fragment or None


class SEOReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = [(lang, kind, file_for(lang, kind)) for kind in KINDS for lang in LANGS]
        cls.catalogs = {kind: read_catalog(kind) for kind in KINDS}

    def test_every_page_has_exact_document_metadata(self):
        for lang, kind, path in self.pages:
            with self.subTest(page=str(path)):
                s = soup(path)
                self.assertEqual(sum(isinstance(x, Doctype) for x in s.contents), 1)
                self.assertEqual(s.html.get("lang"), lang)
                self.assertEqual(s.html.get("dir"), "rtl" if lang == "ar" else "ltr")
                strings = self.catalogs[kind][lang]
                self.assertEqual(s.title.string, strings["pageTitle"])
                desc = s.select('meta[name="description"]')
                self.assertEqual(len(desc), 1)
                self.assertEqual(desc[0].get("content"), strings["pageDescription"])
                canon = s.select('link[rel="canonical"]')
                self.assertEqual([x.get("href") for x in canon], [ORIGIN + route(lang, kind)])
                ogurl = s.select('meta[property="og:url"]')
                self.assertEqual([x.get("content") for x in ogurl], [ORIGIN + route(lang, kind)])
                self.assertEqual(s.select_one('meta[property="og:title"]')['content'], strings["pageTitle"])
                self.assertEqual(s.select_one('meta[property="og:description"]')['content'], strings["pageDescription"])
                self.assertEqual(s.select_one('meta[property="og:locale"]')['content'], OG_LOCALES[lang])

    def test_catalog_content_and_localized_attributes_are_rendered(self):
        for lang, kind, path in self.pages:
            with self.subTest(page=str(path)):
                s, strings = soup(path), self.catalogs[kind][lang]
                for el in s.select("[data-i18n]"):
                    key = el.get("data-i18n")
                    self.assertIn(key, strings)
                    self.assertEqual(compact_html(el.decode_contents()), compact_html(strings[key]))
                for attr in ("placeholder", "aria-label", "title", "content"):
                    for el in s.select(f"[data-i18n-{attr}]"):
                        key = el.get(f"data-i18n-{attr}")
                        self.assertIn(key, strings)
                        self.assertEqual(el.get(attr), strings[key])
                options = s.select("#languageSelect option")
                selected = [o.get("value") for o in options if o.has_attr("selected")]
                self.assertEqual(selected, [lang])

    def test_hreflang_is_exact_reciprocal_set(self):
        for lang, kind, path in self.pages:
            with self.subTest(page=str(path)):
                links = soup(path).select('link[rel="alternate"]')
                self.assertEqual(len(links), 5)
                actual = {x.get("hreflang"): x.get("href") for x in links}
                expected = {x: ORIGIN + route(x, kind) for x in LANGS}
                expected["x-default"] = ORIGIN + route("en", kind)
                self.assertEqual(actual, expected)

    def test_all_local_references_exist_and_fragments_resolve(self):
        for lang, kind, path in self.pages:
            s = soup(path)
            for el in s.select("[href], [src]"):
                for attr in ("href", "src"):
                    if not el.has_attr(attr):
                        continue
                    value = el[attr]
                    target, fragment = local_target(value, path)
                    if target is None:
                        continue
                    with self.subTest(page=str(path), attr=attr, value=value):
                        self.assertTrue(target.is_file(), f"missing local target: {value}")
                        if fragment:
                            target_soup = soup(target)
                            self.assertIsNotNone(target_soup.find(id=fragment), f"missing fragment #{fragment}")

    def test_sitemap_is_exactly_the_twelve_canonical_urls(self):
        root = ET.parse(ROOT / "sitemap.xml").getroot()
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [x.text for x in root.findall("sm:url/sm:loc", ns)]
        expected = [ORIGIN + route(lang, kind) for kind in KINDS for lang in LANGS]
        self.assertEqual(urls, expected)
        self.assertEqual(len(urls), 12)

    def test_jsonld_is_truthful_and_page_specific(self):
        forbidden = {"aggregateRating", "review", "ratingValue", "bestRating", "worstRating"}
        for lang, kind, path in self.pages:
            with self.subTest(page=str(path)):
                blocks = soup(path).select('script[type="application/ld+json"]')
                self.assertEqual(len(blocks), 1)
                data = json.loads(blocks[0].string)
                self.assertEqual(data.get("@context"), "https://schema.org")
                graph = data.get("@graph")
                self.assertIsInstance(graph, list)
                page_types = {"WebPage", "CollectionPage"}
                page_nodes = [x for x in graph if x.get("url") == ORIGIN + route(lang, kind) and x.get("@type") in page_types]
                self.assertEqual(len(page_nodes), 1)
                page_node = page_nodes[0]
                self.assertEqual(page_node.get("inLanguage"), lang)
                self.assertEqual(page_node.get("name"), self.catalogs[kind][lang]["pageTitle"])
                self.assertEqual(page_node.get("description"), self.catalogs[kind][lang]["pageDescription"])
                dumped = json.dumps(data)
                self.assertFalse(forbidden & set(re.findall(r'"([^" ]+)"\s*:', dumped)))

    def test_home_progressive_fallback_and_nojs_navigation(self):
        for lang in LANGS:
            path = file_for(lang, "home")
            s = soup(path)
            marker = s.find(string=lambda x: x and "arh-js-ready" in x)
            self.assertIsNotNone(marker, str(path))
            style = s.select_one("style#seoProgressiveContent")
            self.assertIsNotNone(style, str(path))
            self.assertEqual(compact_html(style.string or ""), FALLBACK_STYLE)
            nav = s.select_one("noscript#languageFallback nav")
            self.assertIsNotNone(nav)
            self.assertEqual(len(nav.select("a")), 4)
            self.assertEqual([a.get("href") for a in nav.select("a")], [route(x, "home") for x in LANGS])

    def test_unrequested_visible_copy_styles_and_form_controls_are_unchanged(self):
        if __package__:
            from .test_header import normalize_header, prior_css
        else:
            from test_header import normalize_header, prior_css
        for kind, filename in (("home", "index.html"), ("works", "works.html")):
            current = soup(ROOT / filename)
            old = BeautifulSoup(subprocess.check_output(["git", "show", f"{BASELINE}:{filename}"], cwd=ROOT, text=True), "html.parser")
            normalize_header(current, old)  # also ignores the approved GA snippet and footer privacy link
            if kind == "home":
                # The pointer console is the only newly approved body removal.
                remove_tracker_markup(old)
                # Normalize only owner-requested tier names and the preferred-plan label.
                approved_keys = ("homeText68", "homeText75", "homeText76", "homeText83",
                                 "homeText92", "homeText99", "homeText100", "homeText107", "homeText154",
                                 "homeText77", "homeText85", "homeText93", "homeText101")
                for key in approved_keys:
                    node = current.select_one(f'[data-i18n="{key}"]')
                    original = old.select_one(f'[data-i18n="{key}"]')
                    node.clear()
                    for child in list(BeautifulSoup(original.decode_contents(), "html.parser").contents):
                        node.append(child)
                current.select_one("#existingWebsiteField").decompose()
                current.select_one("#budget").replace_with(BeautifulSoup(str(old.select_one("#budget")), "html.parser").select_one("select"))
                current.select_one("#projectType").attrs.pop("aria-controls", None)
            # Ignore generated no-JS additions, but compare all original visible body copy.
            for doc in (current, old):
                for node in doc.select("noscript#languageFallback"):
                    node.decompose()
            self.assertEqual(current.body.get_text(" ", strip=True), old.body.get_text(" ", strip=True), filename)
            def forms(doc):
                return [str(x) for x in doc.select("form")]
            self.assertEqual(forms(current), forms(old), f"form changed in {filename}")
            if kind == "home":
                old_styles = [x.string or "" for x in old.select("style")]
                old_styles[0] = strip_tracker_css(old_styles[0])
                quote_style = current.select_one("style#customPricingQuote")
                self.assertIsNotNone(quote_style)
                self.assertEqual(quote_style.string, ".price.custom-quote{font-size:22px;line-height:1.35;letter-spacing:0}")
                quote_style.decompose()
                current_styles = [x.string or "" for x in current.select("style")]
                self.assertTrue(set(old_styles).issubset(current_styles))
                self.assertEqual([x for x in current_styles if x not in old_styles], [FALLBACK_STYLE])
        self.assertEqual(prior_css((ROOT / "assets/i18n.css").read_text()), subprocess.check_output(["git", "show", f"{BASELINE}:assets/i18n.css"], cwd=ROOT, text=True))

    def test_navigation_internal_paths_preserve_rendered_language(self):
        for lang, kind, path in self.pages:
            s = soup(path)
            for a in s.select("a[href]"):
                if a.find_parent("noscript"):
                    continue
                href = a["href"]
                if href.startswith(("#", "http:", "https:", "mailto:", "tel:")):
                    continue
                parsed = urlsplit(href)
                p = parsed.path
                if p in {route(x, kind) for x in LANGS}:
                    continue
                self.assertFalse(p.startswith(("/ar/", "/fr/", "/hi/")) and not p.startswith(f"/{lang}/"), href)

    def test_builder_is_idempotent(self):
        tracked = ["index.html", "works.html", "privacy.html", "sitemap.xml", "assets/home-locales.js", "assets/works-locales.js", "assets/privacy-locales.js"]
        def digest():
            h = hashlib.sha256()
            for name in tracked:
                h.update(name.encode()); h.update((ROOT / name).read_bytes())
            return h.hexdigest()
        subprocess.run([sys.executable, "tools/build_seo.py"], cwd=ROOT, check=True, capture_output=True, text=True)
        first = digest()
        subprocess.run([sys.executable, "tools/build_seo.py"], cwd=ROOT, check=True, capture_output=True, text=True)
        self.assertEqual(first, digest())


if __name__ == "__main__":
    unittest.main(verbosity=2)
