#!/usr/bin/env python3
"""
Transform hwdui.hto from `for x in y { ... }` to while-loop form so the
H# Python compiler (which doesn't support Python-style for-in) can compile it.

Algorithm: find `for <var> in <expr> {` lines, then walk forward tracking
brace depth, then replace the entire `for ... }` block with a synthetic
iterator and a while loop over the original body.

We track { and } depth so nested blocks are preserved correctly.
"""
import re
import sys


def transform(src: str) -> str:
    out_lines = []
    lines = src.split("\n")
    counter = [0]

    pat_in_body = re.compile(r"(\b\w[\w.]*)\s+in\s+(\w[\w.]*)\b")

    def replace_in(line: str) -> str:
        def sub(m: re.Match) -> str:
            return f"__contains({m.group(2)}, {m.group(1)})"
        return pat_in_body.sub(sub, line)

    def process(start: int, end: int, base_indent: str = "") -> int:
        """Process lines[start:end] in place, appending to out_lines.
        Returns the next unprocessed index."""
        i = start
        while i < end:
            line = lines[i]
            # Single-line for-in: `for x in y { stmts }`
            m1 = re.match(r"^(\s*)for\s+(\w+)\s+in\s+(.+?)\s*\{\s*(.+)\}\s*$", line)
            # Multi-line for-in: `for x in y {` (no closing `}` on same line)
            m2 = re.match(r"^(\s*)for\s+(\w+)\s+in\s+(.+?)\s*\{\s*$", line)
            if m1 or m2:
                if m1:
                    indent, var, expr, body_inline = (
                        m1.group(1), m1.group(2), m1.group(3), m1.group(4).strip()
                    )
                    body = [body_inline]
                    j = i
                else:
                    indent, var, expr = m2.group(1), m2.group(2), m2.group(3)
                    body_indent_tmp = indent + "    "
                    depth = 1
                    j = i + 1
                    while j < end:
                        l = lines[j]
                        opens = l.count("{")
                        closes = l.count("}")
                        depth += opens - closes
                        if depth == 0:
                            break
                        j += 1
                    if depth != 0:
                        raise RuntimeError(f"Unbalanced for-in at line {i+1}")
                    body = lines[i + 1 : j]

                body_indent = indent + "    "
                counter[0] += 1
                cid = counter[0]
                out_lines.append(f"{indent}let __iter{cid} = {expr};")
                out_lines.append(f"{indent}let __i{cid} = 0;")
                out_lines.append(
                    f"{indent}while (__i{cid} < len(__iter{cid})) {{"
                )
                out_lines.append(f"{body_indent}let {var} = __iter{cid}[__i{cid}];")
                # Recursively process the body so nested for-in is handled.
                if m1:
                    # single-line: no nested lines exist
                    out_lines.extend([f"{body_indent}{bl}" for bl in body])
                else:
                    process(i + 1, j)
                out_lines.append(f"{body_indent}__i{cid} = __i{cid} + 1;")
                out_lines.append(f"{indent}}}")
                i = j + 1
                continue
            out_lines.append(line)
            i += 1
        return i

    process(0, len(lines))

    # Second pass: replace Python-style `x in collection` membership test
    # outside of for-in with a `__contains(collection, x)` builtin call.
    out_lines = [replace_in(l) for l in out_lines]
    return "\n".join(out_lines)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: transform_for_in.py <input.hto> <output.hto>")
        sys.exit(1)
    with open(sys.argv[1], "r") as f:
        s = f.read()
    out = transform(s)
    with open(sys.argv[2], "w") as f:
        f.write(out)
    print(f"transformed {len(s)} bytes -> {len(out)} bytes")
