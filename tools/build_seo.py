#!/usr/bin/env python3
"""Build crawlable locale pages from the English pages and existing catalogs.

Run from any directory: python3 tools/build_seo.py
The root English documents remain the editable layout templates. This preserves
all existing body copy and styles; translations come only from the catalogs.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup, Doctype

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://arhdesign.tech'
LANGUAGES = ('en', 'ar', 'fr', 'hi')
OG_LOCALES = {'en': 'en_US', 'ar': 'ar_SA', 'fr': 'fr_FR', 'hi': 'hi_IN'}
TITLES = {
    'home': {
        'en': 'Web Design in Jeddah | ARH Digital',
        'ar': 'تصميم مواقع في جدة | ARH Digital',
        'fr': 'Création de sites web à Djeddah | ARH Digital',
        'hi': 'जेद्दा में वेबसाइट डिज़ाइन | ARH Digital',
    },
    'works': {
        'en': 'Web Design Portfolio | ARH Digital',
        'ar': 'أعمال تصميم المواقع | ARH Digital',
        'fr': 'Réalisations web | ARH Digital',
        'hi': 'वेब डिज़ाइन पोर्टफोलियो | ARH Digital',
    },
    'privacy': {
        'en': 'Privacy Policy | ARH Digital',
        'ar': 'سياسة الخصوصية | ARH Digital',
        'fr': 'Politique de confidentialité | ARH Digital',
        'hi': 'गोपनीयता नीति | ARH Digital',
    },
}
PAGES = {'home': 'index.html', 'works': 'works.html', 'privacy': 'privacy.html'}
CATALOGS = {'home': 'home-locales.js', 'works': 'works-locales.js', 'privacy': 'privacy-locales.js'}


def route(language, kind):
    prefix = '/' if language == 'en' else f'/{language}/'
    return prefix + ('' if kind == 'home' else PAGES[kind])


def catalog(kind):
    path = ROOT / 'assets' / CATALOGS[kind]
    data = json.loads(re.search(r'=\s*({.*})\s*;', path.read_text(), re.S)[1])
    for language in LANGUAGES:
        data[language]['pageTitle'] = TITLES[kind][language]
        data[language]['ogLocale'] = OG_LOCALES[language]
        for key in ('ogTitle', 'twitterTitle'):
            if key in data[language]:
                data[language][key] = TITLES[kind][language]
    path.write_text('window.ARH_LOCALES = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';\n')
    return data


def meta(soup, name, value, attribute='name'):
    tag = soup.head.find('meta', attrs={attribute: name})
    if tag is None:
        tag = soup.new_tag('meta', attrs={attribute: name})
        soup.head.append(tag)
    tag['content'] = value


def local_link(value, language):
    if not value or value.startswith(('#', 'https:', 'http:', 'mailto:', 'tel:', 'data:')):
        return value
    value = re.sub(r'^/(ar|fr|hi)/', '/', value)
    if value.startswith('assets/') or value in ('favicon.svg', 'site.webmanifest'):
        return '/' + value
    if value.startswith('/assets/') or value in ('/favicon.svg', '/site.webmanifest'):
        return value
    match = re.fullmatch(r'/?(?:index\.html)?(#.*)?', value)
    if match:
        return route(language, 'home') + (match[1] or '')
    match = re.fullmatch(r'/?works\.html(#.*)?', value)
    if match:
        return route(language, 'works') + (match[1] or '')
    match = re.fullmatch(r'/?privacy\.html(#.*)?', value)
    if match:
        return route(language, 'privacy') + (match[1] or '')
    return value


def structured_data(kind, language, strings, url):
    studio = {
        '@type': 'ProfessionalService', '@id': ORIGIN + '/#studio',
        'name': 'ARH Digital', 'url': ORIGIN + '/',
        'logo': ORIGIN + '/favicon.svg', 'image': ORIGIN + '/assets/og-cover.png',
        'email': 'Message@arhdesign.tech', 'areaServed': 'Jeddah, Saudi Arabia',
        'sameAs': ['https://www.instagram.com/arh_design2026'],
        'description': strings['pageDescription'] if kind == 'home' else 'Web design for local businesses in Jeddah and beyond.',
    }
    website = {'@type': 'WebSite', '@id': ORIGIN + '/#website', 'url': ORIGIN + '/',
               'name': 'ARH Digital', 'publisher': {'@id': studio['@id']},
               'inLanguage': list(LANGUAGES)}
    page = {'@type': 'CollectionPage' if kind == 'works' else 'WebPage',
            '@id': url + '#webpage', 'url': url, 'name': strings['pageTitle'],
            'description': strings['pageDescription'], 'inLanguage': language,
            'isPartOf': {'@id': website['@id']}, 'about': {'@id': studio['@id']}}
    graph = [studio, website, page]
    if kind == 'works':
        project = {'@type': 'CreativeWork', '@id': ORIGIN + '/works.html#shabibi',
                   'name': 'Shabibi Juice website', 'url': 'https://www.shabibi-juice.store/',
                   'creator': {'@id': studio['@id']}}
        page['mainEntity'] = {'@id': project['@id']}
        graph.append(project)
    return {'@context': 'https://schema.org', '@graph': graph}


def build_page(source, kind, language, data):
    if kind == 'home' and "classList.add('arh-js-ready')" not in source:
        source = source.replace(";$$('.reveal').forEach(e=>io.observe(e));",
                                ";document.documentElement.classList.add('arh-js-ready');$$('.reveal').forEach(e=>io.observe(e));")
    soup = BeautifulSoup(source, 'html.parser')
    for node in list(soup.contents):
        if isinstance(node, Doctype):
            node.extract()
    soup.insert(0, Doctype('html'))
    strings = data[language]
    soup.html['lang'] = language
    soup.html['dir'] = 'rtl' if language == 'ar' else 'ltr'
    soup.html['data-page-kind'] = kind
    for el in soup.select('[data-i18n]'):
        key = el['data-i18n']
        if key not in strings:
            raise ValueError(f'Missing {language}/{kind}/{key}')
        el.clear()
        fragment = BeautifulSoup(strings[key], 'html.parser')
        for child in list(fragment.contents):
            el.append(child)
    for attribute in ('placeholder', 'aria-label', 'title', 'content'):
        for el in soup.select(f'[data-i18n-{attribute}]'):
            el[attribute] = strings[el[f'data-i18n-{attribute}']]
    for option in soup.select('#languageSelect option'):
        option.attrs.pop('selected', None)
        if option['value'] == language:
            option['selected'] = ''
    for el in soup.select('[href], [src]'):
        for attribute in ('href', 'src'):
            if el.has_attr(attribute):
                el[attribute] = local_link(el[attribute], language)
    soup.title.string = strings['pageTitle']
    url = ORIGIN + route(language, kind)
    for old in soup.head.select('link[rel="canonical"], link[hreflang], meta[property="og:locale:alternate"]'):
        old.decompose()
    soup.head.append(soup.new_tag('link', rel='canonical', href=url))
    for alternate in LANGUAGES:
        soup.head.append(soup.new_tag('link', rel='alternate', hreflang=alternate,
                                     href=ORIGIN + route(alternate, kind)))
    soup.head.append(soup.new_tag('link', rel='alternate', hreflang='x-default',
                                 href=ORIGIN + route('en', kind)))
    for name in ('description',):
        meta(soup, name, strings['pageDescription'])
    for name, value in {
        'og:title': strings['pageTitle'], 'og:description': strings['pageDescription'],
        'og:url': url, 'og:locale': OG_LOCALES[language],
    }.items():
        meta(soup, name, value, 'property')
    for alternate in LANGUAGES:
        if alternate != language:
            tag = soup.new_tag('meta', attrs={'property': 'og:locale:alternate', 'content': OG_LOCALES[alternate]})
            soup.head.append(tag)
    meta(soup, 'twitter:title', strings['pageTitle'])
    meta(soup, 'twitter:description', strings['pageDescription'])
    # Metadata and the runtime agree; no late English overwrite on locale URLs.
    meta(soup, 'robots', 'index, follow, max-image-preview:large')
    if kind in ('home', 'privacy'):
        for name in ('og:image:alt',):
            meta(soup, name, strings['ogImageAlt'], 'property')
        meta(soup, 'twitter:image:alt', strings['ogImageAlt'])
    for old in soup.select('script[type="application/ld+json"]'):
        old.decompose()
    schema = soup.new_tag('script', type='application/ld+json')
    schema.string = json.dumps(structured_data(kind, language, strings, url), ensure_ascii=False, separators=(',', ':'))
    soup.head.append(schema)
    if kind == 'home':
        for old in soup.select('#seoProgressiveContent'):
            old.decompose()
        progressive = soup.new_tag('style', id='seoProgressiveContent')
        progressive.string = 'html:not(.arh-js-ready) .reveal{opacity:1;transform:none}'
        soup.head.append(progressive)
    # A real, useful language navigation fallback, visible only without JS.
    for old in soup.select('#languageFallback'):
        old.decompose()
    fallback = soup.new_tag('noscript', id='languageFallback')
    nav = soup.new_tag('nav', attrs={'aria-label': strings['languageLabel']})
    names = {'en': 'English', 'ar': 'العربية', 'fr': 'Français', 'hi': 'हिन्दी'}
    for alternate in LANGUAGES:
        link = soup.new_tag('a', href=route(alternate, kind), hreflang=alternate, lang=alternate)
        link.string = names[alternate]
        if alternate == language:
            link['aria-current'] = 'page'
        nav.append(link)
        nav.append(' · ' if alternate != LANGUAGES[-1] else '')
    fallback.append(nav)
    soup.body.insert(0, fallback)
    return str(soup).strip() + '\n'


def main():
    sources = {kind: (ROOT / filename).read_text() for kind, filename in PAGES.items()}
    all_urls = []
    for kind, source in sources.items():
        data = catalog(kind)
        for language in LANGUAGES:
            path = route(language, kind)
            filename = path.lstrip('/')
            if path.endswith('/'):
                filename += 'index.html'
            destination = ROOT / filename
            destination.parent.mkdir(exist_ok=True, parents=True)
            destination.write_text(build_page(source, kind, language, data))
            all_urls.append(ORIGIN + path)
    ET.register_namespace('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    sitemap = ET.Element(ns + 'urlset')
    for url in all_urls:
        ET.SubElement(ET.SubElement(sitemap, ns + 'url'), ns + 'loc').text = url
    ET.indent(sitemap, space='  ')
    (ROOT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(sitemap, encoding='unicode') + '\n')
    print(f'Built {len(all_urls)} static pages with self-canonicals, reciprocal hreflang and a matching sitemap.')


if __name__ == '__main__':
    main()
