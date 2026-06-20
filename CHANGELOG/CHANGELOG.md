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
- **`for x in y` syntax** — already supported (class fields, range, list,
  string, dict, k/v unpacking), but a latent stack-leak bug in the
  nested-`for` + `break` interaction was fixed.  The compiler now emits
  a `CLEANUP_FOR` opcode at the for-end position: `break` jumps there
  and pops the iterator dict that `FOR_ITER` pushed but didn't get to
  pop; the normal end-of-iteration path skips it because `FOR_ITER`
  has already set `f.pc` past it.  New test file `15_for_loop.hto`
  (18 cases) covers list / string / dict / `k, v` / range (1- and
  2-arg) / break / continue / nested for / empty iterables / state
  isolation between back-to-back for loops.
- **Generics / Templates support (`<T>` syntax)** — class and function
  type-parameter declarations (`class Box<T>`, `class Pair<K, V>`,
  `fn identity<T>(x)`) and explicit type-argument call sites
  (`new Box<int>(42)`, `identity<int>(42)`, `Pair<string, int>("k", 7)`).
  - **AST nodes** — `type_params` field on `ClassDef` and `FunctionDef`,
    `type_args` field on `Call`, `New`, `MethodCall`, and `CallValue` AST
    nodes in `h_ast.py`.
  - **Parser** — new `_parse_type_params()` in `parser.py`; uses lexer
    `save_state`/`restore_state` plus a `(` lookahead so that `a < b` is
    never mistaken for a type-parameter list.  The `<T>` syntax is
    recognized on class declarations, top-level functions, and
    non-deref function expressions.
  - **Lexer** — `save_state()` and `restore_state()` added so the parser
    can speculatively read a `<` and roll back.
  - **Python compiler (`compiler.py`)** — emits `type_params` (string list)
    on class/function consts, attaches `type_args` to call-site consts,
    and introduces four new opcodes:
      * `CALL_FUNCTION_T` — name lookup with type-arg list
      * `CALL_VALUE_T`    — value-arg call with type-arg list
      * `CALL_METHOD_T`   — method call with type-arg list
      * `CALL_NEW_T`      — constructor call with type-arg list
    The stack layout for the `*_T` opcodes is
    `[arg1, ..., argN, type_args_list, callable]`, with the `type_args`
    list just above the value args and the callable (function / class /
    self) on top, matching how the Kotlin runtime pops them.
    `fn init` is now renamed to `__init__` when stored in the class method
    table so that the Kotlin VM's existing `methods["__init__"]` lookup
    continues to work.
  - **Kotlin runtime** — `HClass` and `HFunction` gained a `typeParams:
    List<String>` field; `HbcReader` parses the new `type_params` key.
    `HVM` now has `callFunction(name, argc, hasTypeArgs)` /
    `callValue(argc, hasTypeArgs)` / `callMethod(name, argc, hasTypeArgs)` /
    `callNew(argc, hasTypeArgs)` overloads that pop the type-arg list
    (as an `HList`) immediately above the value args, then pass it as
    `typeArgs` to `invokeCallable`.  When `callNew` is given explicit
    type arguments, the created `HInstance` receives a `__type_args__`
    field so the body can introspect them; the `__type_args__` lookup
    on a non-generic instance yields `HNull` (Python-like).  Reading
    `Cls.__type_params__` on a class returns the type-parameter name list.
  - **Test suite** — new `test_generics.hto` covers `class Box<T>`,
    `class Pair<K, V>`, `class Triple<A, B, C>`, `class Wrapper<T>`,
    `class Point` (non-generic), `fn identity<T>(x)`, `fn first_of<T>(arr)`;
    verifies `__type_args__` / `__type_params__` introspection; verifies
    that `a < b` comparison is not parsed as type-argument syntax; and
    verifies the rename of `init` → `__init__`.  All **18/18** zzwui
    test files pass; **687/687** individual `check()` cases pass.
  - **Compiler fix for `fns[i](v)`-style value calls** — the generic
    callable-expression path now pushes value args first and the
    function/cell expression last, so the Kotlin VM's `callValue`
    (which pops the callable from the top of the stack) sees them in
    the right order.  This was masked before because most call sites
    were simple `name(...)` forms that go through `CALL_FUNCTION`.
  - **`in_function_body` flag in `compiler.py`** — distinguishes
  compiling a function body from compiling the module top level.
  Used to decide whether a name referenced inside a function but
  not bound locally should be treated as a free variable
  (`LOAD_DEREF` + `CALL_VALUE`) or looked up by name at call time
  (`CALL_FUNCTION`).  Without this, top-level functions in
  `zzw_native.hto` were mis-classifying `gui_set_clip` etc. as
  free variables and failing to find them.
- **Native `async fn` / `await expr` syntax** — user-level sugar on
  top of the low-level `coro fn` API.  H# now has a familiar
  async/await story: declare with `async fn`, receive a
  `Future<T>` at the call site, unwrap with `await expr`.  This
  is the user-facing layer; `coro fn` is preserved as the
  low-level primitive and continues to be the only API that
  drives a real (lazy / multi-shot) coroutine — `async fn` is
  purely a static-and-runtime convenience.
  - **Keywords / tokens** — `async` and `await` added to
    `tokens.py` and `lexer.py` as reserved words.  `async` is
    only treated as a keyword when it is immediately followed by
    `fn` (the parser uses `lexer.save_state` /
    `lexer.restore_state` so that `async` remains usable as an
    ordinary identifier in expression contexts).
  - **AST** — `Function` got an `is_async: bool` field; new
    `AwaitExpression` node wrapping the awaited expression.
  - **Parser** — `function_declaration(is_async=True)` sets both
    `is_coro=True` and `is_async=True` on the function AST,
    making `async fn` semantically a `coro fn` plus the
    user-level sugar marker.  `unary()` recognises the
    `await expr` prefix and builds an `AwaitExpression`.
  - **Static type check (`compiler.py`)** — the compiler
    tracks an `in_async` flag while compiling function bodies.
    `await expr` is rejected at compile time when
    `in_function_body` is true but `in_async` is false, with the
    error
    > Static type error: `await` is only allowed inside an
    > `async fn` body (or at the top level of a module).  `coro
    > fn` and plain `fn` do not support `await`.
    Top-level `await` is permitted because the entry script
    acts as an implicit async context — there's no enclosing
    function that could be a non-async one.  This is the
    "明确哪些函数可 await" requirement: the static pass names
    exactly the functions that can be awaited, eliminating the
    callback-chain ambiguity that pure `coro fn` had.
  - **Bytecode** — `await expr` lowers to a single `AWAIT`
    opcode.  `async fn` call sites automatically wrap their
    return value in an `HFuture`, so the user never has to
    touch the future machinery directly.
  - **Runtime (`HValue.kt`)** — new `HType.FUTURE` enum value
    and a corresponding `HFuture(value: HValue, resolved:
    Boolean = true)` data class.  In this VM the future is
    single-threaded and eagerly resolved (the body runs to
    completion on the call, and `await` just unwraps the
    inner value); the shape is also ready for a future
    lazy / multi-threaded implementation
    (`HFuture(resolved = false)` would suspend the frame and
    the scheduler would resume it) without changing the AST or
    the surface syntax.
  - **Runtime (`HVM.kt`)** — new `AWAIT` opcode in the dispatch
    loop: pops the value, type-checks that it is an `HFuture`
    (raises `HSharpRuntimeError` otherwise), and pushes the
    inner value.  `invokeHFunction` wraps the return value in
    `HFuture(raw, resolved = true)` whenever
    `func.isAsync == true`; `coro fn` and plain `fn` are
    unaffected, so `coro fn` remains the low-level API and
    `async fn` is the user-level sugar layer as the spec
    requires.
  - **Runtime (`HbcReader.kt`)** — reads the new `is_async`
    boolean from the function const map and sets
    `HFunction.isAsync`.  `MAKE_CLOSURE` preserves the
    `isAsync` flag when building a closure instance.
  - **Introspection** — function values now expose
    `fn.is_async`, `fn.is_coro`, `fn.name`, and `fn.args` as
    read-only attributes (so a generic decorator can decide
    whether a callable is async at runtime).
  - **Test suite** — new `16_async_await.hto` (16 cases):
    `async fn` declaration, returning a future that `await`
    unwraps, sequential awaits in one body, nested awaits
    across two `async fn`s, `await` on a non-future raising
    at runtime, `coro fn` (low-level) still returning a raw
    value, `is_async` flag true for `async fn` and false for
    `coro fn` and plain `fn`, and async fn returning values
    of different types (number, string, list, bool, null).
    All **20/20** zzwui test files pass; **721/721**
    individual `check()` cases pass.

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
