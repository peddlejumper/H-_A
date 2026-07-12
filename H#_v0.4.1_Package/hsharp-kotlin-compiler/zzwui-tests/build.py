#!/usr/bin/env python3
"""
build.py — Compose zzwui test hbc files by prepending hwdui_min.hto and
zzw_render.hto / zzw_native.hto before the test body. The H# Python
compiler doesn't itself process `import` statements, so we substitute
the imported modules by source concatenation.

A test may include a magic comment near the top to control which modules
get prepended:
    # build: hwdui_min.hto
    # build: zzw_render.hto
    # build: zzw_native.hto
If no `# build:` comment is found, the test gets the full default stack
(hwdui_min.hto, zzw_native.hto, zzw_render.hto).
"""
import os
import re
import subprocess
import sys

HTO_DIR = os.path.join(os.path.dirname(__file__), "hto")
HBC_DIR = os.path.join(os.path.dirname(__file__), "hbc")
HSDIR = "/Users/peddlejumper/H#/v0.4/HSharp_v0.4_Tests"
COMPILER = os.path.join(HSDIR, "compile_test.py")

DEFAULT_DEPS = ["hwdui_min.hto", "zzw_native.hto", "zzw_render_min.hto"]


def deps_for(hto_name: str) -> list[str]:
    src_path = os.path.join(HTO_DIR, hto_name)
    with open(src_path, "r") as f:
        src = f.read()
    # Each `# build:` line may list one or more comma-separated modules.
    found: list[str] = []
    for m in re.finditer(r"^\s*#\s*build:\s*(.+?)\s*$", src, flags=re.M):
        for tok in m.group(1).split(","):
            tok = tok.strip()
            if tok:
                found.append(tok)
    if found:
        return list(found)
    return list(DEFAULT_DEPS)


def build_one(hto_name: str, hbc_name: str, deps: list[str]) -> str:
    src_path = os.path.join(HTO_DIR, hto_name)
    with open(src_path, "r") as f:
        body = f.read()
    # Strip the `# build:` directive lines out of the body before composing.
    body = re.sub(r"^\s*#\s*build:\s*.+?\n", "", body, flags=re.M)
    parts = []
    for d in deps:
        with open(os.path.join(HTO_DIR, d), "r") as f:
            parts.append("# ── begin dep " + d + " ──\n" + f.read() + "\n# ── end dep " + d + " ──\n")
    composed = "".join(parts) + "\n" + body
    tmp_src = os.path.join(HTO_DIR, ".composed_" + hto_name)
    with open(tmp_src, "w") as f:
        f.write(composed)
    hbc_path = os.path.join(HBC_DIR, hbc_name)
    proc = subprocess.run(
        ["python3", COMPILER, tmp_src, hbc_path],
        capture_output=True, text=True,
    )
    os.unlink(tmp_src)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"compile failed for {hto_name}")
    return hbc_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: build.py <test_name> [...]")
        sys.exit(1)
    for t in sys.argv[1:]:
        hto = t if t.endswith(".hto") else (t + ".hto")
        base = hto[:-4] if hto.endswith(".hto") else hto
        hto_name = base + ".hto"
        hbc_name = base + ".hbc"
        deps = deps_for(hto_name)
        path = build_one(hto_name, hbc_name, deps)
        print(f"built {hto_name} -> {os.path.basename(path)} (deps: {', '.join(deps)})")

