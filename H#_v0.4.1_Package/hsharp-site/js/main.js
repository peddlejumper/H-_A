/* =========================================================
   H# Official Site — Robust Animation Engine
   All state managed by GSAP (no CSS class flicker)
   ========================================================= */

(() => {
  'use strict';

  const gsap = window.gsap;
  const ScrollTrigger = window.ScrollTrigger;

  if (!gsap || !ScrollTrigger) {
    console.warn('GSAP not loaded — animations disabled');
    return;
  }
  gsap.registerPlugin(ScrollTrigger);
  gsap.config({ nullTargetWarn: false });

  const prefersReduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ====================================================
     1. Build time
     ==================================================== */
  const buildEl = document.getElementById('build-time');
  if (buildEl) {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    buildEl.textContent = `build · ${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())}`;
  }

  /* ====================================================
     2. Header scroll state
     ==================================================== */
  const header = document.getElementById('header');
  if (header) {
    const updateHeader = () => {
      if (window.scrollY > 8) header.classList.add('scrolled');
      else header.classList.remove('scrolled');
    };
    updateHeader();
    window.addEventListener('scroll', updateHeader, { passive: true });
  }

  /* ====================================================
     3. Unified fade-up animation
        - Initial state set by GSAP (no CSS class)
        - Hero elements animate on load via timeline
        - Non-hero elements animate on scroll via ScrollTrigger
        - overwrite:'auto' prevents double-trigger flicker
     ==================================================== */
  const allFade = Array.from(document.querySelectorAll('.fade-up'));
  const heroFade = allFade.filter((el) => el.closest('.hero'));
  const scrollFade = allFade.filter(
    (el) => !el.closest('.hero') && !el.closest('.hscroll')
  );
  // hscroll cards stay visible inside the pin (revealed explicitly)
  const hscrollCards = Array.from(document.querySelectorAll('.hscroll-card'));

  // Mark which elements are handled by hscroll (so they don't get fade-up)
  if (hscrollCards.length > 0) {
    hscrollCards.forEach((c) => c.classList.remove('fade-up'));
  }

  if (prefersReduced) {
    // Skip all motion: ensure visible, return
    gsap.set(allFade, { opacity: 1, y: 0, clearProps: 'opacity,transform' });
    return;
  }

  // Set initial state for ALL fade-up elements (hero + scroll)
  // This is synchronous so there's no flash of unstyled content
  gsap.set(heroFade, { opacity: 0, y: 24 });
  gsap.set(scrollFade, { opacity: 0, y: 24 });
  gsap.set(hscrollCards, { opacity: 0, y: 24 });

  // HERO — single timeline, all on load
  if (heroFade.length > 0) {
    const heroTl = gsap.timeline({
      delay: 0.05,
      onComplete: () => {
        // Clear inline styles once done so elements behave normally
        heroFade.forEach((el) => gsap.set(el, { clearProps: 'opacity,transform' }));
      },
    });
    heroFade.forEach((el, i) => {
      heroTl.to(
        el,
        {
          opacity: 1,
          y: 0,
          duration: 0.9,
          ease: 'power3.out',
          overwrite: 'auto',
        },
        i === 0 ? 0 : '-=0.55'
      );
    });
  }

  // SCROLL — one ScrollTrigger per element, once: true
  scrollFade.forEach((el) => {
    ScrollTrigger.create({
      trigger: el,
      start: 'top 92%',
      once: true,
      animation: gsap.to(el, {
        opacity: 1,
        y: 0,
        duration: 0.9,
        ease: 'power3.out',
        overwrite: 'auto',
        onComplete: () => gsap.set(el, { clearProps: 'opacity,transform' }),
      }),
    });
  });

  // HSCROLL cards — revealed by the second block below once the
  // horizontal-scroll containerAnimation is built (avoids premature triggers
  // and the lag they cause).

  /* ====================================================
     4. Horizontal GSAP scroll for feature cards
     ==================================================== */
  const hscrollSection = document.querySelector('#hscroll');
  let hscrollST = null;
  if (hscrollSection && matchMedia('(min-width: 769px)').matches) {
    const track = hscrollSection.querySelector('[data-hscroll-track]');
    const counter = hscrollSection.querySelector('[data-hscroll-counter]');
    const progress = hscrollSection.querySelector('[data-hscroll-progress]');
    const cards = hscrollSection.querySelectorAll('.hscroll-card');
    const total = cards.length;

    if (track && cards.length > 0) {
      const getDistance = () => Math.max(0, track.scrollWidth - window.innerWidth);

      const setHeight = () => {
        const dist = getDistance();
        const heightPx = Math.max(window.innerHeight, dist * 2.5);
        hscrollSection.style.height = heightPx + 'px';
        return dist;
      };
      setHeight();

      // Wait one frame so scrollHeight is accurate (fonts, layout)
      requestAnimationFrame(() => {
        setHeight();
        ScrollTrigger.refresh();
      });

      hscrollST = gsap.to(track, {
        x: () => -getDistance(),
        ease: 'none',
        scrollTrigger: {
          trigger: hscrollSection,
          start: 'top top',
          end: 'bottom bottom',
          scrub: 0.4,
          invalidateOnRefresh: true,
          onUpdate: (self) => {
            const p = self.progress;
            if (progress) progress.style.width = (p * 100) + '%';
            if (counter) {
              const idx = Math.min(total, Math.max(1, Math.ceil(p * total) || 1));
              const cur = String(idx).padStart(2, '0');
              const tot = String(total).padStart(2, '0');
              counter.innerHTML = `<span class="current">${cur}</span> / ${tot}`;
            }
          },
        },
      });

      let hscrollResizeT;
      window.addEventListener('resize', () => {
        clearTimeout(hscrollResizeT);
        hscrollResizeT = setTimeout(() => {
          setHeight();
          ScrollTrigger.refresh();
        }, 200);
      });
    }
  }

  // Re-link hscroll card ScrollTriggers to use the hscroll's containerAnimation
  // so they trigger when cards enter the viewport horizontally.
  if (hscrollST && hscrollCards.length > 0) {
    hscrollCards.forEach((c, i) => {
      ScrollTrigger.create({
        trigger: c,
        containerAnimation: hscrollST,
        start: 'left 85%',
        once: true,
        animation: gsap.to(c, {
          opacity: 1,
          y: 0,
          duration: 0.7,
          ease: 'power3.out',
          overwrite: 'auto',
          delay: i * 0.08,
          onComplete: () => gsap.set(c, { clearProps: 'opacity,transform' }),
        }),
      });
    });
  } else if (hscrollCards.length > 0) {
    // Mobile fallback: hscroll is disabled, just reveal cards when they enter.
    hscrollCards.forEach((c) =>
      ScrollTrigger.create({
        trigger: c,
        start: 'top 90%',
        once: true,
        animation: gsap.to(c, {
          opacity: 1,
          y: 0,
          duration: 0.6,
          ease: 'power2.out',
          overwrite: 'auto',
          onComplete: () => gsap.set(c, { clearProps: 'opacity,transform' }),
        }),
      })
    );
  }

  /* ====================================================
     4.5. ZZW Code — IDE mockup + chat stagger + cap cards
     ==================================================== */
  const zzwSection = document.getElementById('zzw');
  if (zzwSection) {
    // Capability cards — keep their existing fade-up but enhance with a
    // stronger stagger once the grid enters the viewport
    const capCards = Array.from(zzwSection.querySelectorAll('.zzw-cap-card'));
    if (capCards.length > 0) {
      ScrollTrigger.create({
        trigger: zzwSection.querySelector('.zzw-cap-grid'),
        start: 'top 85%',
        once: true,
        animation: gsap.fromTo(
          capCards,
          { opacity: 0, y: 28 },
          {
            opacity: 1,
            y: 0,
            duration: 0.8,
            ease: 'power3.out',
            stagger: 0.08,
            overwrite: 'auto',
            onComplete: () => {
              capCards.forEach((c) => gsap.set(c, { clearProps: 'opacity,transform' }));
            },
          }
        ),
      });
    }

    // AI chat messages — reveal sequentially as the IDE mockup enters
    const chatMsgs = Array.from(zzwSection.querySelectorAll('.zzw-chat .zzw-msg'));
    if (chatMsgs.length > 0) {
      gsap.set(chatMsgs, { opacity: 0, x: 0, y: 10 });
      ScrollTrigger.create({
        trigger: zzwSection.querySelector('.zzw-ide'),
        start: 'top 80%',
        once: true,
        animation: gsap.to(chatMsgs, {
          opacity: 1,
          y: 0,
          duration: 0.55,
          ease: 'power2.out',
          stagger: 0.18,
          overwrite: 'auto',
          onComplete: () => {
            chatMsgs.forEach((m) => gsap.set(m, { clearProps: 'opacity,transform' }));
          },
        }),
      });
    }

    // IDE entrance: subtle scale + lift when first scrolled in
    const zzwIde = zzwSection.querySelector('.zzw-ide');
    if (zzwIde) {
      // We want it to keep its fade-up behavior from the allFade list,
      // but add a small extra motion: the three panes fly in from sides.
      const zzwPanes = zzwSection.querySelectorAll('.zzw-files, .zzw-editor, .zzw-chat');
      gsap.set(zzwPanes, { opacity: 0, y: 16 });
      ScrollTrigger.create({
        trigger: zzwIde,
        start: 'top 85%',
        once: true,
        animation: gsap.to(zzwPanes, {
          opacity: 1,
          y: 0,
          duration: 0.7,
          ease: 'power3.out',
          stagger: 0.12,
          overwrite: 'auto',
          onComplete: () => {
            zzwPanes.forEach((p) => gsap.set(p, { clearProps: 'opacity,transform' }));
          },
        }),
      });
    }

    // CTA strip — gentle entrance
    const zzwCta = zzwSection.querySelector('.zzw-cta-strip');
    if (zzwCta) {
      gsap.set(zzwCta, { opacity: 0, y: 24, scale: 0.98 });
      ScrollTrigger.create({
        trigger: zzwCta,
        start: 'top 90%',
        once: true,
        animation: gsap.to(zzwCta, {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.9,
          ease: 'power3.out',
          overwrite: 'auto',
          onComplete: () => gsap.set(zzwCta, { clearProps: 'opacity,transform' }),
        }),
      });
    }
  }

  /* ====================================================
     5. Code typewriter
     ==================================================== */
  const codeEl = document.getElementById('code-target');
  const outputEl = document.getElementById('terminal-output');
  if (codeEl) {
    const codeRaw =
`fn main() {
  let lang = "H#"
  let n = 42
  print("Hello, " + lang + "!")
  print("The answer is " + str(n))
  for i in 0..3 {
    print("loop " + str(i) + " done.")
  }
}`;

    const keywords = ['fn', 'let', 'if', 'else', 'for', 'while', 'return', 'import', 'class', 'new', 'in', 'true', 'false', 'nullptr'];
    const escapeHtml = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    function highlight(code) {
      let s = escapeHtml(code);
      s = s.replace(/(\/\/[^\n]*)/g, '<span class="tok-com">$1</span>');
      s = s.replace(/("(?:\\"|[^"])*")/g, '<span class="tok-str">$1</span>');
      s = s.replace(/\b(\d+)\b/g, '<span class="tok-num">$1</span>');
      const kwRe = new RegExp('\\b(' + keywords.join('|') + ')\\b', 'g');
      s = s.replace(kwRe, '<span class="tok-kw">$1</span>');
      s = s.replace(/\b([a-zA-Z_][a-zA-Z0-9_]*)(?=\s*\()/g, (m, p1) =>
        keywords.includes(p1) ? '<span class="tok-kw">' + p1 + '</span>' : '<span class="tok-fn">' + p1 + '</span>'
      );
      s = s.replace(/\b([A-Z][a-zA-Z0-9_]*)\b/g, '<span class="tok-ty">$1</span>');
      return s;
    }

    let typed = '';
    let idx = 0;
    let started = false;
    let typeToken = 0;

    function typeStep(token) {
      if (token !== typeToken) return; // canceled
      if (idx >= codeRaw.length) {
        if (outputEl) outputEl.classList.add('show');
        return;
      }
      const ch = codeRaw[idx];
      typed += ch;
      codeEl.innerHTML = highlight(typed);
      idx += 1;
      const delay = ch === '\n' ? 50 : (Math.random() * 10 + 10);
      setTimeout(() => typeStep(token), delay);
    }

    ScrollTrigger.create({
      trigger: '#terminal-body',
      start: 'top 85%',
      once: true,
      onEnter: () => {
        if (!started) {
          started = true;
          typeToken += 1;
          setTimeout(() => typeStep(typeToken), 200);
        }
      },
    });
  }

  /* ====================================================
     6. Performance counter
     ==================================================== */
  const counters = document.querySelectorAll('[data-count]');
  counters.forEach((el) => {
    const target = parseFloat(el.dataset.count);
    if (isNaN(target)) return;
    const obj = { v: 0 };
    el.textContent = '0';
    ScrollTrigger.create({
      trigger: el,
      start: 'top 88%',
      once: true,
      onEnter: () => {
        gsap.to(obj, {
          v: target,
          duration: 1.8,
          ease: 'power2.out',
          overwrite: 'auto',
          onUpdate: () => {
            el.textContent = Math.round(obj.v).toLocaleString();
          },
        });
      },
    });
  });

  /* ====================================================
     7. Smooth anchor offset
     ==================================================== */
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      const id = a.getAttribute('href');
      if (id.length < 2) return;
      const target = document.querySelector(id);
      if (!target) return;
      e.preventDefault();
      const top = target.getBoundingClientRect().top + window.scrollY - 64;
      window.scrollTo({ top, behavior: 'smooth' });
    });
  });

  /* ====================================================
     8. Refresh on resize / font load
     ==================================================== */
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => ScrollTrigger.refresh(), 200);
  });
  window.addEventListener('load', () => ScrollTrigger.refresh());
  if (document.fonts) {
    document.fonts.addEventListener('loadingdone', () => ScrollTrigger.refresh());
  }

})();
