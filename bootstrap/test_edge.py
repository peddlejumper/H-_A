#!/usr/bin/env python3
"""Comprehensive edge-case tests for bootstrap VM."""
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


def run(src, interp):
    lexer = Lexer(src)
    parser = Parser(lexer)
    ast = parser.parse()
    return interp.interpret(ast)


def pipe(snippet):
    escaped = snippet.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return f'''
let __src = "{escaped}";
let __t = tokenize(__src);
let __a = parse(__t);
let __bc = compile(__a);
execute(__bc, {{}});
'''


def main():
    interp = Interpreter()
    for comp in ['tokenize', 'parser', 'compiler', 'interpreter']:
        run(load_hto(os.path.join(ROOT, f'{comp}.hto')), interp)
    print("Bootstrap loaded.\n")

    tests = [
        # String operations
        ("string indexing",
         'let s = "hello";\nprint(s[1]);',
         "e"),
        ("string length",
         'let s = "hello";\nprint(len(s));',
         "5"),
        ("string concat",
         'let a = "foo";\nlet b = "bar";\nprint(a + b);',
         "foobar"),

        # Dict operations
        ("dict create and access",
         'let d = {"x": 1, "y": 2};\nprint(d["x"]);\nprint(d["y"]);',
         "1\n2"),
        ("dict set item",
         'let d = {};\nd["k"] = 99;\nprint(d["k"]);',
         "99"),

        # List operations
        ("list push and len",
         'let l = [1, 2, 3];\npush(l, 4);\nprint(len(l));\nprint(l[3]);',
         "4\n4"),
        ("list pop",
         'let l = [10, 20, 30];\nlet x = pop(l);\nprint(x);\nprint(len(l));',
         "30\n2"),

        # Nested functions + closures
        ("closure over loop var",
         'let fns = [];\nlet i = 0;\nwhile (i < 3) {\n  let captured = i;\n  fn make_fn(c) {\n    fn inner() { return c; }\n    return inner;\n  }\n  push(fns, make_fn(captured));\n  i = i + 1;\n}\nprint(fns[0]());\nprint(fns[1]());\nprint(fns[2]());',
         "0\n1\n2"),

        # Class with method using closure
        ("class method calls global fn",
         'fn helper(x) { return x + 100; }\nclass C {\n  fn work(self, n) { return helper(n); }\n}\nlet c = new C();\nprint(c.work(5));',
         "105"),

        # Class inheritance
        ("class inheritance basic",
         'class Animal {\n  fn init(self, n) { self.name = n; }\n  fn speak(self) { return self.name; }\n}\nclass Dog {\n  fn bark(self) { return self.name + " woof"; }\n}\nlet a = new Animal("Rex");\nprint(a.speak());',
         "Rex"),

        # Recursion + closure
        ("recursive closure (fib)",
         'fn make_fib() {\n  fn fib(n) {\n    if (n < 2) { return n; }\n    return fib(n - 1) + fib(n - 2);\n  }\n  return fib;\n}\nlet f = make_fib();\nprint(f(10));',
         "55"),

        # Match with closure binding
        ("match binding used in closure",
         'fn test(x) {\n  return match x {\n    v => {\n      fn double(y) { return y * 2; }\n      return double(v);\n    }\n  };\n}\nprint(test(21));',
         "42"),

        # For loop with closure
        ("for loop sum with helper",
         'fn add(a, b) { return a + b; }\nlet items = [1, 2, 3, 4, 5];\nlet s = 0;\nfor x in items {\n  s = add(s, x);\n}\nprint(s);',
         "15"),

        # Nested function modifying outer
        ("nested fn modifies outer var",
         'let x = 10;\nfn inc() { x = x + 5; return x; }\nprint(inc());\nprint(x);',
         "15\n15"),

        # Multiple closures share state
        ("shared state via closures",
         'fn make_counter() {\n  let count = 0;\n  fn inc() { count = count + 1; return count; }\n  fn get() { return count; }\n  return inc;\n}\nlet c = make_counter();\nprint(c());\nprint(c());\nprint(c());',
         "1\n2\n3"),

        # String comparison
        ("string equality",
         'let a = "hello";\nlet b = "hello";\nprint(a == b);\nprint(a != "world");',
         "true\ntrue"),

        # Boolean operations
        ("boolean and/or",
         'print(true and false);\nprint(true or false);\nprint(not false);',
         "false\ntrue\ntrue"),

        # Negative numbers
        ("negative arithmetic",
         'let x = -5;\nprint(x + 10);\nprint(0 - 3);',
         "5\n-3"),

        # Dict iteration
        ("dict iteration",
         'let d = {"a": 1, "b": 2};\nfor k, v in d {\n  print(k);\n  print(v);\n}',
         "a\n1\nb\n2"),
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
    print(f"\n{n_pass}/{len(results)} edge-case tests passed")
    return 0 if n_pass == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
