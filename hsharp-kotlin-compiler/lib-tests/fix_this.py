#!/usr/bin/env python3
"""Replace `this` with `self` in class methods, since H# uses `self`."""
import re
from pathlib import Path


def update_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    # Replace this.xxx with self.xxx, this = ... with self = ...
    text = re.sub(r'\bthis\.', 'self.', text)
    text = re.sub(r'\bthis\b', 'self', text)
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
