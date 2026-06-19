/* =========================================================
   H# Download page — platform tab switching + animations
   ========================================================= */
(() => {
  'use strict';

  const gsap = window.gsap;
  const ScrollTrigger = window.ScrollTrigger;
  if (!gsap || !ScrollTrigger) return;
  gsap.registerPlugin(ScrollTrigger);

  // 1. Platform tabs — show only matching rows
  const tabs = Array.from(document.querySelectorAll('.dl-tab'));
  const groups = Array.from(document.querySelectorAll('[data-platform-group]'));

  function applyPlatform(p) {
    tabs.forEach((t) => {
      const active = t.dataset.platform === p;
      t.classList.toggle('is-active', active);
      t.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    groups.forEach((g) => {
      const match = g.dataset.platformGroup === p;
      if (match) g.removeAttribute('hidden');
      else g.setAttribute('hidden', '');
    });
  }

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => applyPlatform(tab.dataset.platform));
  });

  // 2. Product card stagger
  gsap.utils.toArray('.dl-product').forEach((card, i) => {
    gsap.fromTo(
      card,
      { opacity: 0, y: 28 },
      {
        opacity: 1,
        y: 0,
        duration: 0.8,
        ease: 'power3.out',
        delay: i * 0.12,
        overwrite: 'auto',
        scrollTrigger: {
          trigger: card,
          start: 'top 88%',
          once: true,
        },
        onComplete: () => gsap.set(card, { clearProps: 'opacity,transform' }),
      }
    );
  });

  // 3. Version table rows — soft stagger
  gsap.utils.toArray('.dl-version-table tbody tr').forEach((row, i) => {
    gsap.fromTo(
      row,
      { opacity: 0, y: 8 },
      {
        opacity: 1,
        y: 0,
        duration: 0.5,
        ease: 'power2.out',
        delay: i * 0.05,
        overwrite: 'auto',
        scrollTrigger: {
          trigger: row,
          start: 'top 95%',
          once: true,
        },
        onComplete: () => gsap.set(row, { clearProps: 'opacity,transform' }),
      }
    );
  });

  // 4. Other channels panel + install guide
  gsap.utils.toArray('.dl-other, .dl-install').forEach((el, i) => {
    gsap.fromTo(
      el,
      { opacity: 0, y: 14 },
      {
        opacity: 1,
        y: 0,
        duration: 0.6,
        ease: 'power2.out',
        delay: i * 0.08,
        overwrite: 'auto',
        scrollTrigger: {
          trigger: el,
          start: 'top 92%',
          once: true,
        },
        onComplete: () => gsap.set(el, { clearProps: 'opacity,transform' }),
      }
    );
  });
})();
