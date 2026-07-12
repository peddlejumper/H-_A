#!/usr/bin/env python3
"""Fix the print-summary lines in all 14 lib-test .hto files using
simple string replacement (more robust than regex)."""
import sys
from pathlib import Path


def update_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    # Replace patterns like str(__passed) and str(__failed) in print statements
    text = text.replace("str(__passed)", "str(__stats[0])")
    text = text.replace("str(__failed)", "str(__stats[1])")
    # Replace __failed > 0 (already done) and __failed_names
    if text == orig:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def main():
    root = Path("/Users/peddlejumper/H#/v0.4/hsharp-kotlin-compiler/lib-tests/hto")
    n = 0
    for f in sorted(root.glob("*.hto")):
        if update_file(f):
            print(f"  updated  {f.name}")
            n += 1
    print(f"done: {n} files updated")


if __name__ == "__main__":
    main()
