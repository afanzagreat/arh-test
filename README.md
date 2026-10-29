# ARH Digital V2

A public review build for ARH Digital, made in the separate `arh-test` repository. The existing GitHub Pages setup serves the `main` branch at **https://afanzagreat.github.io/arh-test/**. No Pages settings were changed, no Cloudflare configuration was added, and the production `Arh` repository was not modified.

## What is here

Six separately composed pages: Home, Services, Packages, Work, About, and Start a project. Each is available in English, Arabic (RTL), French, and Hindi. Language switching preserves the current page, query string, and fragment. The Work page uses the existing Shabibi Juice project assets and copy rather than invented clients or performance claims.

The site is light-first, with a complete optional dark theme, a compact A-to-R-to-H first-visit intro, restrained GSAP page reveals, native browser page transitions where supported, and a reduced-motion fallback. Local font files are provided for Latin, Arabic, and Devanagari text.

## Preview and safety

The Pages URL and this repository are public. All 24 V2-generated routes use `noindex`; this is **not access control**. The V2 build replaces `robots.txt` with `Disallow: /` and removes the upstream production `sitemap.xml` and any `CNAME`, so the review build is not advertised as a production target. The unlinked localized privacy pages inherited from the upstream test copy remain unchanged and retain their original tracking and metadata; they are not generated or linked by V2.

The V2 project-brief form has no endpoint: it validates and renders a review in the current browser only, sends no request, and stores nothing. Each generated V2 page has a Content Security Policy that blocks form submission, network connections, frames, and embedded objects. If JavaScript is unavailable, the submit button remains disabled.

GitHub Pages is already enabled on `main`, so a push to this repository updates the review site. No deployment workflow or custom domain was added. Do not configure hosting, a custom domain, or production changes from this repository without separate approval.

## Run locally

```sh
npm install
python3 -m pip install -r tools/requirements.txt
npm run build
python3 -m http.server 8765 --bind 127.0.0.1
```

Open `http://127.0.0.1:8765/`. The builder copies GSAP and the self-hosted fonts from `node_modules` into `assets/`, then generates the 24 HTML routes and locale bundles. The shared `<base>` setup supports both root hosting and the `/arh-test/` GitHub Pages path.

## Tests

With Chromium available, keep the local server running and run:

```sh
npm test
```

The suite covers language-runtime cases, conditional form behavior, package selection, all 24 page/language routes at phone and desktop widths, the local-only quote journey, language switching, mobile navigation, and absence of form POSTs. To verify the project Pages prefix too, serve the parent directory and run the browser suite with `PROTOTYPE_URL=http://127.0.0.1:8766/arh-test`.

## Source and assets

Page generation lives in `tools/build_prototype.py`; custom copy lives in `assets/v2-copy.json`; the V2 visual system is `tools/prototype-templates/base-v2.css`; interactions are in `assets/prototype.js`. Generated HTML and `*-prototype-locales.js` files are rebuild outputs. Font license files are included in `assets/fonts/`; GSAP's bundled version and license are identified in `assets/vendor/gsap.min.js`.
