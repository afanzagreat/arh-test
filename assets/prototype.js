(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const all = s => [...document.querySelectorAll(s)];
  const menu = $('#mobileNav');
  const menuBtn = $('#menuBtn');
  function closeMenu() {
    menu.classList.remove('open');
    menu.setAttribute('aria-hidden', 'true');
    menuBtn.setAttribute('aria-expanded', 'false');
    menuBtn.focus();
  }
  menuBtn.addEventListener('click', () => {
    const open = !menu.classList.contains('open');
    menu.classList.toggle('open', open);
    menu.setAttribute('aria-hidden', String(!open));
    menuBtn.setAttribute('aria-expanded', String(open));
    if (open) menu.querySelector('a').focus();
  });
  $('#closeMenu').addEventListener('click', closeMenu);
  document.addEventListener('keydown', e => {
    if (!menu.classList.contains('open')) return;
    if (e.key === 'Escape') closeMenu();
    if (e.key === 'Tab') {
      const items = [...menu.querySelectorAll('a,button')];
      const first = items[0], last = items.at(-1);
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });
  const theme = $('#themeBtn');
  try { document.documentElement.dataset.theme = localStorage.getItem('arh-test-theme') || ''; } catch (_) {}
  theme.addEventListener('click', () => {
    const value = document.documentElement.dataset.theme === 'dark' ? '' : 'dark';
    document.documentElement.dataset.theme = value;
    try { localStorage.setItem('arh-test-theme', value); } catch (_) {}
  });
  all('[data-mode]').forEach(button => {
    button.setAttribute('aria-pressed', String(button.classList.contains('active')));
    button.addEventListener('click', () => {
      const once = button.dataset.mode === 'once';
      $('#monthlyPlans').hidden = once;
      $('#oncePlans').hidden = !once;
      all('[data-mode]').forEach(b => {
        b.classList.toggle('active', b === button);
        b.setAttribute('aria-pressed', String(b === button));
      });
    });
  });
  all('.faq-q').forEach(button => {
    button.setAttribute('aria-expanded', 'false');
    button.addEventListener('click', () => {
      const item = button.closest('.faq-item');
      const open = !item.classList.contains('open');
      all('.faq-item').forEach(el => {
        el.classList.remove('open');
        el.querySelector('.faq-q').setAttribute('aria-expanded', 'false');
      });
      item.classList.toggle('open', open);
      button.setAttribute('aria-expanded', String(open));
    });
  });
  const form = $('#contactForm');
  if (!form) return;
  const plan = $('#budget');
  const requested = new URLSearchParams(location.search).get('plan');
  if ([...plan.options].some(option => option.value === requested)) plan.value = requested;
  form.querySelector('button[type="submit"]').disabled = false;
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const details = $('#briefDetails');
    details.replaceChildren();
    for (const id of ['name', 'email', 'projectType', 'budget', 'existingWebsite', 'promoCode', 'message']) {
      const input = $('#' + id);
      if (input.disabled || !input.value.trim()) continue;
      const dt = document.createElement('dt');
      const dd = document.createElement('dd');
      dt.textContent = form.querySelector('label[for="' + id + '"]').textContent;
      dd.textContent = input.tagName === 'SELECT' ? input.selectedOptions[0].textContent : input.value;
      details.append(dt, dd);
    }
    $('#formMsg').textContent = window.ARHI18n.t('quoteSuccess');
    $('#briefReview').hidden = false;
    $('#briefReview').focus();
  });
  form.addEventListener('input', () => { $('#briefReview').hidden = true; $('#formMsg').textContent = ''; });
  form.addEventListener('change', () => { $('#briefReview').hidden = true; $('#formMsg').textContent = ''; });
})();
