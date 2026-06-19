# Changelog

All notable changes to the H# programming language project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2026-06-20

### Added

- **Native GUI bridge (`gui_*` natives)** — 30+ stub functions in
  `HNativeBridge.kt` covering window management, drawing primitives, the event
  loop, timers, screen info, clipboard, and color utilities.  The zzwui
  library can now call `native_draw_rect`, `native_set_clip`,
  `native_parse_color`, `native_lerp_color`, `native_get_events`, etc. through
  the Kotlin runtime without `Undefined name` errors.  A `GUIWindows` registry
  hands out deterministic window ids (1, 2, 3, …) so widget trees can be
  observed.
- **`ZzwWindow` and `ZzwRenderer` classes** — full root-window container
  and rendering engine in `zzw_render_min.hto`, with init/sizing/positioning
  primitives, a clip stack, theme dictionary, and font management.
- **`zzwui` UI library** — hand-written `hwdui_min.hto` (541 lines) implementing
  the widget class hierarchy (`zzwUI`, `Button`, `Label`, `Panel`, `CheckBox`,
  `TextInput`, `Slider`, `ListBox`, `ProgressBar`, `ImageView`, `Canvas`).
  Includes `__contains(coll, key)` as a manual replacement for H#'s missing
  `x in y` operator.
- **`drawImage(x, y, w, h, color)` method on `ZzwRenderer`** — bridges to
  `native_draw_image`.
- **Test suite** — 521 individual `check()` cases across 14 test files:
  - 8 algorithm/data-structure tests in `lib-tests/hto/`
  - 7 stress/scaling tests in `stress-tests/hto/`
  - 14 zzwui tests in `zzwui-tests/hto/`
- **Test runners** — `run_lib_tests.py`, `stress-tests/run_tests.py`,
  `zzwui-tests/run_zzwui_tests.py` and their `report.md` + `results.json`
  outputs.  Each runner parses the `PASS=N FAIL=M` summary line emitted by
  the H# test bodies and writes a Markdown report.
- **`build.py` for zzwui tests** — composes per-test dependencies
  (`hwdui_min.hto`, `zzw_native.hto`, `zzw_render_min.hto`) into a single
  source file via a `# build:` directive.
- **`H#_v0.4.1_Package/`** — single-directory distribution of every useful
  artifact of v0.4.1 (Kotlin compiler source + jars, zzwui, bootstrap, VS Code
  extension, IDE, launcher, website, docs, CHANGELOG).

### Changed

- **VS Code extension bumped to 0.4.1** — `package.json` and
  `extension.vsixmanifest` now report `0.4.1`.  `lib/hsharp-kotlin-compiler.jar`
  and `lib/hsharp-runtime.jar` replaced with the freshly built jars from
  `hsharp-kotlin-compiler/build/libs/`.  Re-packaged as
  `hsharp-language-0.4.1.vsix` (≈ 0.29 MB, 20 files).
- **`hsharp-kotlin-compiler` runtime now exposes a `gui_*` namespace** — the
  Kotlin VM's `HNativeBridge.kt` was extended from ~10 primitives to ~40
  primitives (math + string + array + GUI + color + system).
- **`run_zzwui_tests.py`** — new test runner modeled on `run_lib_tests.py`,
  with category aggregation, per-test timing, JSON dump, and a
  Markdown report generator that includes Findings/Coverage/Failure Detail
  sections.

### Fixed

- **H# compiler cannot call a field-stored function with `obj.field(args)`.**
  The Python parser emits `CALL_METHOD` for any `expr.member(args)` form, and
  the Kotlin VM's `CALL_METHOD` looks the member up in the *class method
  table only* — it does not fall through to `obj.fields`.  Workaround in
  `hwdui_min.hto`: rebind the field to a local with `let cb = self.onClick;`
  and call `cb(self)` (compiles to `CALL_FUNCTION`).
- **zzw_render.hto cannot be loaded as-is** — its top-level widget renderer
  functions (`zzwui_render_widget` etc.) cross-reference each other in
  ways that fail at module-load time.  `zzw_render_min.hto` extracts the
  two engine classes (no cross-references) for testing.
- **`MinStack.pop()` let-shadowing bug** in `11_oo_design_lib.hto` —
  `let i = i + 1` inside a while body shadowed the outer `i`.  Replaced
  with `i = i + 1`.
- **`MinStack.top()` test data** in `11_oo_design_lib.hto` — the expected
  top of `[5,2,8,1]` is `1` (last element pushed), not `8`.
- **Two-sum test data** in `08_algorithm_lib.hto` — the two-pointer
  algorithm on `[1,3,4,5,7,11]` for target `9` returns indices `[2,3]`, not
  `[0,1]`.

### Test data corrections

- `04_native / n/create` — `native_create_window` returns the first window
  id `1` (not `0`).  Test now checks `r1 != nullptr and r1 != 0`.
- `05_layout_stress / l/g_*` — grid cell step is `col_w + spacing (4) = 44`,
  not `42`.  Updated expected x-positions.
- `07_widget_tree / t/mass_y29` — `Label.height (20) + Panel.spacing (4) = 24`;
  `y[29] = 29 * 24 = 696` (was 638).
- `14_perf / p/dol_y9` — `Button.height (20) + Panel.spacing (4) = 24`;
  `y[9] = 9 * 24 = 216` (was 198).

## [0.4.0] - 2026-06-19

### Added

- **Initial public release of the H# programming language v0.4.**
- **H# v0.4 Python implementation** — `HSharp_v0.4_Package/` directory
  containing the parser, lexer, AST, bytecode emitter, and tree-walking
  interpreter in pure Python.  Includes the standard library
  (`array_utils`, `string_utils`, `math_utils`, `datetime_module`, `io_module`,
  `net_module`, `db_module`, `crypto_module`, `json_serializer`, `formatter`,
  `linter`, `perf_monitor`).
- **H# v0.4 IDE** (`hsharp-ide/`) — Avalonia-based .NET 6/7 IDE built around
  the H# language.  Source-only release; binaries must be built with
  `dotnet publish`.
- **H# v0.4 Launcher** (`hsharp-launcher/`) — environment checker and
  version switcher.
- **H# v0.4 Website** (`hsharp-site/`) — the marketing site (index, beta,
  download, guide, pricing, verify pages).
- **VS Code extension 0.4.0** — `vscode-hsharp/` with syntax highlighting
  (`hsharp.tmLanguage.json`), language configuration, snippets, the
  "H#: Run .hto via Kotlin VM" / "H#: Compile .hto to .hbc" / "H#: Package
  as native app" commands, and bundled `hsharp-kotlin-compiler.jar` +
  `hsharp-runtime.jar` from the 0.4.0 build.
- **H# Performance Benchmarks** — `benchmarks/` comparing H# (.htoc) against
  C, C++, Java, Python3, TypeScript on arithmetic, fib, list, matrix,
  primes, and string operations.
- **H# HSpace Computing Paper** — `HSharp_Space_Computing_Paper.md` describing
  the language's design for distributed / space-constrained execution.
- **H# Bootstrap (self-hosted compiler)** — `bootstrap/` contains the
  H#-written lexer, parser, compiler, and interpreter that compile back to
  H# bytecode, demonstrating self-hosting.
- **H# Standard Libraries report** — `bootstrap/STANDARD_LIBS_REPORT.md`
  summarising the standard library surface.

### Known limitations at v0.4.0

- No `for x in y` syntax — only `while` loops.
- No `x in y` operator — must use a manual scan or the `__contains` helper.
- `dict[k]` throws on missing keys — must guard with `has_key(dict, k)`.
- Class instantiation must use `new ClassName()`, not `ClassName()`.
- No `import` statement in the Python compiler — modules are concatenated
  by `build.py` instead.
- `obj.field(args)` (where `field` is a runtime function value) compiles to
  `CALL_METHOD` and only works for true class methods, not field-stored
  functions.

## [0.3.x] and earlier

See `docs/HSharp-Guide.md` for the design history of the H# language
prior to v0.4.
