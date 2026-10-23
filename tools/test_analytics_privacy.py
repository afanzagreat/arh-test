#!/usr/bin/env python3
"""Checks for the Google Analytics snippet and the four-language privacy policy."""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
GA_ID = "G-XGKTMX6X5N"
LANGS = ("en", "ar", "fr", "hi")
BASE = "9674c49"  # production main when the analytics branch was cut


def path_for(lang: str, name: str) -> str:
    return ("" if lang == "en" else lang + "/") + name


def soup(path: str) -> BeautifulSoup:
    return BeautifulSoup((ROOT / path).read_text(), "html.parser")


class AnalyticsAndPrivacy(unittest.TestCase):
    pages = [path_for(lang, name) for lang in LANGS for name in ("index.html", "works.html", "privacy.html")]

    def test_every_page_loads_ga4_once_with_the_users_measurement_id(self):
        for path in self.pages:
            with self.subTest(page=path):
                s = soup(path)
                loaders = s.select('head script[src*="googletagmanager.com/gtag/js"]')
                self.assertEqual([x["src"] for x in loaders],
                                 [f"https://www.googletagmanager.com/gtag/js?id={GA_ID}"])
                config = s.select("head script#arhAnalytics")
                self.assertEqual(len(config), 1)
                code = config[0].string
                self.assertEqual(re.findall(r"G-[A-Z0-9]+", code), [GA_ID])
                self.assertIn("allow_google_signals:false", code)
                self.assertIn("allow_ad_personalization_signals:false", code)
                raw = (ROOT / path).read_text()
                self.assertEqual(raw.count(GA_ID), 2)  # loader URL + config call, nothing else

    def test_no_other_new_third_party_hosts_were_added(self):
        allowed_new = {"www.googletagmanager.com", "web3forms.com", "policies.google.com", "tools.google.com"}
        for path in self.pages:
            old_path = path
            try:
                old = subprocess.check_output(["git", "show", f"{BASE}:{old_path}"], cwd=ROOT, text=True,
                                              stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                old = ""
            hosts = lambda text: {urlsplit(u).netloc for u in re.findall(r'(?:src|href|action)="(https?://[^"]+)"', text)}
            new_hosts = hosts((ROOT / path).read_text()) - hosts(old)
            if old:
                self.assertLessEqual(new_hosts, {"www.googletagmanager.com"}, path)
            else:  # brand-new privacy page
                self.assertLessEqual(new_hosts - hosts((ROOT / "works.html").read_text()), allowed_new, path)

    def test_footer_links_to_the_privacy_page_in_the_same_language(self):
        for lang in LANGS:
            for name in ("index.html", "works.html"):
                with self.subTest(lang=lang, page=name):
                    link = soup(path_for(lang, name)).select_one("footer a.privacy-link")
                    self.assertIsNotNone(link)
                    self.assertEqual(link["href"], ("/" if lang == "en" else f"/{lang}/") + "privacy.html")
                    self.assertTrue(link.get_text(strip=True))

    def test_privacy_page_covers_what_the_site_actually_does(self):
        needles = ("Google Analytics", "Web3Forms", "GitHub Pages", "Google Fonts", "Message@arhdesign.tech", "_ga")
        for lang in LANGS:
            with self.subTest(lang=lang):
                s = soup(path_for(lang, "privacy.html"))
                text = s.main.get_text(" ", strip=True)
                for needle in needles:
                    self.assertIn(needle, text)
                self.assertEqual(len(s.select("main h1")), 1)
                self.assertGreaterEqual(len(s.select("main section h2")), 10)
                self.assertTrue(s.select_one('a[href="https://tools.google.com/dlpage/gaoptout"]'))
                self.assertTrue(s.select_one('a[href="mailto:Message@arhdesign.tech"]'))
                self.assertEqual(s.html["lang"], lang)
                self.assertEqual(s.html["dir"], "rtl" if lang == "ar" else "ltr")
                # Every outward link opened in a new tab must be safe.
                for a in s.select('main a[target="_blank"]'):
                    self.assertIn("noopener", a.get("rel", []))

    def test_privacy_header_and_language_switcher_work(self):
        for lang in LANGS:
            s = soup(path_for(lang, "privacy.html"))
            self.assertEqual(s.html["data-page-kind"], "privacy")
            self.assertEqual([o["value"] for o in s.select("#languageSelect option")], list(LANGS))
            self.assertEqual(s.select_one("header .cta")["data-i18n"], "start")
            self.assertTrue(s.select_one("header .nav-instagram"))

    def test_pricing_cta_instagram_and_seo_basics_are_untouched(self):
        # Compare visible home copy against production once the approved additions are stripped.
        for lang in LANGS:
            path = path_for(lang, "index.html")
            now = soup(path)
            for node in now.select('script#arhAnalytics, script[src*="googletagmanager"], a.privacy-link'):
                node.decompose()
            old = BeautifulSoup(subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True),
                                "html.parser")
            self.assertEqual(str(now), str(old), path)
        for path in ("index.html", "works.html"):
            s = soup(path)
            self.assertEqual(len(s.select('link[rel="canonical"]')), 1)
            self.assertEqual(len(s.select('script[type="application/ld+json"]')), 1)
        home = (ROOT / "index.html").read_text()
        for price in ("$26", "$99", "$40", "$209"):
            self.assertIn(price, home)
        self.assertNotIn("signal-console", home)

    def test_llms_txt_is_accurate_and_links_resolve(self):
        text = (ROOT / "llms.txt").read_text()
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith("# ARH Digital"))
        self.assertTrue(any(x.startswith("> ") for x in lines[:4]))
        for section in ("## Services", "## Pricing", "## Languages", "## Key pages", "## Contact"):
            self.assertIn(section, lines)
        for fact in ("$26", "$99", "$40", "$209", "Custom", "Message@arhdesign.tech", "Jeddah",
                     "https://www.instagram.com/arh_design2026"):
            self.assertIn(fact, text)
        # Every first-party link must point at a file that exists in this repo.
        for url in re.findall(r"\]\((https://arhdesign\.tech[^)\s]*)\)", text):
            path = urlsplit(url).path
            target = ROOT / (path.lstrip("/") + ("index.html" if path.endswith("/") else ""))
            self.assertTrue(target.is_file(), url)
        # Pricing must match the home page (single source of truth).
        home = (ROOT / "index.html").read_text()
        for price in re.findall(r"\$\d+", text):
            self.assertIn(price, home)
        self.assertNotIn("G-XGKTMX6X5N", text)

    def test_privacy_pages_are_in_robots_open_sitemap(self):
        sitemap = (ROOT / "sitemap.xml").read_text()
        for lang in LANGS:
            self.assertIn("https://arhdesign.tech/" + path_for(lang, "privacy.html"), sitemap)
        self.assertNotIn("Disallow: /privacy", (ROOT / "robots.txt").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
