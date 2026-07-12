#!/usr/bin/env python3
"""Add `let` to class field declarations.

In H#, class fields must be declared with `let`:
    class Foo {
        let x = 1;        # field
        let items = [];   # field
    }

Without `let`, the parser treats the line as a statement and ignores it.
"""
import re
from pathlib import Path


def update_file(text: str) -> str:
    # Match class body lines that look like a field declaration:
    #   whitespace + identifier + whitespace + = + ...
    # but NOT preceded by `let` or `fn` or `private`
    # and NOT a method call (e.g., `push(self.items, v);`)
    # Heuristic: the line starts with whitespace, then an identifier,
    # then ' = ' (not ' == '), then a value, then ';' at end.
    lines = text.split('\n')
    out = []
    in_class = False
    brace_depth = 0
    for line in lines:
        stripped = line.lstrip()
        # Track class context
        if stripped.startswith('class ') and stripped.endswith('{'):
            in_class = True
            brace_depth = 1
            out.append(line)
            continue
        if in_class:
            brace_depth += stripped.count('{') - stripped.count('}')
            if brace_depth <= 0:
                in_class = False
            # Check if this looks like a field declaration
            # Pattern: optional whitespace, identifier, optional whitespace, =, not ==
            m = re.match(r'^(\s+)([a-zA-Z_][a-zA-Z0-9_]*)\s*=(?!=)(.*)$', line)
            if m and not line.rstrip().endswith('{') and not line.rstrip().endswith('}'):
                indent = m.group(1)
                name = m.group(2)
                rest = m.group(3)
                # Skip if it's already 'let' or 'private' or 'fn'
                if not line.lstrip().startswith(('let ', 'private ', 'fn ', '//', '#')):
                    # Skip if the rest is a function call (method call inside class body)
                    # Method calls end with ); or just );
                    if not re.match(r'\s*\(', rest):
                        # Add 'let' before the name
                        new_line = f"{indent}let {name} ={rest}"
                        out.append(new_line)
                        continue
        out.append(line)
    return '\n'.join(out)


def main():
    root = Path("/Users/peddlejumper/H#/v0.4/hsharp-kotlin-compiler/lib-tests/hto")
    n = 0
    for f in sorted(root.glob("*.hto")):
        text = f.read_text(encoding="utf-8")
        new_text = update_file(text)
        if new_text != text:
            f.write_text(new_text, encoding="utf-8")
            print(f"  updated  {f.name}")
            n += 1
    print(f"done: {n} files updated")


if __name__ == "__main__":
    main()
