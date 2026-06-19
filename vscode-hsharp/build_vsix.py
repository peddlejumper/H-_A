#!/usr/bin/env python3
"""Build a .vsix file from a vscode-hsharp/ source tree without needing vsce/node.

A .vsix is just a zip archive with:
  - [Content_Types].xml at root
  - all extension files under extension/ prefix
"""
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT  # output to vscode-hsharp/

def add_file(zf: zipfile.ZipFile, abs_path: Path, arcname: str):
    zf.write(abs_path, arcname)
    print(f"  + {arcname}  ({abs_path.stat().st_size:>8} bytes)")

def main():
    out = DIST / "hsharp-language-0.4.1.vsix"
    if out.exists():
        out.unlink()

    # Files to include, in the order they appeared in the original 0.4.0 vsix
    files = [
        "[Content_Types].xml",
        ".vscodeignore",
        "package.json",
        "LICENSE.txt",
        "language-configuration.json",
        "extension.vsixmanifest",
        "extension.js",
        ".vsixignore",
        "snippets/hsharp.json",
        "python/compiler.py",
        "python/h_ast.py",
        "python/tokens.py",
        "python/parser.py",
        "python/lexer.py",
        "python/hsharp_compile.py",
        "images/hsharp-icon.svg",
        "images/hsharp-icon.png",
        "lib/hsharp-kotlin-compiler.jar",
        "lib/hsharp-runtime.jar",
        "syntaxes/hsharp.tmLanguage.json",
    ]

    print(f"Building {out}")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            abs_path = ROOT / f
            if not abs_path.exists():
                print(f"  ! MISSING: {f}")
                continue
            add_file(zf, abs_path, f"extension/{f}")

    size = out.stat().st_size
    print(f"\nDone. {out}  ({size:>10,} bytes, {size/1024/1024:.2f} MB)")

if __name__ == "__main__":
    main()
