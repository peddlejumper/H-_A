"""H# Self-Bootstrapping: compile all H# source to bytecode bundle."""

import sys, os, json, time, importlib.util

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# Load in dependency order (tokens → ast → h_ast → lexer → parser → compiler)
load_module('tokens', os.path.join(ROOT, 'tokens.py'))
load_module('ast', os.path.join(ROOT, 'ast.py'))
load_module('h_ast', os.path.join(ROOT, 'h_ast.py'))
lexer_mod = load_module('lexer', os.path.join(ROOT, 'lexer.py'))
parser_mod = load_module('parser', os.path.join(ROOT, 'parser.py'))
compiler_mod = load_module('compiler', os.path.join(ROOT, 'compiler.py'))

Lexer = lexer_mod.Lexer
Parser = parser_mod.Parser
Compiler = compiler_mod.Compiler

BOOTSTRAP_SOURCES = [
    "bootstrap/interpreter.hto",
    "bootstrap/compiler.hto",
    "bootstrap/executor.hto",
    "bootstrap/parser.hto",
    "bootstrap/bootstrap.hto",
    "bootstrap/tokenize.hto",
    "bootstrap/hwdui.hto",
    "bootstrap/formatter.hto",
    "bootstrap/linter.hto",
    "bootstrap/fs_module.hto",
    "bootstrap/io_module.hto",
    "bootstrap/math_utils.hto",
    "bootstrap/string_utils.hto",
    "bootstrap/array_utils.hto",
    "bootstrap/d3system.hto",
    "bootstrap/d3system_ops.hto",
    "bootstrap/d3_emotion.hto",
    "bootstrap/perf_monitor.hto",
    "bootstrap/env_optimized.hto",
    "bootstrap/math_extended.hto",
    "bootstrap/datetime_module.hto",
    "bootstrap/pkg_inspect.hto",
    "bootstrap/json_serializer.hto",
    "bootstrap/hsharp_builder.hto",
    "bootstrap/dzzw.hto",
    "bootstrap/test_dzzw_v2.hto",
    "bootstrap/test_ternary.hto",
    "bootstrap/selftest.hto",
    "bootstrap/test_parse_min.hto",
    "bootstrap/selfhost_test.hto",
    "bootstrap/hsharpmyl.hto",
    "bootstrap/test_hsharpmyl.hto",
    "bootstrap/test_hsharpmyl_v4.hto",
    "bootstrap/test_union.hto",
    "bootstrap/hwdui_dotnet.hto",
    "bootstrap/test_hwdui_dotnet.hto",
    "bootstrap/hwdui_java.hto",
    "bootstrap/test_hwdui_java.hto",
    "bootstrap/hwdui_cpp.hto",
    "bootstrap/test_hwdui_cpp.hto",
]

def compile_file(path):
    with open(os.path.join(ROOT, path), "r", encoding="utf-8") as f:
        source = f.read()
    lexer = Lexer(source)
    parser = Parser(lexer)
    program = parser.parse()
    modname = path.replace("bootstrap/", "").replace(".hto", "")
    compiler = Compiler()
    bytecode = compiler.compile(program)
    return modname, bytecode

def main():
    print(f"═══ H# Self-Bootstrapping Compiler ═══")
    print(f"Compiling {len(BOOTSTRAP_SOURCES)} H# source files...")
    print()

    bundle = {"version": "v0.4", "modules": {}, "built_at": time.time()}
    failed = []

    for path in BOOTSTRAP_SOURCES:
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            print(f"  SKIP: {path} (not found)")
            continue
        try:
            modname, bc = compile_file(path)
            bundle["modules"][modname] = bc
            ninstrs = len(bc["instructions"])
            nconsts = len(bc["consts"])
            print(f"  OK: {modname:20s}  {ninstrs:5d} instrs, {nconsts:3d} consts")
        except Exception as e:
            failed.append((path, str(e)))
            print(f"  FAIL: {path}: {e}")

    out = os.path.join(ROOT, "bootstrap", "hsharp_bundle.hbc")
    with open(out, "w") as f:
        json.dump(bundle, f, indent=2)

    print()
    if failed:
        print(f"WARNING: {len(failed)} files failed to compile:")
        for p, e in failed:
            print(f"  - {p}: {e}")
    print(f"Bundle: {out}")
    print(f"Modules: {len(bundle['modules'])}/{len(BOOTSTRAP_SOURCES)}")

if __name__ == "__main__":
    main()