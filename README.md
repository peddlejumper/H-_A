# H# v0.4.1 — Full Package

This directory is the **single-source distribution of the H# programming
language v0.4.1**.  Every useful file of the current implementation is
collected here.

## What is H#?

H# (H-Sharp) is a Python-derived, indentation-sensitive, optionally
object-oriented language with:

- A **Python-like surface syntax** (`#` comments, `let` bindings,
  `[…]` lists, `{…}` dicts, `fn` definitions, `class Foo { let x; fn bar(); }`).
- A **Kotlin bytecode VM** (`hsharp-kotlin-compiler/`) that runs `.hbc`
  files compiled from `.hto` sources via the Python-based parser.
- A **widget UI library** (`zzwui`) that provides `ZzwRenderer`,
  `ZzwWindow`, and a `zzwUI` widget class hierarchy on top of the native
  GUI bridge (`gui_*` natives in `HNativeBridge.kt`).
- A **VS Code extension** (`vscode-hsharp/`) with syntax highlighting,
  snippets, run/compile/package commands.
- A **.NET/Avalonia IDE** (`hsharp-ide/`), a launcher (`hsharp-launcher/`)
  and a website (`hsharp-site/`).

## Layout

```
H#_v0.4.1_Package/
├── README.md                       ← this file
├── CHANGELOG/CHANGELOG.md          ← release notes
├── docs/                           ← language guide, performance benchmarks, design papers
├── hsharp-kotlin-compiler/         ← Kotlin VM/compiler — primary runtime
│   ├── src/                        ← Kotlin source (com.hsharp.*)
│   ├── lib/                        ← prebuilt jars (hsharp-kotlin-compiler.jar, hsharp-runtime.jar, kotlin-stdlib)
│   ├── lib-tests/                  ← 8 algorithm/OO tests + report
│   ├── stress-tests/               ← 7 stress/scaling tests + report
│   ├── zzwui-tests/                ← 14 zzwui tests + report (521 cases)
│   ├── scripts/                    ← build.sh, hsharp-runtime shell wrapper
│   └── README.md
├── bootstrap/                      ← 45 H# source files (the self-hosted std lib)
├── hsharp-v0.4-Python-Package/     ← pure Python reference implementation (v0.4.0)
├── HSharp_v0.4_Tests/              ← additional Python integration tests
├── vscode-hsharp/                  ← VS Code extension source + 0.4.1 .vsix
├── hsharp-ide/                     ← .NET/Avalonia IDE (source only)
├── hsharp-launcher/                ← .NET launcher (source only)
└── hsharp-site/                    ← static website
```

## Test status (v0.4.1)

| Suite | Files | Cases | Pass rate |
| --- | ---: | ---: | ---: |
| `hsharp-kotlin-compiler/lib-tests/` | 8 | (see report) | 100% |
| `hsharp-kotlin-compiler/stress-tests/` | 7 | (see report) | 100% |
| `hsharp-kotlin-compiler/zzwui-tests/` | **14** | **521** | **100%** |
| **Total** | **29+** | **521+** | **100%** |

See `hsharp-kotlin-compiler/*/report.md` for the full per-test breakdown.

## Running the Kotlin compiler

```sh
cd hsharp-kotlin-compiler
java -cp "lib/hsharp-kotlin-compiler.jar:lib/hsharp-runtime.jar:lib/*" \
     com.hsharp.compiler.MainKt run path/to/program.hbc
```

`hsharp-runtime` is a shell wrapper that handles the classpath:

```sh
./scripts/hsharp-runtime path/to/program.hbc
```

## Running the test suites

```sh
cd hsharp-kotlin-compiler
python3 lib-tests/run_lib_tests.py        # 8 lib tests
python3 stress-tests/run_tests.py         # 7 stress tests
python3 zzwui-tests/run_zzwui_tests.py    # 14 zzwui tests
```

Each runner writes a `report.md` and a `results.json` into its directory.

## Installing the VS Code extension

```sh
code --install-extension vscode-hsharp/hsharp-language-0.4.1.vsix
```

The extension uses the bundled `lib/hsharp-kotlin-compiler.jar` and
`lib/hsharp-runtime.jar` out of the box; you can override with the
`hsharp.kotlinCompiler.jar` and `hsharp.kotlinRuntime.jar` settings.

## Building from source

```sh
cd hsharp-kotlin-compiler
./scripts/build.sh          # produces build/libs/hsharp-kotlin-compiler.jar
                            # and build/libs/hsharp-runtime.jar
```

Then replace the bundled jars in `vscode-hsharp/lib/` and re-pack:

```sh
cd vscode-hsharp
python3 build_vsix.py       # produces hsharp-language-0.4.X.vsix
```

## Repository

`https://github.com/peddlejumper/H-_A`

## License

MIT — see `vscode-hsharp/LICENSE.txt`.
