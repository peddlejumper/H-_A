/* =========================================================
   H# download verification — 2-step local challenge
   Stage 1: "I'm not a robot" checkbox (with fake "verifying" delay)
   Stage 2: drag slider from left to right
   Stage 3: success state, then auto-trigger the actual download
   All state is local — no network, no cookie, no fingerprint.
   ========================================================= */
(() => {
  'use strict';

  const gsap = window.gsap;
  if (!gsap) return;

  // 0. Resolve the file from query string
  //   verify.html?file=macos-arm64-hps                → v0.4.2 macOS Apple Silicon .hps
  //   verify.html?file=macos-x64-app                 → v0.4.2 macOS Intel .app
  //   verify.html?file=beta-arm64-hps&v=0.5.0-beta.1 → v0.5.0-beta.1 macOS Apple Silicon .hps
  //   ...etc
  const params = new URLSearchParams(window.location.search);
  const file = params.get('file') || 'macos-arm64-hps';

  const FILE_MAP = {
    // ---- v0.4.2 stable ----
    'macos-arm64-hps':   { version: '0.4.2',         platform: 'macOS · Apple Silicon', kind: 'H# 语言包',   ext: '.hps', file: 'hsharp-0.4.2-macos-arm64.hps',         url: 'https://github.com/peddlejumper/HSharp/releases/download/v0.4.2/hsharp-0.4.2-macos-arm64.hps' },
    'macos-x64-hps':     { version: '0.4.2',         platform: 'macOS · Intel',          kind: 'H# 语言包',   ext: '.hps', file: 'hsharp-0.4.2-macos-x64.hps',           url: 'https://github.com/peddlejumper/HSharp/releases/download/v0.4.2/hsharp-0.4.2-macos-x64.hps' },
    'macos-arm64-app':   { version: '0.4.2',         platform: 'macOS · Apple Silicon', kind: 'H# 启动器',   ext: '.app', file: 'ZZWCode-0.4.2-mac-arm64.dmg',           url: 'https://github.com/peddlejumper/HSharp/releases/download/v0.4.2/ZZWCode-0.4.2-mac-arm64.dmg' },
    'macos-x64-app':     { version: '0.4.2',         platform: 'macOS · Intel',          kind: 'H# 启动器',   ext: '.app', file: 'ZZWCode-0.4.2-mac-x64.dmg',             url: 'https://github.com/peddlejumper/HSharp/releases/download/v0.4.2/ZZWCode-0.4.2-mac-x64.dmg' },

    // ---- v0.5.0 beta ----
    'beta-arm64-hps':    { version: '0.5.0-beta.1', platform: 'macOS · Apple Silicon', kind: 'H# 语言包',   ext: '.hps', file: 'hsharp-0.5.0-beta.1-macos-arm64.hps',   url: 'https://github.com/peddlejumper/HSharp/releases/download/v0.5.0-beta.1/hsharp-0.5.0-beta.1-macos-arm64.hps' },
    'beta-x64-hps':      { version: '0.5.0-beta.1', platform: 'macOS · Intel',          kind: 'H# 语言包',   ext: '.hps', file: 'hsharp-0.5.0-beta.1-macos-x64.hps',     url: 'https://github.com/peddlejumper/HSharp/releases/download/v0.5.0-beta.1/hsharp-0.5.0-beta.1-macos-x64.hps' },
    'beta-arm64-app':    { version: '0.5.0-beta.1', platform: 'macOS · Apple Silicon', kind: 'H# 启动器',   ext: '.app', file: 'ZZWCode-0.5.0-beta.1-mac-arm64.dmg',   url: 'https://github.com/peddlejumper/HSharp/releases/download/v0.5.0-beta.1/ZZWCode-0.5.0-beta.1-mac-arm64.dmg' },
    'beta-x64-app':      { version: '0.5.0-beta.1', platform: 'macOS · Intel',          kind: 'H# 启动器',   ext: '.app', file: 'ZZWCode-0.5.0-beta.1-mac-x64.dmg',     url: 'https://github.com/peddlejumper/HSharp/releases/download/v0.5.0-beta.1/ZZWCode-0.5.0-beta.1-mac-x64.dmg' },
  };
  const target = FILE_MAP[file] || FILE_MAP['macos-arm64-hps'];

  // Render target name
  const targetNameEl = document.getElementById('targetName');
  const targetNameSuccessEl = document.getElementById('targetNameSuccess');
  if (targetNameEl) targetNameEl.textContent = `H# v${target.version} · ${target.platform} (${target.kind})`;
  if (targetNameSuccessEl) targetNameSuccessEl.textContent = target.file;

  // Update document title to reflect version
  document.title = `下载验证 — H# v${target.version}`;

  // Set manual download link target
  const manualLink = document.getElementById('manualDownload');
  if (manualLink) manualLink.href = target.url;

  // ---------- Stage 1: checkbox ----------
  const checkbox = document.getElementById('verifyCheckbox');
  const stage1 = document.querySelector('[data-stage="1"]');
  const stage2 = document.querySelector('[data-stage="2"]');
  const stage3 = document.querySelector('[data-stage="3"]');
  const stepIndicator = document.querySelectorAll('[data-verify-step]');

  if (checkbox) {
    checkbox.addEventListener('click', () => {
      if (checkbox.classList.contains('is-checking') || checkbox.classList.contains('is-done')) return;
      checkbox.classList.add('is-checking');
      checkbox.setAttribute('aria-pressed', 'true');

      // Simulated "verifying" — 1.1s feels like a real hCaptcha roundtrip
      setTimeout(() => {
        checkbox.classList.remove('is-checking');
        checkbox.classList.add('is-done');
        advanceToStage2();
      }, 1100);
    });
  }

  function advanceToStage2() {
    // Update step indicator
    if (stepIndicator[0]) stepIndicator[0].classList.add('is-done');
    if (stepIndicator[1]) {
      stepIndicator[1].classList.remove('is-active');
      stepIndicator[1].classList.add('is-done');
    }
    if (stepIndicator[2]) stepIndicator[2].classList.add('is-active');

    // Swap stages
    stage1.hidden = true;
    stage2.hidden = false;
    gsap.fromTo(stage2, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' });
  }

  // ---------- Stage 2: drag slider ----------
  const slider = document.getElementById('verifySlider');
  const handle = document.getElementById('verifySliderHandle');
  const fill = document.getElementById('verifySliderFill');
  const sliderText = document.getElementById('verifySliderText');

  if (slider && handle && fill) {
    let dragging = false;
    let startX = 0;
    let startLeft = 0;
    const maxLeft = () => slider.clientWidth - handle.clientWidth;
    const handleRadius = handle.clientWidth / 2;
    let done = false;

    function getX(e) {
      if (e.touches && e.touches.length) return e.touches[0].clientX;
      return e.clientX;
    }

    function onStart(e) {
      if (done) return;
      dragging = true;
      handle.classList.add('is-dragging');
      startX = getX(e);
      const rect = handle.getBoundingClientRect();
      startLeft = rect.left - slider.getBoundingClientRect().left;
      e.preventDefault();
    }
    function onMove(e) {
      if (!dragging) return;
      const dx = getX(e) - startX;
      const max = maxLeft();
      let next = Math.max(0, Math.min(max, startLeft + dx));
      handle.style.left = next + 'px';
      const pct = max > 0 ? (next / max) * 100 : 0;
      fill.style.width = `calc(${pct}% + ${handleRadius}px)`;
      // Pull the text along
      if (sliderText) {
        const textMax = slider.clientWidth - sliderText.clientWidth - 12;
        sliderText.style.left = Math.min(textMax, next + handle.clientWidth + 8) + 'px';
        sliderText.style.opacity = String(Math.max(0, 1 - pct / 90));
      }
      if (pct >= 96) {
        dragging = false;
        done = true;
        handle.classList.remove('is-dragging');
        handle.classList.add('is-done');
        finishVerification();
      }
    }
    function onEnd() {
      if (!dragging) return;
      dragging = false;
      handle.classList.remove('is-dragging');
      if (done) return;
      // Snap back if not finished
      gsap.to(handle, { left: 0, duration: 0.5, ease: 'power3.out' });
      gsap.to(fill, { width: `calc(0% + ${handleRadius}px)`, duration: 0.5, ease: 'power3.out' });
      if (sliderText) {
        gsap.to(sliderText, { left: 64, opacity: 1, duration: 0.5, ease: 'power3.out' });
      }
    }

    handle.addEventListener('mousedown', onStart);
    handle.addEventListener('touchstart', onStart, { passive: false });
    window.addEventListener('mousemove', onMove);
    window.addEventListener('touchmove', onMove, { passive: false });
    window.addEventListener('mouseup', onEnd);
    window.addEventListener('touchend', onEnd);

    // Keyboard support — Space / Right arrow advances by 10%
    handle.addEventListener('keydown', (e) => {
      if (done) return;
      const max = maxLeft();
      const cur = parseFloat(handle.style.left || '0') || 0;
      let step = 0;
      if (e.key === 'ArrowRight' || e.key === ' ') step = max * 0.12;
      if (e.key === 'ArrowLeft') step = -max * 0.12;
      if (!step) return;
      e.preventDefault();
      const next = Math.max(0, Math.min(max, cur + step));
      gsap.to(handle, { left: next, duration: 0.25, ease: 'power2.out' });
      const pct = max > 0 ? (next / max) * 100 : 0;
      gsap.to(fill, { width: `calc(${pct}% + ${handleRadius}px)`, duration: 0.25, ease: 'power2.out' });
      if (sliderText) {
        const textMax = slider.clientWidth - sliderText.clientWidth - 12;
        gsap.to(sliderText, { left: Math.min(textMax, next + handle.clientWidth + 8), opacity: Math.max(0, 1 - pct / 90), duration: 0.25 });
      }
      if (pct >= 96) {
        done = true;
        handle.classList.add('is-done');
        finishVerification();
      }
    });
  }

  function finishVerification() {
    // Update step indicator
    if (stepIndicator[2]) {
      stepIndicator[2].classList.remove('is-active');
      stepIndicator[2].classList.add('is-done');
    }

    // Swap to stage 3
    stage2.hidden = true;
    stage3.hidden = false;
    gsap.fromTo(stage3, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' });

    // Auto-trigger the actual download after 1.5s
    setTimeout(() => {
      const a = document.createElement('a');
      a.href = target.url;
      a.download = target.file;
      a.rel = 'noopener';
      document.body.appendChild(a);
      a.click();
      a.remove();
    }, 1500);
  }
})();
