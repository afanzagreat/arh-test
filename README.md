# ARH test prototype

Private, undeployed prototype based on `afanzagreat/Arh` production commit `cacededc640a7ff6181c9d9d2ee57e55c67ce2d8` (latest `main` when copied). Production was not modified. This repository retains the source history, production design system, original approved package copy, and existing Shabibi image assets.

## What to try

Six focused pages: Home, Services, Packages, Work, About, and Get a Quote. Each has a static English, Arabic, French, and Hindi version (24 routes). Language switching keeps the current page and query string; Arabic uses RTL layout. The quote journey carries a selected package across pages, conditionally requires the existing-site URL for redesigns, and shows a local review of the brief.

- Essential: **$26/month** or **$99 one-time**.
- Pro: **$40/month** or **$209 one-time**.
- Custom: **inquiry-only**, no numeric price.

The Work page uses the existing Shabibi project, not invented clients or performance results. About describes the studio's approach without inventing a team biography.

## Safety boundary

Nothing is deployed or published. There is no `CNAME`, deployment workflow, or sitemap. Generated pages have `noindex,nofollow,noarchive`, and `robots.txt` disallows crawling. These are defense in depth, not access control; repository privacy is the actual boundary.

The prototype quote form has no live endpoint or access key. It validates and renders a brief **only in the browser**, makes no POST request, and does not store the brief. CSP additionally blocks form actions, network connections, and frames. External Google Fonts and a deliberate link to the existing Shabibi website remain; the case-study image is local. Without JavaScript the review button stays disabled. Do not enable Pages or attach a hosting service without separate approval.

## Run locally

```sh
python3 -m http.server 8765 --bind 127.0.0.1
# Open http://127.0.0.1:8765/ on the same computer.
```

## Edit and rebuild

```sh
python3 -m pip install -r tools/requirements.txt
python3 tools/build_prototype.py
```

Layout assembly is in `tools/build_prototype.py`; new copy is in `assets/prototype-copy.json`; layout additions and interactions are in `assets/prototype.css` and `assets/prototype.js`. Production section templates are preserved in `tools/prototype-templates/`. Generated `*-prototype-locales.js` and HTML files are rebuilt, not edited directly. Original home/works catalogs supply the established translated package terms.

The inherited `tools/build_seo.py`, `tools/test_seo.py`, `tools/test_requested_changes.py`, and `SEO-REVIEW.md` describe historical production architecture, not this prototype. Do not run the production SEO builder here: it would recreate production-domain metadata. Use the prototype builder instead.

## Regression tests

```sh
npm install
npx playwright install chromium
# Keep the loopback server running in another terminal.
npm test
```

For an already installed Chromium, set `CHROMIUM_PATH=/path/to/chromium`. Browser tests cover 24 routes at mobile and desktop widths, package selection, all four local-only quote flows, language/page preservation, and mobile navigation. Unit tests also cover the preserved redesign-field behavior and language runtime.
