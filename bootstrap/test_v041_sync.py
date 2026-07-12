#!/usr/bin/env python3
"""Test v0.4.1 feature sync to bootstrap end.

Validates that the bootstrap toolchain (tokenize.hto, parser.hto, compiler.hto)
can correctly process H# source code containing v0.4.1 new features:
  - Union declarations and construction
  - match expressions (wildcard/binding/literal/variant/guard)
  - Channel API (chan_new/chan_send/chan_recv)
  - ? error propagation
  - concurrent blocks
  - async/parallel fn + await
  - Generics (class Box<T>, fn name<T>(args), new Box<int>(args))

The bootstrap interpreter has known closure-scope bugs that prevent full
execution; this test validates the tokenize → parse → compile pipeline only.
"""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.abspath(os.path.join(ROOT, '..'))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter


def load_hto(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def run_hsharp_source(src, interp):
    lexer = Lexer(src)
    parser = Parser(lexer)
    ast = parser.parse()
    return interp.interpret(ast)


def main():
    interp = Interpreter()

    # Load bootstrap components
    print("=" * 60)
    print("  v0.4.1 Bootstrap Sync Test")
    print("=" * 60)
    print()

    components = ['tokenize', 'parser', 'compiler', 'interpreter']
    for comp in components:
        path = os.path.join(ROOT, f'{comp}.hto')
        if os.path.exists(path):
            print(f"  Loading {comp}.hto...")
            run_hsharp_source(load_hto(path), interp)
        else:
            print(f"  WARNING: {comp}.hto not found")
            sys.exit(1)
    print("  Bootstrap components loaded.")
    print()

    # Read the test file
    test_path = os.path.join(ROOT, 'test_v041_sync.hto')
    test_src = load_hto(test_path)

    results = []

    # Stage 1: Bootstrap tokenize
    print("[Stage 1] Bootstrap tokenize() on v0.4.1 test source...")
    try:
        test_code = f"""
let __test_src = test_source;
let __test_tokens = tokenize(__test_src);
print("tokenize OK: " + str(len(__test_tokens)) + " tokens");
"""
        interp.global_env.define('test_source', test_src)
        run_hsharp_source(test_code, interp)
        results.append(('tokenize', True, ''))
    except Exception as e:
        results.append(('tokenize', False, str(e)))
        print(f"  FAILED: {e}")

    # Stage 2: Bootstrap parse
    print("[Stage 2] Bootstrap parse() on tokenized output...")
    try:
        test_code = """
let __test_ast = parse(__test_tokens);
print("parse OK");
"""
        run_hsharp_source(test_code, interp)
        results.append(('parse', True, ''))
    except Exception as e:
        results.append(('parse', False, str(e)))
        print(f"  FAILED: {e}")

    # Stage 3: Bootstrap compile
    print("[Stage 3] Bootstrap compile() on parsed AST...")
    try:
        test_code = """
let __test_bc = compile(__test_ast);
print("compile OK: " + str(len(__test_bc["instructions"])) + " instructions");
"""
        run_hsharp_source(test_code, interp)
        results.append(('compile', True, ''))
    except Exception as e:
        results.append(('compile', False, str(e)))
        print(f"  FAILED: {e}")

    # Summary
    print()
    print("=" * 60)
    all_ok = True
    for stage, ok, err in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {stage:12s} : {status}")
        if not ok:
            print(f"               Error: {err[:100]}")
            all_ok = False
    print()
    if all_ok:
        print("  v0.4.1 features successfully synced to bootstrap toolchain.")
        print("  tokenize.hto + parser.hto + compiler.hto all handle new syntax.")
    else:
        print("  Some stages failed. See errors above.")
    print("=" * 60)
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
