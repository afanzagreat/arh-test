"""Header-only regression checks against the last approved production commit."""
import json
import re
import subprocess
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '86b8347'
CSS_MARKER = '\n/* Keep the compact Instagram icon beside Contact in both navigation layouts. */'
LABELS = {'en': 'Get a quote ↗', 'ar': 'اطلب عرض سعر ↗', 'fr': 'Demander un devis ↗', 'hi': 'कोटेशन पाएं ↗'}


def drop_analytics_and_privacy(current):
    """Undo only the approved Google Analytics snippet and footer privacy link."""
    for node in current.select('script[src^="https://www.googletagmanager.com/"], script#arhAnalytics, a.privacy-link'):
        node.decompose()
    return current


def normalize_header(current, old):
    """Undo only the approved header changes for historical preservation tests."""
    drop_analytics_and_privacy(current)
    for icon in current.select('.nav-instagram'):
        icon.decompose()
    for pair in current.select('.nav-contact'):
        pair.unwrap()
    for node, original in zip(current.select('[data-i18n="start"]'), old.select('[data-i18n="start"]')):
        node.string = original.get_text()
    return current


def prior_css(css):
    return css.split(CSS_MARKER)[0]


def baseline(path):
    return subprocess.check_output(['git', 'show', f'{BASELINE}:{path}'], cwd=ROOT, text=True)


class HeaderRegression(unittest.TestCase):
    def test_all_eight_pages_and_exact_preservation(self):
        for lang, label in LABELS.items():
            for filename in ('index.html', 'works.html'):
                path = ('' if lang == 'en' else lang + '/') + filename
                current = BeautifulSoup((ROOT / path).read_text(), 'html.parser')
                old = BeautifulSoup(baseline(path), 'html.parser')
                self.assertEqual(current.select_one('header [data-i18n="start"]').get_text(), label, path)
                pairs = current.select('.nav-contact')
                self.assertEqual(len(pairs), 2 if filename == 'index.html' else 1, path)
                for pair in pairs:
                    contact, icon = pair.find_all('a', recursive=False)
                    self.assertEqual(contact.get('data-i18n'), 'contact')
                    self.assertEqual(icon['href'], 'https://www.instagram.com/arh_design2026')
                    self.assertTrue(icon['aria-label'])
                    self.assertEqual(icon['data-i18n-aria-label'], 'instagramLabel')
                    self.assertEqual(icon['target'], '_blank')
                    self.assertIn('noopener', icon['rel'])
                    self.assertEqual(icon.svg['aria-hidden'], 'true')
                    self.assertEqual(icon.svg['width'], '18')
                self.assertEqual([str(x) for x in current.select('.insta-link')], [str(x) for x in old.select('.insta-link')], path)
                self.assertEqual(str(normalize_header(current, old)), str(old), path)

    def test_catalog_changes_are_header_only(self):
        for kind in ('home', 'works'):
            path = f'assets/{kind}-locales.js'
            parse = lambda text: json.loads(re.search(r'=\s*({.*})\s*;', text, re.S)[1])
            current, old = parse((ROOT / path).read_text()), parse(baseline(path))
            for lang in LABELS:
                self.assertEqual(current[lang].pop('start'), LABELS[lang])
                old[lang].pop('start')
                self.assertTrue(current[lang].pop('instagramLabel'))
                self.assertTrue(current[lang].pop('privacyLink'))
            self.assertEqual(current, old)
        self.assertEqual(prior_css((ROOT / 'assets/i18n.css').read_text()), baseline('assets/i18n.css'))

if __name__ == '__main__':
    unittest.main()
