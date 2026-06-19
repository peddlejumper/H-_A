/* =========================================================
   H# Pricing page — billing toggle + FAQ enhancements
   ========================================================= */
(() => {
  'use strict';

  const gsap = window.gsap;
  const ScrollTrigger = window.ScrollTrigger;
  if (!gsap || !ScrollTrigger) return;
  gsap.registerPlugin(ScrollTrigger);

  // 1. Billing toggle (monthly / yearly)
  const toggleBtns = Array.from(document.querySelectorAll('.pricing-toggle-btn'));
  const amounts = Array.from(document.querySelectorAll('[data-price]'));
  const periods = Array.from(document.querySelectorAll('[data-period]'));

  function applyBilling(mode) {
    amounts.forEach((el) => {
      const v = el.dataset[mode];
      if (v == null) return;
      el.textContent = '¥' + v;
    });
    periods.forEach((el) => {
      el.textContent = mode === 'yearly' ? '/ 月（年付）' : '/ 月';
    });
  }

  toggleBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      toggleBtns.forEach((b) => {
        b.classList.toggle('is-active', b === btn);
        b.setAttribute('aria-selected', b === btn ? 'true' : 'false');
      });
      applyBilling(btn.dataset.billing);
    });
  });

  // 2. Tier card stagger
  gsap.utils.toArray('.pricing-tier').forEach((card, i) => {
    gsap.fromTo(
      card,
      { opacity: 0, y: 28 },
      {
        opacity: 1,
        y: 0,
        duration: 0.8,
        ease: 'power3.out',
        delay: i * 0.1,
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

  // 3. FAQ items — soft entrance + animated caret handled by CSS
  gsap.utils.toArray('.faq-item').forEach((item, i) => {
    gsap.fromTo(
      item,
      { opacity: 0, y: 14 },
      {
        opacity: 1,
        y: 0,
        duration: 0.6,
        ease: 'power2.out',
        delay: i * 0.05,
        overwrite: 'auto',
        scrollTrigger: {
          trigger: item,
          start: 'top 92%',
          once: true,
        },
        onComplete: () => gsap.set(item, { clearProps: 'opacity,transform' }),
      }
    );
  });

  // 4. Comparison table — row stagger
  gsap.utils.toArray('.compare-table tbody tr').forEach((row, i) => {
    gsap.fromTo(
      row,
      { opacity: 0, y: 8 },
      {
        opacity: 1,
        y: 0,
        duration: 0.5,
        ease: 'power2.out',
        delay: i * 0.04,
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
})();
