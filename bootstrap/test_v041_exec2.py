#!/usr/bin/env python3
"""Test bootstrap VM execution of v0.4.1 features.

Validates that the bootstrap VM can actually execute bytecode
containing v0.4.1 new features (not just tokenize→parse→compile).
"""
import os, sys, io
from contextlib import redirect_stdout

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
    print("=" * 60)
    print("  Bootstrap VM v0.4.1 Feature Execution Test")
    print("=" * 60)
    print()

    components = ['tokenize', 'parser', 'compiler', 'interpreter']
    for comp in components:
        path = os.path.join(ROOT, f'{comp}.hto')
        run_hsharp_source(load_hto(path), interp)
    print("  Bootstrap components loaded.")
    print()

    results = []

    def run_test(name, src, expected_output=None):
        print(f"[Test] {name}")
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                run_hsharp_source(src, interp)
            output = buf.getvalue().strip()
            if expected_output is not None:
                if output == expected_output:
                    print(f"  PASS (output: {output})")
                    results.append((name, True, ''))
                else:
                    print(f"  FAIL: expected '{expected_output}', got '{output}'")
                    results.append((name, False, f'expected {expected_output!r}, got {output!r}'))
            else:
                print(f"  OK (output: {output[:100]})")
                results.append((name, True, output))
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append((name, False, str(e)[:120]))

    def pipe(snippet):
        """Wrap a H# source snippet through bootstrap tokenize→parse→compile→execute."""
        # Escape for embedding in H# string
        escaped = snippet.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'''
let __src = "{escaped}";
let __t = tokenize(__src);
let __a = parse(__t);
let __bc = compile(__a);
execute(__bc, {{}});
'''

    # Test 1: class with init (new convention)
    run_test("class with init (new Box(42))", pipe(
        'class Box {\n  let value = 0;\n  fn init(self, v) { self.value = v; }\n  fn get(self) { return self.value; }\n}\nlet b = new Box(42);\nprint(b.get());\n'
    ), "42")

    # Test 2: class without init (field default)
    run_test("class field default (Point)", pipe(
        'class Point {\n  let x = 10;\n  let y = 20;\n}\nlet p = new Point();\nprint(p.x);\nprint(p.y);\n'
    ), "10\n20")

    # Test 3: match expression - literal pattern
    run_test("match literal (1=>one)", pipe(
        'fn describe(x) {\n  return match x {\n    1 => "one",\n    42 => "answer",\n    _ => "other"\n  };\n}\nprint(describe(1));\nprint(describe(42));\nprint(describe(99));\n'
    ), "one\nanswer\nother")

    # Test 4: match expression - binding pattern
    run_test("match binding (v=>v)", pipe(
        'fn identity(x) {\n  return match x {\n    v => v\n  };\n}\nprint(identity(7));\n'
    ), "7")

    # Test 5: match expression - guard
    run_test("match guard (sign)", pipe(
        'fn sign(x) {\n  return match x {\n    n if n > 0 => "pos",\n    n if n < 0 => "neg",\n    _ => "zero"\n  };\n}\nprint(sign(5));\nprint(sign(0));\nprint(sign(-3));\n'
    ), "pos\nzero\nneg")

    # Test 6: union declaration + construction
    run_test("union construct (Shape)", pipe(
        'union Shape {\n  Circle: r;\n  Rect: w, h;\n  Point;\n}\nlet c = Shape{Circle: 7};\nprint(c.__variant__);\nprint(c.r);\nlet r = Shape{Rect: 3, 4};\nprint(r.__variant__);\nprint(r.w);\nprint(r.h);\nlet p = Shape{Point};\nprint(p.__variant__);\n'
    ), "Circle\n7\nRect\n3\n4\nPoint")

    # Test 7: match with variant pattern
    run_test("match variant (Option)", pipe(
        'union Opt {\n  Some: val;\n  None;\n}\nfn unwrap(o) {\n  return match o {\n    Some(v) => v,\n    None => "nothing",\n    _ => "other"\n  };\n}\nlet s = Opt{Some: 99};\nlet n = Opt{None};\nprint(unwrap(s));\nprint(unwrap(n));\n'
    ), "99\nnothing")

    # Test 8: ? error propagation
    run_test("? propagate (ok)", pipe(
        'fn risky(n) {\n  if (n < 0) {\n    throw "neg";\n  }\n  return n * 2;\n}\nlet v = risky(5)?;\nprint(v);\n'
    ), "10")

    # Test 9: ? error propagation - error case
    run_test("? propagate (err)", pipe(
        'fn risky(n) {\n  if (n < 0) {\n    throw "neg";\n  }\n  return n * 2;\n}\nlet v = risky(-1)?;\nprint(v);\n'
    ), "neg")

    # Test 10: nested function calls
    run_test("nested calls (add(square(3),4)=13)", pipe(
        'fn square(n) { return n * n; }\nfn add(a, b) { return a + b; }\nprint(add(square(3), 4));\n'
    ), "13")

    # Test 11: recursion (factorial)
    run_test("recursion (factorial 5=120)", pipe(
        'fn fact(n) {\n  if (n <= 1) { return 1; }\n  return n * fact(n - 1);\n}\nprint(fact(5));\n'
    ), "120")

    # Test 12: for loop over list
    run_test("for loop (sum list)", pipe(
        'let items = [1, 2, 3, 4, 5];\nlet s = 0;\nfor x in items {\n  s = s + x;\n}\nprint(s);\n'
    ), "15")

    # Summary
    print()
    print("=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    for name, ok, err in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {name:40s} : {status}")
        if not ok:
            print(f"    {err[:120]}")
    print()
    print(f"  {passed}/{total} tests passed")
    if passed == total:
        print("  Bootstrap VM v0.4.1 execution: FULL SUCCESS")
    else:
        print(f"  Bootstrap VM v0.4.1 execution: {total - passed} failures")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
