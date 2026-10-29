(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const all = (selector, root = document) => [...root.querySelectorAll(selector)];
  const root = document.documentElement;
  const gsap = window.gsap;
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const getText = key => window.ARHI18n?.t(key) || key;

  // The small-screen menu remains ordinary links. The drawer only changes visibility and focus.
  const menu = $('#mobileNav');
  const menuButton = $('#menuBtn');
  const closeButton = $('#closeMenu');
  const header = $('.site-header');
  const main = $('#mainContent');
  const footer = $('.site-footer');
  if (menu && menuButton && closeButton) {
    const menuItems = () => all('a, button', menu);
    function closeMenu(restoreFocus = true) {
      const wasOpen = menu.classList.contains('open');
      menu.classList.remove('open');
      menu.setAttribute('aria-hidden', 'true');
      menu.inert = true;
      menuButton.setAttribute('aria-expanded', 'false');
      if (header) header.inert = false;
      if (main) main.inert = false;
      if (footer) footer.inert = false;
      if (restoreFocus && wasOpen) menuButton.focus();
    }
    function openMenu() {
      menu.classList.add('open');
      menu.setAttribute('aria-hidden', 'false');
      menu.inert = false;
      menuButton.setAttribute('aria-expanded', 'true');
      if (header) header.inert = true;
      if (main) main.inert = true;
      if (footer) footer.inert = true;
      menu.querySelector('a')?.focus();
    }
    menuButton.addEventListener('click', () => menu.classList.contains('open') ? closeMenu() : openMenu());
    closeButton.addEventListener('click', () => closeMenu());
    menu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => closeMenu(false)));
    document.addEventListener('keydown', event => {
      if (!menu.classList.contains('open')) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        closeMenu();
        return;
      }
      if (event.key === 'Tab') {
        const items = menuItems();
        const first = items[0];
        const last = items.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    });
    window.matchMedia('(min-width: 981px)').addEventListener?.('change', event => {
      if (event.matches) closeMenu(false);
    });
  }

  // Persist theme before paint in the generated HTML, then keep the semantic state in one place.
  const themeButton = $('#themeBtn');
  function updateThemeControl() {
    if (!themeButton) return;
    const dark = root.dataset.theme === 'dark';
    themeButton.setAttribute('aria-pressed', String(dark));
    themeButton.setAttribute('aria-label', getText(dark ? 'themeToLight' : 'themeToDark'));
    const glyph = $('.theme-glyph', themeButton);
    if (glyph) glyph.textContent = dark ? '◑' : '◐';
  }
  function applyTheme(theme) {
    root.dataset.theme = theme;
    try { localStorage.setItem('arh-test-theme', theme); } catch (_) { /* Storage can be unavailable. */ }
    updateThemeControl();
  }
  if (themeButton) {
    updateThemeControl();
    let switching = false;
    themeButton.addEventListener('click', async event => {
      if (switching) return;
      const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
      if (reduceMotion || typeof document.startViewTransition !== 'function') {
        applyTheme(next);
        return;
      }
      const width = window.innerWidth;
      const height = window.innerHeight;
      const x = Math.min(width, Math.max(0, Number.isFinite(event.clientX) ? event.clientX : width / 2));
      const y = Math.min(height, Math.max(0, Number.isFinite(event.clientY) ? event.clientY : height / 2));
      const radius = Math.ceil(Math.hypot(Math.max(x, width - x), Math.max(y, height - y)) + 2);
      root.style.setProperty('--theme-x', `${Math.round(x)}px`);
      root.style.setProperty('--theme-y', `${Math.round(y)}px`);
      root.style.setProperty('--theme-radius', `${radius}px`);
      root.dataset.themeReveal = 'true';
      switching = true;
      themeButton.disabled = true;
      try {
        const transition = document.startViewTransition(() => applyTheme(next));
        await transition.finished;
      } catch (_) {
        // The theme update is already committed; unsupported or interrupted animation never rolls it back.
      } finally {
        delete root.dataset.themeReveal;
        themeButton.disabled = false;
        switching = false;
      }
    });
    window.addEventListener('arh:languagechange', updateThemeControl);
  }

  // Pricing switches preserve normal form values; plan links also prefill the corresponding quote choice.
  const modeButtons = all('[data-mode]');
  modeButtons.forEach(button => {
    button.setAttribute('aria-pressed', String(button.classList.contains('active')));
    button.addEventListener('click', () => {
      const once = button.dataset.mode === 'once';
      const monthly = $('#monthlyPlans');
      const oneTime = $('#oncePlans');
      if (monthly) monthly.hidden = once;
      if (oneTime) oneTime.hidden = !once;
      modeButtons.forEach(item => {
        const active = item === button;
        item.classList.toggle('active', active);
        item.setAttribute('aria-pressed', String(active));
      });
    });
  });

  // One-open-at-a-time FAQ, with a small height reveal and an instant no-GSAP fallback.
  all('.faq-q').forEach((button, index) => {
    const item = button.closest('.faq-item');
    const answer = item?.querySelector('.faq-a');
    if (!answer) return;
    if (!answer.id) answer.id = `faq-answer-${index + 1}`;
    button.setAttribute('aria-controls', answer.id);
    button.setAttribute('aria-expanded', 'false');
    answer.hidden = true;
    button.addEventListener('click', () => {
      const open = !item.classList.contains('open');
      all('.faq-item.open').forEach(other => {
        if (other === item) return;
        const otherButton = other.querySelector('.faq-q');
        const otherAnswer = other.querySelector('.faq-a');
        other.classList.remove('open');
        otherButton?.setAttribute('aria-expanded', 'false');
        if (gsap && !reduceMotion) {
          gsap.to(otherAnswer, { height: 0, opacity: 0, duration: 0.22, ease: 'power2.out', onComplete: () => { otherAnswer.hidden = true; } });
        } else {
          otherAnswer.hidden = true;
        }
      });
      item.classList.toggle('open', open);
      button.setAttribute('aria-expanded', String(open));
      if (open) {
        answer.hidden = false;
        if (gsap && !reduceMotion) {
          gsap.fromTo(answer, { height: 0, opacity: 0 }, { height: 'auto', opacity: 1, duration: 0.3, ease: 'power2.out' });
        } else {
          answer.style.height = 'auto';
          answer.style.opacity = '1';
        }
      } else if (gsap && !reduceMotion) {
        gsap.to(answer, { height: 0, opacity: 0, duration: 0.22, ease: 'power2.out', onComplete: () => { answer.hidden = true; } });
      } else {
        answer.hidden = true;
      }
    });
  });

  // This review form is intentionally local-only: valid entries are rendered as text and never sent or stored.
  const form = $('#contactForm');
  if (form) {
    const planSelect = $('#budget');
    const requestedPlan = new URLSearchParams(window.location.search).get('plan');
    if (planSelect && [...planSelect.options].some(option => option.value === requestedPlan)) {
      planSelect.value = requestedPlan;
    }
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = false;
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const details = $('#briefDetails');
      const review = $('#briefReview');
      const message = $('#formMsg');
      if (!details || !review || !message) return;
      details.replaceChildren();
      for (const id of ['name', 'email', 'projectType', 'budget', 'existingWebsite', 'promoCode', 'message']) {
        const input = $('#' + id);
        if (!input || input.disabled || !String(input.value).trim()) continue;
        const label = form.querySelector(`label[for="${id}"]`);
        const term = document.createElement('dt');
        const definition = document.createElement('dd');
        term.textContent = label?.textContent || id;
        definition.textContent = input.tagName === 'SELECT' ? input.selectedOptions[0].textContent : input.value;
        details.append(term, definition);
      }
      message.textContent = getText('quoteSuccess');
      review.hidden = false;
      review.focus();
    });
    const clearReview = () => {
      const review = $('#briefReview');
      const message = $('#formMsg');
      if (review) review.hidden = true;
      if (message) message.textContent = '';
    };
    form.addEventListener('input', clearReview);
    form.addEventListener('change', clearReview);
  }

  // Bounded entrance/scroll reveals; content stays visible if GSAP or the observer is unavailable.
  if (gsap) {
    const media = gsap.matchMedia();
    media.add('(prefers-reduced-motion: no-preference)', () => {
      const intro = all('[data-intro]');
      if (intro.length) {
        gsap.fromTo(intro, { autoAlpha: 0, y: 18 }, {
          autoAlpha: 1, y: 0, duration: 0.62, stagger: 0.08, ease: 'power3.out', clearProps: 'all'
        });
      }
      const revealTargets = all('[data-reveal]');
      if (!('IntersectionObserver' in window)) {
        if (revealTargets.length) gsap.fromTo(revealTargets, { autoAlpha: 0, y: 14 }, {
          autoAlpha: 1, y: 0, duration: 0.58, stagger: 0.06, ease: 'power3.out', clearProps: 'all'
        });
        return;
      }
      const observer = new IntersectionObserver(entries => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          observer.unobserve(entry.target);
          gsap.fromTo(entry.target, { autoAlpha: 0, y: 16 }, {
            autoAlpha: 1, y: 0, duration: 0.58, ease: 'power3.out', clearProps: 'all'
          });
        }
      }, { threshold: 0.12, rootMargin: '0px 0px -48px 0px' });
      revealTargets.forEach(target => observer.observe(target));
      return () => observer.disconnect();
    });
  }

  // One short first-visit brand reveal on the home route. It is not a progress indicator.
  const loader = $('#siteLoader');
  const loaderGlyph = $('#loaderGlyph');
  const skipLoader = $('#loaderSkip');
  if (loader && loaderGlyph && skipLoader && root.dataset.pageKind === 'home' && gsap && !reduceMotion) {
    let alreadySeen = false;
    try { alreadySeen = sessionStorage.getItem('arh-test-loader-seen') === '1'; } catch (_) {}
    if (!alreadySeen) {
      try { sessionStorage.setItem('arh-test-loader-seen', '1'); } catch (_) {}
      const previousFocus = document.activeElement;
      loader.hidden = false;
      loader.setAttribute('aria-hidden', 'false');
      loader.setAttribute('aria-modal', 'true');
      if (header) header.inert = true;
      if (main) main.inert = true;
      if (footer) footer.inert = true;
      skipLoader.focus({ preventScroll: true });
      const counter = { value: 0 };
      let finished = false;
      const finish = () => {
        if (finished) return;
        finished = true;
        timeline.kill();
        loaderGlyph.textContent = 'H';
        loader.setAttribute('aria-hidden', 'true');
        loader.removeAttribute('aria-modal');
        loader.hidden = true;
        if (header) header.inert = false;
        if (main) main.inert = false;
        if (footer) footer.inert = false;
        if (loader.contains(document.activeElement)) {
          if (previousFocus && previousFocus !== document.body && previousFocus.isConnected && typeof previousFocus.focus === 'function') {
            previousFocus.focus({ preventScroll: true });
          } else {
            main?.focus({ preventScroll: true });
          }
        }
        skipLoader.removeEventListener('click', finish);
      };
      const timeline = gsap.timeline({ onComplete: finish, defaults: { ease: 'power2.out' } });
      skipLoader.addEventListener('click', finish);
      timeline.to(counter, { value: 28, duration: 0.32, ease: 'none', onUpdate: () => { loaderGlyph.textContent = String(Math.floor(counter.value)).padStart(2, '0'); } })
        .call(() => { loaderGlyph.textContent = 'A'; })
        .to(loaderGlyph, { y: -5, duration: 0.09, ease: 'power2.out' })
        .call(() => { loaderGlyph.textContent = 'R'; })
        .to(loaderGlyph, { y: 0, duration: 0.09, ease: 'power2.inOut' })
        .call(() => { loaderGlyph.textContent = 'H'; })
        .to(loader, { autoAlpha: 0, duration: 0.16, ease: 'power1.out' });
    }
  }
})();
