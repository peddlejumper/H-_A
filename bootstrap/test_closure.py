#!/usr/bin/env python3
"""Test closure semantics in bootstrap VM."""
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


def run(src, interp):
    lexer = Lexer(src)
    parser = Parser(lexer)
    ast = parser.parse()
    return interp.interpret(ast)


def main():
    interp = Interpreter()
    for comp in ['tokenize', 'parser', 'compiler', 'interpreter']:
        run(load_hto(os.path.join(ROOT, f'{comp}.hto')), interp)
    print("Bootstrap loaded.\n")

    import io
    from contextlib import redirect_stdout

    def pipe(snippet):
        """Wrap H# source through bootstrap tokenize→parse→compile→execute."""
        escaped = snippet.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'''
let __src = "{escaped}";
let __t = tokenize(__src);
let __a = parse(__t);
let __bc = compile(__a);
execute(__bc, {{}});
'''

    tests = [
        ("read outer var",
         "let x = 10;\nfn getX() { return x; }\nprint(getX());",
         "10"),
        ("return function (makeAdder)",
         "fn makeAdder(n) {\n  fn adder(x) { return x + n; }\n  return adder;\n}\nlet add5 = makeAdder(5);\nprint(add5(3));",
         "8"),
        ("closure modifies outer",
         "let counter = 0;\nfn inc() { counter = counter + 1; return counter; }\nprint(inc());\nprint(inc());",
         "1\n2"),
        ("nested closures",
         "fn outer() {\n  let a = 1;\n  fn mid() {\n    let b = 2;\n    fn inner() { return a + b; }\n    return inner;\n  }\n  return mid;\n}\nlet m = outer();\nlet i = m();\nprint(i());",
         "3"),
        ("closure captures parameter",
         "fn f(x) {\n  fn g() { return x * 2; }\n  return g;\n}\nlet h = f(21);\nprint(h());",
         "42"),
    ]

    results = []
    for name, src, expected in tests:
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                run(pipe(src), interp)
            got = buf.getvalue().strip()
            ok = got == expected
            results.append((name, ok, got, expected))
            print(f"[{'PASS' if ok else 'FAIL'}] {name}")
            if not ok:
                print(f"   expected: {expected!r}")
                print(f"   got:      {got!r}")
        except Exception as e:
            results.append((name, False, f"ERROR: {e}", expected))
            print(f"[FAIL] {name}  ERROR: {e}")

    n_pass = sum(1 for r in results if r[1])
    print(f"\n{n_pass}/{len(results)} closure tests passed")


if __name__ == '__main__':
    main()
