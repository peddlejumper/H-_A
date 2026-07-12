(function() {
    'use strict';

    var domLoaded, init;

    var translations = {
        en: {
            'nav.about': 'About',
            'nav.features': 'Features',
            'nav.code': 'Code',
            'nav.download': 'Download',
            'hero.sub1': 'A parallel computing focused',
            'hero.sub2': 'functional programming language',
            'hero.sub3': 'for the space computing era',
            'hero.scroll': 'Scroll',
            'about.title': 'What is <span class="accent">H#</span>?',
            'about.desc1': 'H# is an experimental programming language with a Python-like syntax that compiles to a custom bytecode VM. It\'s built from scratch with a focus on exploration of new programming paradigms and space computing concepts.',
            'about.desc2': 'With built-in D3 system for space operations, coroutine-based concurrency, and an optimizing compiler, H# pushes the boundaries of what\'s possible in language design.',
            'about.stat1': 'Current Version',
            'about.stat2': 'Years Development',
            'about.stat3': 'Custom VM',
            'features.title': 'Core <span class="broken-text" data-i18n="features.sub">Capabilities</span>',
            'features.sub': 'Capabilities',
            'f1.title': 'Space Computing',
            'f1.desc': 'Built-in D3 emotional system for spatial computing operations. New paradigm for handling complex geometric relationships.',
            'f2.title': 'Parallel Execution',
            'f2.desc': 'Coroutine-based concurrency with custom scheduler. Efficient multi-tasking without the GIL bottleneck.',
            'f3.title': 'Optimizing Compiler',
            'f3.desc': 'Multiple optimization passes from AST generation to register allocation. Clean and well-documented compiler pipeline.',
            'f4.title': 'Functional First',
            'f4.desc': 'First-class functions, closures, and lexical scoping. Built-in support for functional programming patterns.',
            'f5.title': 'Python Interop',
            'f5.desc': 'Seamless integration with Python host functions. Leverage the entire Python ecosystem from H# code.',
            'f6.title': 'Extensible',
            'f6.desc': 'Modular standard library design. Easy to add new modules and extend the language capabilities.',
            'code.title': 'Sample <span class="stagger-text" data-i18n="code.sub">Code</span>',
            'code.sub': 'Code',
            'code.desc': 'See H# in action with these examples',
            'download.title': 'Get <span class="glitch-text" data-i18n="download.sub">Started</span>',
            'download.sub': 'Started',
            'download.desc': 'H# is open source and available on GitHub. Clone it, build it, and explore.',
            'download.github': 'GitHub',
            'download.docs': 'Documentation',
            'footer.tagline': 'Parallel computing for the space era',
            'nav.zzw': 'ZZW Code',
            'zzw.title': '<span class="accent">ZZW Code</span> — AI-Powered H# IDE',
            'zzw.subtitle': 'A modern development environment with built-in AI assistance, Monaco editor, and seamless H# support',
            'zzw.f1.title': 'AI Code Assistant',
            'zzw.f1.desc': 'Get intelligent code suggestions, refactoring help, and explanations powered by Claude AI',
            'zzw.f2.title': 'Monaco Editor',
            'zzw.f2.desc': 'Industry-standard code editor with syntax highlighting, auto-completion, and multi-file support',
            'zzw.f3.title': 'Integrated Terminal',
            'zzw.f3.desc': 'Run H# code directly with real-time output, error highlighting, and debugging support',
            'zzw.f4.title': 'File Explorer',
            'zzw.f4.desc': 'Organize projects with folders, create and manage multiple .hto files with ease',
            'zzw.f5.title': 'Local Storage',
            'zzw.f5.desc': 'Your files are saved locally in IndexedDB. No cloud dependency, full privacy',
            'zzw.f6.title': 'H# Syntax Highlighting',
            'zzw.f6.desc': 'Custom language definition for H# with keywords, functions, and comments beautifully colored',
            'zzw.cta.title': 'Ready to Code?',
            'zzw.cta.desc': 'Launch ZZW Code now and experience the future of H# development',
            'zzw.cta.btn': 'Open ZZW Code'
        },
        zh: {
            'nav.about': '关于',
            'nav.features': '特性',
            'nav.code': '代码',
            'nav.download': '下载',
            'hero.sub1': '专注并行计算',
            'hero.sub2': '函数式编程语言',
            'hero.sub3': '面向空间计算时代',
            'hero.scroll': '滚动',
            'about.title': '什么是 <span class="accent">H#</span>？',
            'about.desc1': 'H# 是一门实验性编程语言，采用类似 Python 的语法，编译为自定义字节码虚拟机。从零开始构建，专注于探索新的编程范式和空间计算概念。',
            'about.desc2': '内置 D3 空间操作系统、协程并发和优化编译器，H# 突破了语言设计的边界。',
            'about.stat1': '当前版本',
            'about.stat2': '开发年限',
            'about.stat3': '自研虚拟机',
            'features.title': '核心 <span class="broken-text" data-i18n="features.sub">能力</span>',
            'features.sub': '能力',
            'f1.title': '空间计算',
            'f1.desc': '内置 D3 情感系统用于空间计算操作。处理复杂几何关系的新范式。',
            'f2.title': '并行执行',
            'f2.desc': '基于协程的并发与自定义调度器。高效多任务，无 GIL 瓶颈。',
            'f3.title': '优化编译器',
            'f3.desc': '从 AST 生成到寄存器分配的多轮优化通道。清晰易懂的编译器管道。',
            'f4.title': '函数优先',
            'f4.desc': '一等公民函数、闭包和词法作用域。内置函数式编程模式支持。',
            'f5.title': 'Python 互操作',
            'f5.desc': '与 Python 主机函数无缝集成。从 H# 代码中使用整个 Python 生态。',
            'f6.title': '可扩展',
            'f6.desc': '模块化标准库设计。轻松添加新模块，扩展语言能力。',
            'code.title': '示例 <span class="stagger-text" data-i18n="code.sub">代码</span>',
            'code.sub': '代码',
            'code.desc': '通过这些示例了解 H# 的实际应用',
            'download.title': '开始 <span class="glitch-text" data-i18n="download.sub">使用</span>',
            'download.sub': '使用',
            'download.desc': 'H# 是开源项目，可在 GitHub 获取。克隆、构建、探索。',
            'download.github': 'GitHub',
            'download.docs': '文档',
            'footer.tagline': '空间计算时代的并行编程',
            'nav.zzw': 'ZZW Code',
            'zzw.title': '<span class="accent">ZZW Code</span> — AI 驱动的 H# IDE',
            'zzw.subtitle': '内置 AI 助手、Monaco 编辑器和无缝 H# 支持的现代化开发环境',
            'zzw.f1.title': 'AI 代码助手',
            'zzw.f1.desc': '获取智能代码建议、重构帮助和 Claude AI 驱动的代码解释',
            'zzw.f2.title': 'Monaco 编辑器',
            'zzw.f2.desc': '业界标准的代码编辑器，支持语法高亮、自动补全和多文件编辑',
            'zzw.f3.title': '集成终端',
            'zzw.f3.desc': '直接运行 H# 代码，实时输出、错误高亮和调试支持',
            'zzw.f4.title': '文件浏览器',
            'zzw.f4.desc': '用文件夹组织项目，轻松创建和管理多个 .hto 文件',
            'zzw.f5.title': '本地存储',
            'zzw.f5.desc': '文件保存在本地 IndexedDB，无云依赖，完全隐私',
            'zzw.f6.title': 'H# 语法高亮',
            'zzw.f6.desc': '为 H# 定制的语言定义，关键字、函数和注释颜色绚丽',
            'zzw.cta.title': '准备开始编程？',
            'zzw.cta.desc': '立即启动 ZZW Code，体验 H# 开发的未来',
            'zzw.cta.btn': '打开 ZZW Code'
        }
    };

    function setLanguage(lang) {
        var html = document.documentElement;
        html.setAttribute('lang', lang);
        localStorage.setItem('hsharp-lang', lang);

        var els = document.querySelectorAll('[data-i18n]');
        for (var i = 0; i < els.length; i++) {
            var key = els[i].getAttribute('data-i18n');
            if (translations[lang][key]) {
                els[i].innerHTML = translations[lang][key];
            }
        }

        var btns = document.querySelectorAll('.lang-btn');
        for (var i = 0; i < btns.length; i++) {
            btns[i].classList.toggle('active', btns[i].getAttribute('data-lang') === lang);
        }
    }

    domLoaded = function(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    };

    init = function() {
        var nav = document.querySelector('.navigation');
        var hero = document.querySelector('.hero');
        var geos = document.querySelectorAll('.geo');
        var cards = document.querySelectorAll('.feature-card');
        var codes = document.querySelectorAll('.code-display');
        var icons = document.querySelectorAll('.feature-icon');
        var footer = document.querySelector('.footer');
        var broken = document.querySelector('.broken-text');
        var glitch = document.querySelector('.glitch-text');
        var langBtns = document.querySelectorAll('.lang-btn');
        var lastScroll = 0;
        var ticking = false;

        // Language switcher
        var savedLang = localStorage.getItem('hsharp-lang') || 'en';
        setLanguage(savedLang);

        for (var i = 0; i < langBtns.length; i++) {
            langBtns[i].addEventListener('click', function() {
                setLanguage(this.getAttribute('data-lang'));
            });
        }

        // Progress bar
        var bar = document.createElement('div');
        bar.style.cssText = 'position:fixed;top:0;left:0;height:3px;width:0%;background:linear-gradient(90deg,#00ffaa,#6644ff);z-index:1001;transition:width .1s';
        document.body.appendChild(bar);

        // Cursor glow
        var glow = document.createElement('div');
        glow.style.cssText = 'position:fixed;width:400px;height:400px;border-radius:50%;background:radial-gradient(circle,rgba(0,255,170,.08) 0%,transparent 70%);pointer-events:none;z-index:0;transform:translate(-50%,-50%);transition:left .3s,top .3s';
        document.body.appendChild(glow);
        var gx = window.innerWidth / 2, gy = window.innerHeight / 2;

        document.addEventListener('mousemove', function(e) {
            gx = e.clientX;
            gy = e.clientY;
            glow.style.left = gx + 'px';
            glow.style.top = gy + 'px';
        }, { passive: true });

        // Hero parallax
        if (hero && geos.length) {
            hero.addEventListener('mousemove', function(e) {
                var x = (e.clientX / window.innerWidth - 0.5) * 2;
                var y = (e.clientY / window.innerHeight - 0.5) * 2;
                for (var i = 0; i < geos.length; i++) {
                    geos[i].style.transform = 'translate(' + (x * (i + 1) * 30) + 'px,' + (y * (i + 1) * 30) + 'px)';
                }
            }, { passive: true });
        }

        // Broken text
        if (broken) {
            var btext = broken.textContent;
            broken.innerHTML = '';
            for (var i = 0; i < btext.length; i++) {
                var span = document.createElement('span');
                span.textContent = btext[i];
                span.style.cssText = 'display:inline-block;transition:transform .2s';
                broken.appendChild(span);
            }
            broken.addEventListener('mouseenter', function() {
                var spans = broken.querySelectorAll('span');
                for (var i = 0; i < spans.length; i++) {
                    (function(idx) {
                        setTimeout(function() {
                            spans[idx].style.transform = 'translateY(' + ((Math.random() - 0.5) * 10) + 'px)';
                            setTimeout(function() { spans[idx].style.transform = ''; }, 100);
                        }, idx * 20);
                    })(i);
                }
            });
        }

        // Glitch text
        if (glitch) {
            var gInterval;
            glitch.addEventListener('mouseenter', function() {
                gInterval = setInterval(function() {
                    glitch.style.transform = 'translate(' + ((Math.random() - 0.5) * 6) + 'px,' + ((Math.random() - 0.5) * 6) + 'px)';
                    glitch.style.textShadow = (Math.random() > 0.5 ? '3px 0 #00ffaa' : '-3px 0 #6644ff') + ',' + (Math.random() > 0.5 ? '-3px 0 #6644ff' : '3px 0 #00ffaa');
                    setTimeout(function() { glitch.style.transform = ''; glitch.style.textShadow = ''; }, 80);
                }, 150);
            });
            glitch.addEventListener('mouseleave', function() {
                clearInterval(gInterval);
                glitch.style.transform = '';
                glitch.style.textShadow = '';
            });
        }

        // Smooth scroll
        var anchors = document.querySelectorAll('a[href^="#"]');
        for (var i = 0; i < anchors.length; i++) {
            anchors[i].addEventListener('click', function(e) {
                e.preventDefault();
                var target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    var navH = nav.offsetHeight;
                    var top = target.getBoundingClientRect().top + window.scrollY - navH - 20;
                    window.scrollTo({ top: top, behavior: 'smooth' });
                }
            });
        }

        // Scroll handler
        function onScroll() {
            lastScroll = window.scrollY;
            var docH = document.documentElement.scrollHeight - window.innerHeight;
            bar.style.width = (lastScroll / docH * 100) + '%';

            if (lastScroll > 300) {
                nav.style.transform = 'translateY(-100%)';
            } else {
                nav.style.transform = '';
            }

            var percent = lastScroll / docH;
            for (var i = 0; i < icons.length; i++) {
                icons[i].style.transform = 'rotate(' + (percent * 180 * (i % 2 === 0 ? 1 : -1)) + 'deg) scale(' + (1 + Math.sin(percent * Math.PI) * 0.15) + ')';
            }

            ticking = false;
        }

        window.addEventListener('scroll', function() {
            if (!ticking) {
                requestAnimationFrame(onScroll);
                ticking = true;
            }
        }, { passive: true });

        // Cards
        var cardObs = new IntersectionObserver(function(entries) {
            for (var i = 0; i < entries.length; i++) {
                if (entries[i].isIntersecting) {
                    var card = entries[i].target;
                    var delay = parseFloat(card.getAttribute('data-delay') || 0);
                    setTimeout(function(c) {
                        c.style.opacity = '1';
                        c.style.transform = 'translateY(0)';
                        c.style.boxShadow = '0 20px 60px rgba(0, 255, 170, 0.15)';
                    }, delay * 100, card);
                    cardObs.unobserve(card);
                }
            }
        }, { threshold: 0.2, rootMargin: '0px 0px -50px 0px' });

        for (var i = 0; i < cards.length; i++) {
            cards[i].style.cssText += ';opacity:0;transform:translateY(40px);transition:opacity .6s,transform .6s,border-color .3s,box-shadow .3s';
            cardObs.observe(cards[i]);
        }

        // Codes
        var codeObs = new IntersectionObserver(function(entries) {
            for (var i = 0; i < entries.length; i++) {
                if (entries[i].isIntersecting) {
                    var block = entries[i].target;
                    block.style.opacity = '1';
                    block.style.transform = 'translateY(0)';

                    var lines = block.querySelectorAll('.code-line');
                    for (var j = 0; j < lines.length; j++) {
                        (function(idx, el) {
                            setTimeout(function() {
                                el.style.opacity = '1';
                                el.style.transform = 'translateX(0)';
                            }, idx * 60);
                        })(j, lines[j]);
                    }
                    codeObs.unobserve(block);
                }
            }
        }, { threshold: 0.3 });

        for (var i = 0; i < codes.length; i++) {
            codes[i].style.cssText += ';opacity:0;transform:translateY(40px);transition:opacity .6s,transform .6s';
            codeObs.observe(codes[i]);
        }

        var allLines = document.querySelectorAll('.code-line');
        for (var i = 0; i < allLines.length; i++) {
            allLines[i].style.cssText += ';opacity:0;transform:translateX(-20px);transition:opacity .4s,transform .4s';
        }

        // Footer
        if (footer) {
            footer.style.cssText += ';opacity:0;transition:opacity .8s';
            var footObs = new IntersectionObserver(function(entries) {
                if (entries[0].isIntersecting) {
                    footer.style.opacity = '1';
                    footObs.unobserve(footer);
                }
            }, { threshold: 0.5 });
            footObs.observe(footer);
        }

        // Particles
        setTimeout(function() {
            var colors = ['#00ffaa', '#6644ff', '#ff44aa', '#ffaa00'];
            setInterval(function() {
                if (document.hidden) return;

                var p = document.createElement('div');
                var size = Math.random() * 3 + 2;
                var color = colors[Math.floor(Math.random() * colors.length)];
                p.style.cssText = 'position:fixed;left:' + (Math.random() * window.innerWidth) + 'px;top:' + (window.innerHeight + 20) + 'px;width:' + size + 'px;height:' + size + 'px;background:' + color + ';border-radius:50%;pointer-events:none;z-index:5;box-shadow:0 0 ' + (size * 3) + 'px ' + color + ';';

                document.body.appendChild(p);

                var py = window.innerHeight + 20, px = parseFloat(p.style.left), t = 0;
                var speed = Math.random() * 2 + 1;
                var drift = (Math.random() - 0.5);
                var start = performance.now();

                function anim(time) {
                    t = (time - start) / 1000;
                    if (t > 3) {
                        p.remove();
                        return;
                    }
                    py -= speed * 2;
                    px += drift;
                    p.style.top = py + 'px';
                    p.style.left = px + 'px';
                    p.style.opacity = t < 0.3 ? t / 0.3 * 0.8 : t > 2.5 ? (3 - t) / 0.5 * 0.8 : 0.8;
                    requestAnimationFrame(anim);
                }
                requestAnimationFrame(anim);
            }, 500);
        }, 2000);

        // Easter egg
        var seq = '';
        window.addEventListener('keydown', function(e) {
            seq += e.key.toLowerCase();
            if (seq.length > 8) seq = seq.slice(-8);
            if (seq.indexOf('hsharp') !== -1) {
                document.body.style.transition = 'filter .3s';
                document.body.style.filter = 'hue-rotate(180deg)';
                setTimeout(function() { document.body.style.filter = ''; }, 400);
                seq = '';
            }
        });

        console.log('H# initialized');
    };

    domLoaded(init);
})();
