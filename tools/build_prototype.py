#!/usr/bin/env python3
"""Build private, non-deployed prototype pages from preserved production templates."""
import copy
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
LANGS = ('en', 'ar', 'fr', 'hi')
PAGES = ('home', 'services', 'packages', 'works', 'about', 'quote')

def catalog(name):
    return json.loads(re.search(r'=\s*({.*})\s*;', (ROOT / f'assets/{name}-locales.js').read_text(), re.S)[1])

def route(lang, page):
    return ('/' if lang == 'en' else f'/{lang}/') + ('' if page == 'home' else f'{page}.html')

def node(html):
    return BeautifulSoup(html, 'html.parser')

def text(key, tag='p', cls=''):
    return f'<{tag} class="{cls}" data-i18n="{key}"></{tag}>'

def intro(title, lead=None):
    return '<section class="wrap page-intro">' + text(title, 'h1') + (text(lead, 'p', 'lead') if lead else '') + '</section>'

def cta():
    return '<section class="wrap cta"><div class="cta-box">' + text('quoteTitle', 'h2') + '<div class="actions centered"><a class="btn" href="/quote.html" data-i18n="navQuote"></a></div></div></section>'

def studio_spark():
    # Pure decoration: no pointer listeners, coordinates, canvas or user input.
    return '<div class="wrap studio-signoff" aria-hidden="true"><span class="spark-rule"></span><div class="studio-spark"><span class="spark-halo"></span><span class="spark-star"></span><span class="spark-orbit"><i></i></span></div><span class="spark-rule"></span></div>'

def main():
    home = node((ROOT / 'tools/prototype-templates/home.html').read_text())
    work = node((ROOT / 'tools/prototype-templates/works.html').read_text())
    base = catalog('home')
    works = catalog('works')
    extra = json.loads((ROOT / 'assets/prototype-copy.json').read_text())
    for lang in LANGS:
        base[lang].update({'work_' + k: v for k, v in works[lang].items()})
        base[lang].update(extra[lang])
    styles = '\n'.join(s.get_text() for s in home.head.select('style'))
    (ROOT / 'assets/prototype-base.css').write_text(styles + '\n')
    sections = {name: str(home.select_one('#' + name)) for name in ['services','pricing','contact','faq']}
    process = str(home.select_one('section.process'))
    hero = copy.deepcopy(home.select_one('section.hero'))
    hero.select_one('[data-i18n="heroCta"]')['href'] = '/quote.html'
    hero.select_one('[data-i18n="seeWork"]')['href'] = '/works.html'
    case_card = '<section class="wrap case-teaser"><div><div class="eyebrow">01 / SHABIBI JUICE</div>' + text('work_caseTitle','h2') + text('workIntro','p','lead') + '<a class="btn" href="/works.html" data-i18n="browseWork"></a></div><a href="/works.html" class="case-image" aria-label="Shabibi Juice"><img src="/assets/shabibi-home-hero.jpg" alt="Shabibi Juice" loading="lazy" width="900" height="600"></a></section>'
    about = intro('aboutTitle','aboutLead') + '<section class="wrap about-layout"><div>' + text('aboutEyebrow','div','eyebrow') + text('aboutBody','p','lead') + '</div><div class="principles">' + ''.join('<article class="service">'+text(f'aboutPrinciple{i}','h3')+text(f'aboutPrinciple{i}Body')+'</article>' for i in range(1,4)) + '</div></section>'
    quote = node(sections['contact'])
    quote.select_one('h2')['data-i18n'] = 'quoteTitle'
    quote.select_one('h2').name = 'h1'
    quote.select_one('.contact-side').clear()
    side = quote.select_one('.contact-side')
    side.append(node(text('quoteLead','p','lead') + text('quoteDemo','p','note') + '<a class="btn outline" href="/packages.html" data-i18n="navPackages"></a>'))
    form = quote.select_one('form')
    form.attrs.update({'action':'#','data-prototype':'true'})
    for hidden in form.select('input[type="hidden"]'): hidden.decompose()
    form.select_one('button[type="submit"]')['data-i18n'] = 'quoteSubmit'
    # Without JavaScript the form is visibly read-only, never a production endpoint.
    form.select_one('button[type="submit"]')['disabled'] = ''
    form.append(node('<noscript>'+text('quoteDemo')+'</noscript>'))
    form.append(node('<section id="briefReview" class="brief-review" hidden tabindex="-1">'+text('reviewTitle','h3')+'<dl id="briefDetails"></dl>'+text('reviewNote')+'</section>'))
    budget = form.select_one('#budget')
    budget.select_one('option[value="unsure"]')['selected']=''
    details = '<section class="wrap case-study" id="shabibi"><div class="case-image"><img src="/assets/shabibi-home-hero.jpg" alt="Shabibi Juice" width="1200" height="800"></div><div class="case-columns">' + ''.join('<article>'+text('case'+part,'h2')+text('case'+part+'Body')+'</article>' for part in ['Context','Approach','Outcome']) + '</div><a class="btn outline" href="https://www.shabibi-juice.store/" target="_blank" rel="noopener" data-i18n="work_visit"></a></section>'
    pages = {
        'home': str(hero) + '<section class="wrap shortcut"><a class="btn outline" href="/services.html" data-i18n="homeNext"></a><a class="btn outline" href="/packages.html" data-i18n="navPackages"></a></section>' + case_card + cta(),
        'services': intro('servicesPageTitle','servicesLead') + sections['services'] + process + cta(),
        'packages': intro('packagesTitle','homeText57') + sections['pricing'] + sections['faq'] + cta(),
        'works': intro('work_worksTitle','workIntro') + details + cta(),
        'about': about + process + cta(),
        'quote': str(quote),
    }
    nav_keys = dict(zip(PAGES, ['navHome','navServices','navPackages','navWork','navAbout','navQuote']))
    fonts = home.select_one('link[href*="fonts.googleapis.com/css2"]')['href']
    for page, body in pages.items():
        strings = copy.deepcopy(base)
        for lang in LANGS:
            strings[lang]['pageTitle'] = f"{strings[lang][nav_keys[page]]} | ARH Digital — Prototype"
            strings[lang]['pageDescription'] = strings[lang]['aboutLead']
        (ROOT / f'assets/{page}-prototype-locales.js').write_text('window.ARH_LOCALES = '+json.dumps(strings,ensure_ascii=False,indent=2)+';\n')
        for lang in LANGS:
            nav = ''.join(f'<a href="{route(lang,p)}" data-i18n="{nav_keys[p]}"'+(' aria-current="page"' if p==page else '')+'></a>' for p in PAGES[:-1])
            languages = ''.join(f'<option value="{l}" lang="{l}"'+(' selected' if l==lang else '')+f'>{label}</option>' for l,label in [('en','English'),('ar','العربية'),('fr','Français'),('hi','हिन्दी')])
            html = f'''<!doctype html><html lang="{lang}" dir="{'rtl' if lang=='ar' else 'ltr'}" data-page-kind="{page}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title></title><meta name="robots" content="noindex,nofollow,noarchive"><meta name="description" data-i18n-content="pageDescription"><meta http-equiv="Content-Security-Policy" content="form-action 'none'; connect-src 'none'; frame-src 'none'"><link rel="icon" href="/favicon.svg"><link rel="stylesheet" href="{fonts}"><link rel="stylesheet" href="/assets/prototype-base.css"><link rel="stylesheet" href="/assets/i18n.css"><link rel="stylesheet" href="/assets/prototype.css"></head><body><a class="skip-link" href="#mainContent" data-i18n="navHome"></a><div class="announce prototype-banner" data-i18n="prototypeBanner"></div><header><nav class="wrap"><a class="logo" href="{route(lang,'home')}">ARH<b>.</b></a><div class="links">{nav}</div><div class="controls"><select id="languageSelect" class="language-select" data-i18n-aria-label="languageLabel">{languages}</select><button id="themeBtn" class="icon-btn" type="button" data-i18n-aria-label="aria_themeBtn">◐</button><a class="btn nav-quote" href="{route(lang,'quote')}" data-i18n="navQuote"></a></div><button id="menuBtn" type="button" class="menu" aria-expanded="false" aria-controls="mobileNav" data-i18n-aria-label="aria_menuBtn">☰</button></nav></header><div class="mobile-nav" id="mobileNav" aria-hidden="true"><button type="button" class="close" id="closeMenu" data-i18n-aria-label="aria_closeMenu">×</button>{nav}<a href="{route(lang,'quote')}" data-i18n="navQuote"></a></div><main id="mainContent">{body}</main><footer class="wrap"><span>© 2026 ARH Digital.</span><a href="{route(lang,'quote')}" data-i18n="navQuote"></a><span data-i18n="prototypeBanner"></span></footer><script src="/assets/{page}-prototype-locales.js"></script><script src="/assets/i18n.js"></script><script src="/assets/contact-form.js"></script><script src="/assets/prototype.js"></script></body></html>'''
            soup = node(html)
            soup.select_one('footer').insert_before(node(studio_spark()))
            for el in soup.select('[data-i18n]'):
                el.clear()
                fragment = node(strings[lang][el['data-i18n']])
                for child in list(fragment.contents):el.append(child)
            for attr in ['placeholder','aria-label','title','content']:
                for el in soup.select(f'[data-i18n-{attr}]'):el[attr]=strings[lang][el[f'data-i18n-{attr}']]
            soup.title.string = strings[lang]['pageTitle']
            for el in soup.select('[href]'):
                href = el['href']
                if el.has_attr('data-plan'):
                    el['href']=route(lang,'quote')+'?plan='+el['data-plan']
                elif href.startswith('#'):
                    # Section anchors from production become intentional journeys.
                    if href=='#contact': el['href']=route(lang,'quote')
                elif href.startswith('/') and not href.startswith('/assets/') and href!='/favicon.svg':
                    if 'data-plan' in el.attrs:
                        el['href']=route(lang,'quote')+'?plan='+el['data-plan']
                    elif href in ['/', '/index.html'] or re.fullmatch(r'/(services|packages|works|about|quote)\.html',href):
                        target = 'home' if href in ['/','/index.html'] else href[1:-5]
                        el['href']=route(lang,target)
            for el in soup.select('.reveal'):el['class']=[x for x in el['class'] if x!='reveal']
            fallback = soup.new_tag('noscript')
            fallback.append(node('<nav class="fallback-languages">'+' · '.join(f'<a href="{route(l,page)}" lang="{l}">{label}</a>' for l,label in [('en','English'),('ar','العربية'),('fr','Français'),('hi','हिन्दी')])+'</nav>'))
            soup.body.insert(0,fallback)
            destination = ROOT / (route(lang,page).lstrip('/') or 'index.html')
            if destination.suffix != '.html':destination=destination/'index.html'
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(str(soup)+'\n')
    (ROOT/'robots.txt').write_text('User-agent: *\nDisallow: /\n')
    (ROOT/'sitemap.xml').unlink(missing_ok=True)
    (ROOT/'CNAME').unlink(missing_ok=True)
    print('Built 24 private prototype pages; no live form endpoint, domain binding or sitemap.')

if __name__ == '__main__':main()
