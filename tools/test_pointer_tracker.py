#!/usr/bin/env python3
"""Regression tests for removing the visual ARH/LIVE SIGNAL pointer console.

The tests intentionally compare the edited homepages with the committed
baseline (caceded), removing only the baseline ``.signal-console`` node and
its CSS/handler.  This keeps unrelated markup, behavior, metadata, assets,
and the decorative hero signal bars covered byte-for-byte where practical.

Run from the repository root with::

    python3 -m unittest tools.test_pointer_tracker -v
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "caceded"
HOME_PAGES = ("index.html", "ar/index.html", "fr/index.html", "hi/index.html")
WORK_PAGES = ("works.html", "ar/works.html", "fr/works.html", "hi/works.html")

# The console is one minified CSS block, retained in the baseline style next to
# the unrelated .hero-signal rules.  Keep this deliberately selector-specific:
# orbit/hero styles containing the word "signal" are not removed or ignored.
_TRACKER_HANDLER = re.compile(r"const consoleEl=document\.querySelector\('\.signal-console'\).*$", re.S)
_TRACKER_MARKERS = (
    ".signal-console", ".signal-field", ".signal-cross", ".signal-cursor",
    ".signal-wave", ".signal-top", ".signal-bottom", ".signal-coords",
    "signalPulse", "pointermove", "LIVE SIGNAL",
)


def read_current(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def read_baseline(path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{BASELINE}:{path}"], cwd=ROOT, text=True
    )


def soup(text: str) -> BeautifulSoup:
    return BeautifulSoup(text, "html.parser")


def drop_analytics_and_privacy(document):
    """Ignore only the approved Google Analytics snippet and footer privacy link."""
    if __package__:
        from .test_header import drop_analytics_and_privacy as drop
    else:
        from test_header import drop_analytics_and_privacy as drop
    return drop(document)



def remove_tracker_markup(document: BeautifulSoup) -> BeautifulSoup:
    """Remove only the baseline console node, mutating and returning document."""
    for node in document.select(".signal-console"):
        node.decompose()
    return document


def strip_tracker_css(css: str) -> str:
    """Return baseline CSS with only the console/wave rules removed."""
    start = css.find(".signal-console{")
    end = css.find(".hero-signal{", start)
    if start < 0 or end < 0:
        raise AssertionError("baseline signal-console CSS block was not found")
    css = css[:start] + css[end:]
    css = css.replace(
        "@media(max-width:900px){.signal-console{top:auto;right:16px;bottom:18px;width:205px;height:92px}",
        "@media(max-width:900px){",
    )
    css = css.replace(".signal-field{height:46px}", "")
    css = css.replace(".signal-console{display:none}", "")
    css = css.replace(".track,.signal-wave,.hero-signal span", ".track,.hero-signal span")
    css = css.replace(
        ".signal-console,.orbit-tracker{display:none!important}",
        ".orbit-tracker{display:none!important}",
    )
    return css


def strip_tracker_handler(script: str) -> str:
    """Return the app script before its final pointer-console handler."""
    stripped, count = _TRACKER_HANDLER.subn("", script, count=1)
    if count != 1:
        raise AssertionError("baseline pointer-console handler was not found")
    return stripped


class PointerTrackerRegression(unittest.TestCase):
    maxDiff = None

    def test_all_four_homepages_have_no_tracker_markup_or_console_rules(self):
        for path in HOME_PAGES:
            doc = soup(read_current(path))
            self.assertFalse(doc.select(".signal-console"), path)
            raw = read_current(path)
            for marker in _TRACKER_MARKERS:
                self.assertNotIn(marker, raw, f"{path}: stale tracker marker {marker}")
            for style in doc.select("style"):
                self.assertNotRegex(style.string or "", r"signal-console|signal-field|signal-cross|signal-cursor|signal-wave|signalPulse")

    def test_body_is_baseline_body_after_removing_only_console(self):
        for path in HOME_PAGES:
            current = soup(read_current(path))
            old = remove_tracker_markup(soup(read_baseline(path)))
            if __package__:
                from .test_header import normalize_header
            else:
                from test_header import normalize_header
            normalize_header(current, old)
            old_inline = old.select("script:not([src])")
            old_inline[-1].string = strip_tracker_handler(old_inline[-1].string or "")
            self.assertEqual(str(current.body), str(old.body), path)

    def test_inline_scripts_preserve_app_logic_except_final_tracker_handler(self):
        for path in HOME_PAGES:
            current = drop_analytics_and_privacy(soup(read_current(path)))
            old = soup(read_baseline(path))
            now_inline = [x.string or "" for x in current.select("script:not([src])")]
            old_inline = [x.string or "" for x in old.select("script:not([src])")]
            self.assertEqual(len(now_inline), len(old_inline), path)
            self.assertEqual(now_inline[0], old_inline[0], f"{path}: JSON-LD script changed")
            self.assertEqual(now_inline[1], strip_tracker_handler(old_inline[1]), path)
            self.assertNotIn("pointermove", now_inline[1])

    def test_hero_signal_bars_and_pupil_aim_behavior_remain(self):
        for path in HOME_PAGES:
            doc = soup(read_current(path))
            self.assertEqual(len(doc.select(".hero-signal span")), 5, path)
            self.assertEqual(len(doc.select(".pupil")), 6, path)
            app = (doc.select("script:not([src])")[-1].string or "")
            for fragment in (
                "const pupils=$$('.pupil')", "function aim(x,y)",
                "addEventListener('mousemove'", "aim(e.clientX,e.clientY)",
                "addEventListener('focus'",
            ):
                self.assertIn(fragment, app, f"{path}: pupil behavior lost: {fragment}")

    def test_metadata_contact_assets_and_work_pages_are_unchanged(self):
        for path in HOME_PAGES + WORK_PAGES:
            current = drop_analytics_and_privacy(soup(read_current(path)))
            old = soup(read_baseline(path))
            self.assertEqual(
                [str(x) for x in current.select("head meta, head link")],
                [str(x) for x in old.select("head meta, head link")],
                path,
            )
            self.assertEqual(
                [x.decode_contents() for x in current.select('script[type="application/ld+json"]')],
                [x.decode_contents() for x in old.select('script[type="application/ld+json"]')],
                path,
            )
            if path in HOME_PAGES:
                self.assertEqual(
                    [(x.get("src"), x.get("defer")) for x in current.select("script[src]")],
                    [(x.get("src"), x.get("defer")) for x in old.select("script[src]")],
                    path,
                )
                self.assertEqual(str(current.select_one("form#contactForm")), str(old.select_one("form#contactForm")), path)
            else:
                if __package__:
                    from .test_header import normalize_header
                else:
                    from test_header import normalize_header
                self.assertEqual(str(normalize_header(current, old)), str(old), path)

    def test_baseline_console_css_is_the_only_inline_style_difference(self):
        for path in HOME_PAGES:
            current = soup(read_current(path))
            old = soup(read_baseline(path))
            old_styles = [x.string or "" for x in old.select("style")]
            expected = [strip_tracker_css(old_styles[0]), *old_styles[1:]]
            self.assertEqual([x.string or "" for x in current.select("style")], expected, path)


if __name__ == "__main__":
    unittest.main()
