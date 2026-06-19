/* =========================================================
   H# Guide page — TOC active state + scroll progress
   Runs alongside main.js (which handles fade-up for guide too)
   ========================================================= */
(() => {
  'use strict';

  const gsap = window.gsap;
  const ScrollTrigger = window.ScrollTrigger;
  if (!gsap || !ScrollTrigger) return;
  gsap.registerPlugin(ScrollTrigger);

  const tocLinks = Array.from(document.querySelectorAll('[data-toc-link]'));
  const sections = tocLinks
    .map((a) => document.querySelector(a.getAttribute('href')))
    .filter(Boolean);
  const progressBar = document.querySelector('[data-guide-progress]');

  if (sections.length === 0) return;

  // 1. TOC active link — highlight the section currently in view
  sections.forEach((sec) => {
    ScrollTrigger.create({
      trigger: sec,
      start: 'top 35%',
      end: 'bottom 35%',
      onToggle: (self) => {
        if (!self.isActive) return;
        const id = '#' + sec.id;
        tocLinks.forEach((a) => a.classList.toggle('active', a.getAttribute('href') === id));
      },
    });
  });

  // 2. Top progress bar — reflects scroll position within the guide body
  const body = document.querySelector('.guide-body');
  if (body && progressBar) {
    ScrollTrigger.create({
      trigger: body,
      start: 'top top',
      end: 'bottom bottom',
      onUpdate: (self) => {
        progressBar.style.width = (self.progress * 100).toFixed(2) + '%';
      },
    });
  }

  // 3. Code blocks — soft fade-in when each block enters
  gsap.utils.toArray('.guide-code-block, .guide-callout, .guide-table, .guide-list, .guide-steps').forEach((el) => {
    gsap.fromTo(
      el,
      { opacity: 0, y: 14 },
      {
        opacity: 1,
        y: 0,
        duration: 0.7,
        ease: 'power3.out',
        overwrite: 'auto',
        scrollTrigger: {
          trigger: el,
          start: 'top 90%',
          once: true,
        },
        onComplete: () => gsap.set(el, { clearProps: 'opacity,transform' }),
      }
    );
  });
})();
