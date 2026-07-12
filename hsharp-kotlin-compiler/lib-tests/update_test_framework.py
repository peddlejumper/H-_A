#!/usr/bin/env python3
"""Update all 14 lib-test .hto files to use a mutable __stats list
so the check() function can communicate results back to the module-level
print statement.

Old pattern:
    let __passed = 0;
    let __failed = 0;
    let __failed_names = [];
    fn check(name, cond) {
        if (cond) { __passed = __passed + 1; }
        else { __failed = __failed + 1; push(__failed_names, name); }
    }
    ...
    print("XX_LIB : PASS=" + str(__passed) + " FAIL=" + str(__failed));
    if (__failed > 0) { ... __failed_names ... }

New pattern (uses a single mutable HList so closure-cell mutations
are visible to the module-level code):
    let __stats = [0, 0, []];   # [passed, failed, failed_names]
    fn check(name, cond) {
        if (cond) { __stats[0] = __stats[0] + 1; }
        else { __stats[1] = __stats[1] + 1; push(__stats[2], name); }
    }
    ...
    print("XX_LIB : PASS=" + str(__stats[0]) + " FAIL=" + str(__stats[1]));
    if (__stats[1] > 0) { ... __stats[2] ... }
"""
import re
import sys
from pathlib import Path

OLD_HEADER = """let __passed = 0;
let __failed = 0;
let __failed_names = [];

fn check(name, cond) {
    if (cond) {
        __passed = __passed + 1;
    } else {
        __failed = __failed + 1;
        push(__failed_names, name);
    }
}"""

NEW_HEADER = """let __stats = [0, 0, []];   # [passed, failed, failed_names]

fn check(name, cond) {
    if (cond) {
        __stats[0] = __stats[0] + 1;
    } else {
        __stats[1] = __stats[1] + 1;
        push(__stats[2], name);
    }
}"""


def update_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    # Replace the header
    if OLD_HEADER in text:
        text = text.replace(OLD_HEADER, NEW_HEADER)
    else:
        print(f"  WARNING: header not found in {path.name}", file=sys.stderr)
        return False
    # Replace the print-summary lines
    text = re.sub(
        r'print\("([A-Z0-9_]+)\s*:?\s*PASS="\s*\+\s*str\(__passed\)\s*\+\s*" FAIL="\s*\+\s*str\(__failed\)\s*\+\s*"\);',
        r'print("\1 : PASS=" + str(__stats[0]) + " FAIL=" + str(__stats[1]));',
        text,
    )
    # Replace the failed-tests loop
    text = text.replace("if (__failed > 0) {", "if (__stats[1] > 0) {")
    text = text.replace("__failed_names[", "__stats[2][")
    text = text.replace("i < len(__failed_names)", "i < len(__stats[2])")
    if text == orig:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def main():
    root = Path("/Users/peddlejumper/H#/v0.4/hsharp-kotlin-compiler/lib-tests/hto")
    n = 0
    for f in sorted(root.glob("*.hto")):
        if update_file(f):
            print(f"  updated {f.name}")
            n += 1
        else:
            print(f"  skipped {f.name}")
    print(f"done: {n} files updated")


if __name__ == "__main__":
    main()
