#!/usr/bin/env python3
"""Build ARH V2's six localized, non-deployed static review pages."""
import copy
import json
import re
import shutil
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
LANGS = ('en', 'ar', 'fr', 'hi')
PAGES = ('home', 'services', 'packages', 'works', 'about', 'quote')
NAV_KEYS = {
    'home': 'navHome', 'services': 'navServices', 'packages': 'navPackages',
    'works': 'navWork', 'about': 'navAbout', 'quote': 'navQuote'
}
PAGE_TITLE_KEYS = {
    'home': 'titleHome', 'services': 'titleServices', 'packages': 'titlePackages',
    'works': 'titleWorks', 'about': 'titleAbout', 'quote': 'titleQuote'
}
PAGE_DESCRIPTION_KEYS = {
    'home': 'descriptionHome', 'services': 'descriptionServices',
    'packages': 'descriptionPackages', 'works': 'descriptionWorks',
    'about': 'descriptionAbout', 'quote': 'descriptionQuote'
}
FONT_FILES = {
    'dm-sans-latin.woff2': ('@fontsource-variable/dm-sans', 'files/dm-sans-latin-wght-normal.woff2'),
    'space-grotesk-latin.woff2': ('@fontsource-variable/space-grotesk', 'files/space-grotesk-latin-wght-normal.woff2'),
    'tajawal-arabic-400.woff2': ('@fontsource/tajawal', 'files/tajawal-arabic-400-normal.woff2'),
    'tajawal-arabic-500.woff2': ('@fontsource/tajawal', 'files/tajawal-arabic-500-normal.woff2'),
    'tajawal-arabic-700.woff2': ('@fontsource/tajawal', 'files/tajawal-arabic-700-normal.woff2'),
    'hind-devanagari-400.woff2': ('@fontsource/hind', 'files/hind-devanagari-400-normal.woff2'),
    'hind-devanagari-500.woff2': ('@fontsource/hind', 'files/hind-devanagari-500-normal.woff2'),
    'hind-devanagari-600.woff2': ('@fontsource/hind', 'files/hind-devanagari-600-normal.woff2'),
    'hind-devanagari-700.woff2': ('@fontsource/hind', 'files/hind-devanagari-700-normal.woff2'),
}
FONT_LICENSES = {
    'dm-sans-OFL.txt': '@fontsource-variable/dm-sans',
    'space-grotesk-OFL.txt': '@fontsource-variable/space-grotesk',
    'tajawal-OFL.txt': '@fontsource/tajawal',
    'hind-OFL.txt': '@fontsource/hind',
}


def catalog(name):
    source = (ROOT / f'assets/{name}-locales.js').read_text()
    match = re.search(r'=\s*({.*})\s*;', source, re.S)
    if not match:
        raise ValueError(f'Could not read locale catalog: {name}')
    return json.loads(match[1])


def route(lang, page):
    prefix = './' if lang == 'en' else f'{lang}/'
    return prefix if page == 'home' else prefix + f'{page}.html'


def node(html):
    return BeautifulSoup(html, 'html.parser')


def text(key, tag='p', cls=''):
    classes = f' class="{cls}"' if cls else ''
    return f'<{tag}{classes} data-i18n="{key}"></{tag}>'


def intro(title, lead, page):
    return ('<section class="page-intro wrap" data-page-intro>'
            f'<h1 data-i18n="{title}"></h1>'
            f'<p class="lead" data-i18n="{lead}"></p>'
            '</section>')


def cta():
    return ('<section class="closing-cta wrap" data-reveal>'
            '<div class="closing-copy"><h2 data-i18n="ctaTitle"></h2>'
            '<p data-i18n="ctaLead"></p></div>'
            '<a class="btn btn-primary" href="/quote.html" data-i18n="ctaButton"></a>'
            '</section>')


def strip_reveal_markers(section):
    for element in section.select('.reveal'):
        element['class'] = [name for name in element.get('class', []) if name != 'reveal']
    section['data-reveal'] = ''
    return section


def remove_eyebrows(section):
    for element in section.select('.eyebrow'):
        element.decompose()
    return section


def copy_runtime_assets():
    vendor = ROOT / 'assets/vendor'
    fonts = ROOT / 'assets/fonts'
    vendor.mkdir(parents=True, exist_ok=True)
    fonts.mkdir(parents=True, exist_ok=True)
    gsap_source = ROOT / 'node_modules/gsap/dist/gsap.min.js'
    if not gsap_source.exists():
        raise SystemExit('GSAP is missing. Run npm install before building the site.')
    gsap_text = gsap_source.read_text(encoding='utf-8').rstrip()
    (vendor / 'gsap.min.js').write_text('\n'.join(line.rstrip() for line in gsap_text.splitlines()) + '\n', encoding='utf-8')
    for target, (package, relative) in FONT_FILES.items():
        source = ROOT / 'node_modules' / package / relative
        if not source.exists():
            raise SystemExit(f'Font asset is missing: {source.relative_to(ROOT)}. Run npm install before building.')
        shutil.copyfile(source, fonts / target)
    for target, package in FONT_LICENSES.items():
        source = ROOT / 'node_modules' / package / 'LICENSE'
        if not source.exists():
            raise SystemExit(f'Font license is missing: {source.relative_to(ROOT)}')
        shutil.copyfile(source, fonts / target)


def add_language_routes(html, lang, page):
    for element in html.select('[href]'):
        href = element['href']
        if element.has_attr('data-plan'):
            element['href'] = route(lang, 'quote') + '?plan=' + element['data-plan']
        elif href.startswith('#'):
            if href == '#contact':
                element['href'] = route(lang, 'quote')
            else:
                element['href'] = route(lang, page) + href
        elif href.startswith('/assets/'):
            element['href'] = href.lstrip('/')
        elif href in ['/favicon.svg', '/site.webmanifest']:
            element['href'] = href.lstrip('/')
        elif href.startswith('/'):
            if href in ['/', '/index.html']:
                target = 'home'
            elif re.fullmatch(r'/(services|packages|works|about|quote)\.html', href):
                target = href[1:-5]
            else:
                continue
            element['href'] = route(lang, target)


def main():
    copy_runtime_assets()
    home_template = node((ROOT / 'tools/prototype-templates/home.html').read_text())
    base_css = (ROOT / 'tools/prototype-templates/base-v2.css').read_text()
    (ROOT / 'assets/prototype-base.css').write_text(base_css + '\n')

    base = catalog('home')
    work_catalog = catalog('works')
    current_copy = json.loads((ROOT / 'assets/prototype-copy.json').read_text())
    v2_copy = json.loads((ROOT / 'assets/v2-copy.json').read_text())
    for lang in LANGS:
        base[lang].update({'work_' + key: value for key, value in work_catalog[lang].items()})
        base[lang].update(current_copy[lang])
        base[lang].update(v2_copy[lang])
        base[lang].update({
            'homeText15': v2_copy[lang]['homeServicesLabel'],
            'homeText31': v2_copy[lang]['homeServicesLabel'],
            'homeText32': v2_copy[lang]['processTitle'],
            'homeText34': v2_copy[lang]['processLead'],
            'homeText55': v2_copy[lang]['packagesTitle'],
            'homeText124': v2_copy[lang]['faqTitle'],
            'homeText138': v2_copy[lang]['quotePanelTitle'],
        })
        # The reference template uses em-dashes in inherited labels. Keep the V2 copy audit mechanical.
        for key, value in list(base[lang].items()):
            if isinstance(value, str):
                base[lang][key] = value.replace('—', ' · ')

    services = strip_reveal_markers(copy.deepcopy(home_template.select_one('#services')))
    services['id'] = 'services'
    services.select_one('.eyebrow')['data-i18n'] = 'homeServicesLabel'
    process = strip_reveal_markers(copy.deepcopy(home_template.select_one('section.process')))
    remove_eyebrows(process)
    process.select_one('h2')['data-i18n'] = 'processTitle'
    process.select_one('.lead')['data-i18n'] = 'processLead'
    pricing = strip_reveal_markers(copy.deepcopy(home_template.select_one('#pricing')))
    pricing['id'] = 'pricing'
    remove_eyebrows(pricing)
    if pricing.select_one('h2'):
        pricing.select_one('h2').decompose()
    if pricing.select_one('.lead'):
        pricing.select_one('.lead').decompose()
    faq = strip_reveal_markers(copy.deepcopy(home_template.select_one('#faq')))
    faq['id'] = 'faq'
    remove_eyebrows(faq)
    contact = node(str(home_template.select_one('#contact')))
    contact['data-reveal'] = ''
    contact['class'] = [name for name in contact.get('class', []) if name != 'reveal']
    for eyebrow in contact.select('.eyebrow'):
        eyebrow.decompose()
    if contact.select_one('h2'):
        contact.select_one('h2').decompose()
    side = contact.select_one('.contact-side')
    side.clear()
    side.append(node(text('quoteTitle', 'h1', 'quote-heading') + text('quoteLead', 'p', 'lead') +
                     text('quoteDemo', 'p', 'note') +
                     '<a class="text-link" href="/packages.html" data-i18n="navPackages"></a>'))
    form = contact.select_one('form')
    form.attrs.update({'action': '#', 'data-prototype': 'true'})
    for hidden in form.select('input[type="hidden"]'):
        hidden.decompose()
    form.select_one('button[type="submit"]')['data-i18n'] = 'quoteSubmit'
    form.select_one('button[type="submit"]')['disabled'] = ''
    form.append(node('<section id="briefReview" class="brief-review" hidden tabindex="-1">' +
                     text('reviewTitle', 'h2') + '<dl id="briefDetails"></dl>' + text('reviewNote') + '</section>'))
    budget = form.select_one('#budget')
    if budget.select_one('option[value="unsure"]'):
        budget.select_one('option[value="unsure"]')['selected'] = ''

    home_hero = (
        '<section class="home-hero wrap">'
        '<div class="home-hero-copy" data-intro>'
        '<p class="eyebrow" data-i18n="kicker"></p>'
        '<h1 data-i18n="heroTitle"></h1>'
        '<p class="hero-lead" data-i18n="heroText"></p>'
        '<div class="actions"><a class="btn btn-primary" href="/quote.html" data-i18n="heroCta"></a>'
        '<a class="btn btn-quiet" href="/works.html" data-i18n="seeWork"></a></div>'
        '</div>'
        '<div class="hero-art" aria-hidden="true" data-intro>'
        '<div class="hero-art-top"><span>ARH</span><span>DIGITAL STUDIO</span></div>'
        '<div class="hero-art-mark"><span>A</span><span>R</span><span>H</span></div>'
        '<div class="hero-art-orbit"></div><div class="hero-art-stamp">ARH</div>'
        '<div class="hero-art-bottom"><span>ARH DIGITAL</span><i>JEDDAH</i></div>'
        '</div></section>'
    )
    home_ribbon = '<section class="home-ribbon wrap" aria-label="Studio approach" data-i18n-aria-label="studioApproach"><span data-i18n="homeRibbon"></span></section>'
    home_case = (
        '<section class="home-case wrap" data-reveal><div class="case-copy">'
        '<p class="eyebrow" data-i18n="homeCaseEyebrow"></p>'
        '<h2 data-i18n="homeCaseTitle"></h2><p class="lead" data-i18n="homeCaseBody"></p>'
        '<a class="text-link" href="/works.html" data-i18n="homeCaseLink"></a></div>'
        '<a class="case-image" href="/works.html">'
        '<img src="/assets/shabibi-home-hero.jpg" alt="" width="1920" height="1280" loading="lazy">'
        '<span class="image-note" data-i18n="homeCaseEyebrow"></span></a></section>'
    )
    work_hero = (
        '<section class="work-hero wrap"><div class="work-heading" data-intro>'
        '<p class="eyebrow" data-i18n="work_recent"></p><h1 data-i18n="work_worksTitle"></h1>'
        '<p class="lead" data-i18n="workIntro"></p></div>'
        '<figure class="work-hero-image case-image" data-intro>'
        '<img src="/assets/shabibi-home-hero.jpg" data-i18n-alt="workImageHeroAlt" width="1920" height="1280" loading="eager" fetchpriority="high">'
        '<figcaption data-i18n="workImageHeroAlt"></figcaption></figure></section>'
    )
    case_details = (
        '<section class="case-details wrap" id="shabibi" data-reveal>'
        '<div class="case-context"><p class="eyebrow" data-i18n="work_juiceBar"></p>'
        '<h2 data-i18n="caseContext"></h2><p class="lead" data-i18n="caseContextBody"></p></div>'
        '<div class="case-columns"><article><h3 data-i18n="caseApproach"></h3><p data-i18n="caseApproachBody"></p></article>'
        '<article><h3 data-i18n="caseOutcome"></h3><p data-i18n="caseOutcomeBody"></p></article>'
        '<article><h3 data-i18n="work_liveWebsite"></h3><p data-i18n="work_caseBody"></p>'
        '<a class="text-link" href="https://www.shabibi-juice.store/" target="_blank" rel="noopener" data-i18n="work_visit"></a></article></div></section>'
    )
    work_gallery = (
        '<section class="case-gallery wrap" data-reveal><div class="gallery-intro">'
        '<h2 data-i18n="workGalleryTitle"></h2><p class="lead" data-i18n="workGalleryLead"></p></div>'
        '<div class="gallery-grid"><figure class="gallery-fruit"><img src="/assets/shabibi-fruit.webp" data-i18n-alt="workImageFruitAlt" width="1200" height="900" loading="lazy"><figcaption data-i18n="workImageFruitAlt"></figcaption></figure>'
        '<figure class="gallery-mark"><img src="/assets/shabibi-logo.webp" data-i18n-alt="workImageMarkAlt" width="256" height="256" loading="lazy"><figcaption data-i18n="workImageMarkAlt"></figcaption></figure>'
        '<div class="gallery-note"><span>ARH × SHABIBI</span><p data-i18n="workGalleryLead"></p></div></div></section>'
    )
    about_intro = (
        '<section class="page-intro about-intro wrap" data-page-intro><div class="about-title">'
        '<p class="eyebrow" data-i18n="aboutEyebrow"></p><h1 data-i18n="aboutTitle"></h1></div>'
        '<div class="about-intro-copy"><p class="lead" data-i18n="aboutLead"></p><p data-i18n="aboutBody"></p></div></section>'
    )
    about_values = (
        '<section class="about-values wrap" data-reveal><div class="values-heading"><h2 data-i18n="aboutManifesto"></h2>'
        '<p class="lead" data-i18n="aboutManifestoBody"></p></div><div class="principles">'
        + ''.join('<article class="principle"><span class="principle-mark" aria-hidden="true">0' + str(i) + '</span>' +
                  text(f'aboutPrinciple{i}', 'h3') + text(f'aboutPrinciple{i}Body') + '</article>' for i in range(1, 4)) +
        '</div></section>'
    )
    about_quotes = (
        '<section class="studio-notes wrap" data-reveal><blockquote data-i18n="homeText49"></blockquote>'
        '<div><p data-i18n="homeText51"></p><p data-i18n="homeText53"></p></div></section>'
    )
    pages = {
        'home': home_hero + home_ribbon + home_case + str(services) + str(process) + cta(),
        'services': intro('servicesPageTitle', 'servicesLead', 'services') + str(services) + str(process) + cta(),
        'packages': intro('packagesTitle', 'packagesLead', 'packages') + str(pricing) + str(faq) + cta(),
        'works': work_hero + str(case_details) + work_gallery + cta(),
        'about': about_intro + about_values + about_quotes + str(process) + cta(),
        'quote': str(contact),
    }
    fonts_css = '''@font-face{font-family:"DM Sans";src:url("/assets/fonts/dm-sans-latin.woff2") format("woff2");font-weight:100 900;font-style:normal;font-display:swap}\n@font-face{font-family:"Space Grotesk";src:url("/assets/fonts/space-grotesk-latin.woff2") format("woff2");font-weight:300 700;font-style:normal;font-display:swap}\n@font-face{font-family:"Tajawal";src:url("/assets/fonts/tajawal-arabic-400.woff2") format("woff2");font-weight:400;font-style:normal;font-display:swap}\n@font-face{font-family:"Tajawal";src:url("/assets/fonts/tajawal-arabic-500.woff2") format("woff2");font-weight:500 600;font-style:normal;font-display:swap}\n@font-face{font-family:"Tajawal";src:url("/assets/fonts/tajawal-arabic-700.woff2") format("woff2");font-weight:700 900;font-style:normal;font-display:swap}\n@font-face{font-family:"Hind";src:url("/assets/fonts/hind-devanagari-400.woff2") format("woff2");font-weight:400;font-style:normal;font-display:swap}\n@font-face{font-family:"Hind";src:url("/assets/fonts/hind-devanagari-500.woff2") format("woff2");font-weight:500;font-style:normal;font-display:swap}\n@font-face{font-family:"Hind";src:url("/assets/fonts/hind-devanagari-600.woff2") format("woff2");font-weight:600;font-style:normal;font-display:swap}\n@font-face{font-family:"Hind";src:url("/assets/fonts/hind-devanagari-700.woff2") format("woff2");font-weight:700 900;font-style:normal;font-display:swap}\n'''
    fonts_css = fonts_css.replace('url("/assets/fonts/', 'url("fonts/')
    (ROOT / 'assets/prototype-base.css').write_text(fonts_css + base_css.rstrip() + '\n')

    for page, body in pages.items():
        for lang in LANGS:
            strings = copy.deepcopy(base[lang])
            strings['pageTitle'] = strings[PAGE_TITLE_KEYS[page]]
            strings['pageDescription'] = strings[PAGE_DESCRIPTION_KEYS[page]]
            locale_file = ROOT / f'assets/{page}-prototype-locales.js'
            locale_file.write_text('window.ARH_LOCALES = ' + json.dumps({l: base[l] for l in LANGS}, ensure_ascii=False, indent=2) + ';\n')
            nav = ''.join(
                f'<a href="{route(lang, target)}" data-i18n="{NAV_KEYS[target]}"' +
                (' aria-current="page"' if target == page else '') + '></a>'
                for target in PAGES
            )
            language_options = ''.join(
                f'<option value="{code}" lang="{code}"' + (' selected' if code == lang else '') + f'>{label}</option>'
                for code, label in [('en', 'English'), ('ar', 'العربية'), ('fr', 'Français'), ('hi', 'हिन्दी')]
            )
            html = f'''<!doctype html>
<html lang="{lang}" dir="{'rtl' if lang == 'ar' else 'ltr'}" data-theme="light" data-page-kind="{page}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<base href="{'./' if lang == 'en' else '../'}">
<title>{strings['pageTitle']}</title>
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="description" content="{strings['pageDescription']}">
<meta http-equiv="Content-Security-Policy" content="form-action 'none'; connect-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'self'">
<link rel="icon" href="favicon.svg" type="image/svg+xml"><link rel="manifest" href="site.webmanifest">
<script>try{{const t=localStorage.getItem('arh-test-theme');if(t==='dark')document.documentElement.dataset.theme=t}}catch(e){{}}</script>
<link rel="preload" href="/assets/fonts/dm-sans-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/space-grotesk-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/prototype-base.css">
</head>
<body>
<a class="skip-link" href="{route(lang, page)}#mainContent" data-i18n="skipToContent"></a>
<div class="announce prototype-banner" data-i18n="prototypeBanner"></div>
<header class="site-header"><nav class="wrap header-row" aria-label="Main navigation" data-i18n-aria-label="mainNavLabel">
<a class="logo" href="{route(lang, 'home')}" aria-label="ARH Digital home"><span>ARH</span><i>.</i></a>
<div class="links">{nav}</div>
<div class="controls"><select id="languageSelect" class="language-select" data-i18n-aria-label="languageLabel">{language_options}</select>
<button id="themeBtn" class="theme-btn" type="button" aria-pressed="false" data-i18n-aria-label="aria_themeBtn"><span class="theme-glyph" aria-hidden="true">◐</span></button></div>
<button id="menuBtn" type="button" class="menu" aria-expanded="false" aria-controls="mobileNav" data-i18n-aria-label="aria_menuBtn"><span aria-hidden="true">≡</span></button>
</nav></header>
<div class="mobile-nav" id="mobileNav" aria-hidden="true" inert aria-label="Mobile navigation" data-i18n-aria-label="mobileNavLabel">
<button type="button" class="mobile-close" id="closeMenu" data-i18n-aria-label="aria_closeMenu"><span aria-hidden="true">×</span></button>{nav}
</div>
<main id="mainContent" tabindex="-1">{body}</main>
<footer class="site-footer"><div class="wrap footer-row"><a class="logo" href="{route(lang, 'home')}" aria-label="ARH Digital home"><span>ARH</span><i>.</i></a><p data-i18n="footerLine"></p><a class="footer-link" href="{route(lang, 'quote')}" data-i18n="navQuote"></a><small data-i18n="footerPrivacy"></small></div></footer>
<div class="theme-veil" id="themeVeil" aria-hidden="true"></div>
<div class="site-loader" id="siteLoader" role="dialog" aria-labelledby="loaderStatus" hidden aria-hidden="true">
<div class="loader-top"><span class="loader-wordmark">ARH<span>.</span></span><button id="loaderSkip" class="loader-skip" type="button" data-i18n="loaderSkip"></button></div>
<div class="loader-center"><span class="loader-kicker" id="loaderStatus" role="status" aria-live="polite" aria-atomic="true" data-i18n="loaderStatus"></span><span class="loader-glyph" id="loaderGlyph" aria-hidden="true">00</span></div>
<div class="loader-bottom"><span>ARH DIGITAL / JEDDAH</span><span class="loader-sequence" aria-hidden="true">A&nbsp; / &nbsp;R&nbsp; / &nbsp;H</span></div>
</div>
<script src="/assets/{page}-prototype-locales.js"></script><script src="/assets/i18n.js"></script><script src="/assets/contact-form.js"></script>
<script src="/assets/vendor/gsap.min.js" defer></script><script src="/assets/prototype.js" defer></script>
</body></html>'''
            html = html.replace('="/assets/', '="assets/')
            soup = node(html)
            for element in soup.select('[data-i18n]'):
                key = element['data-i18n']
                element.clear()
                fragment = node(strings[key])
                for child in list(fragment.contents):
                    element.append(child)
            for attr in ['placeholder', 'aria-label', 'title', 'content', 'alt']:
                for element in soup.select(f'[data-i18n-{attr}]'):
                    element[attr] = strings[element[f'data-i18n-{attr}']]
            for element in soup.select('.reveal'):
                element['class'] = [name for name in element.get('class', []) if name != 'reveal']
            add_language_routes(soup, lang, page)
            fallback = soup.new_tag('noscript')
            fallback.append(node('<nav class="fallback-languages" aria-label="Choose a language">' +
                                 ' · '.join(f'<a href="{route(code, page)}" lang="{code}">{label}</a>' for code, label in [('en','English'),('ar','العربية'),('fr','Français'),('hi','हिन्दी')]) + '</nav>'))
            soup.body.insert(0, fallback)
            destination = ROOT / route(lang, page)
            if destination.suffix != '.html':
                destination = destination / 'index.html'
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(str(soup) + '\n')
            locale_file = ROOT / f'assets/{page}-prototype-locales.js'
            if lang == LANGS[-1]:
                locale_file.write_text('window.ARH_LOCALES = ' + json.dumps({l: base[l] for l in LANGS}, ensure_ascii=False, indent=2) + ';\n')

    (ROOT / 'robots.txt').write_text('User-agent: *\nDisallow: /\n')
    (ROOT / 'sitemap.xml').unlink(missing_ok=True)
    (ROOT / 'CNAME').unlink(missing_ok=True)
    print('Built 24 ARH V2 review pages; no live form endpoint, domain binding, or sitemap.')


if __name__ == '__main__':
    main()
