#!/usr/bin/env python3
"""
H# Stress Test Runner — 01_compiler_basic
Runs each .hto test against Python VM and Kotlin HVM, compares outputs.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/peddlejumper/H#/v0.4")
WORK = ROOT / "stress_test" / "01_compiler_basic"
HSHARP = ROOT / "hsharp.py"
COMPILE_TEST = ROOT / "HSharp_v0.4_Tests" / "compile_test.py"
KT_JAR = ROOT / "hsharp-kotlin-compiler" / "build" / "libs" / "hsharp-kotlin-compiler.jar"
HBC_DIR = WORK / "hbc"
OUT_DIR = WORK / "out"

HBC_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

TESTS = sorted([p for p in WORK.glob("test*.hto")])

def run(cmd, timeout=30):
    """Run a command, return (returncode, stdout, stderr)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "TIMEOUT"
    except Exception as e:
        return 125, "", str(e)

def run_python_vm(hto_path):
    """Run via Python VM (interpreter)."""
    return run(["python3", str(HSHARP), str(hto_path)])

def run_kotlin_hvm(hto_path, name):
    """Compile to .hbc (proper format) and run via Kotlin HVM."""
    hbc_path = HBC_DIR / (name + ".hbc")
    # Step 1: compile using compile_test.py (proper modules-wrapped format)
    rc, so, se = run(["python3", str(COMPILE_TEST), str(hto_path), str(hbc_path)])
    if rc != 0:
        return rc, so, f"[compile_test.py failed] {se}"
    # Step 2: run via Kotlin HVM
    return run(["java", "-jar", str(KT_JAR), "run", str(hbc_path)])

def run_official_emit_bc(hto_path, name):
    """Test the official workflow: hsharp.py --emit-bc then Kotlin HVM run.
    Returns (rc, stdout, stderr)."""
    hbc_path = HBC_DIR / (name + "_official.hbc")
    rc, so, se = run(["python3", str(HSHARP), "--emit-bc", str(hto_path)])
    if rc != 0:
        return rc, so, se
    # The --emit-bc writes to <name>.hbc in the same dir as the .hto
    emitted = hto_path.with_suffix(".hbc")
    if emitted.exists():
        # move to our hbcd dir
        target = hbc_path
        target.write_text(emitted.read_text())
        emitted.unlink()
    return run(["java", "-jar", str(KT_JAR), "run", str(hbc_path)])

def normalize(s):
    """Normalize output for comparison: strip trailing whitespace per line."""
    if not s:
        return ""
    return "\n".join(line.rstrip() for line in s.splitlines()).strip()

def main():
    print(f"=== H# Stress Test: 01_compiler_basic ===")
    print(f"Tests found: {len(TESTS)}\n")

    results = []
    py_pass = 0
    kt_pass = 0
    inconsistent = 0
    bugs = []

    for t in TESTS:
        name = t.stem
        print(f"--- {name} ---")

        # Python VM
        py_rc, py_out, py_err = run_python_vm(t)
        py_combined = (py_out + py_err).strip()
        py_ok = py_rc == 0
        if py_ok:
            py_pass += 1

        # Kotlin HVM (via compile_test.py for proper hbc format)
        kt_rc, kt_out, kt_err = run_kotlin_hvm(t, name)
        kt_combined = (kt_out + kt_err).strip()
        kt_ok = kt_rc == 0
        if kt_ok:
            kt_pass += 1

        # Compare outputs (only if both ran)
        py_norm = normalize(py_out)
        kt_norm = normalize(kt_out)
        match = (py_norm == kt_norm) if (py_ok and kt_ok) else None

        if py_ok and kt_ok and not match:
            inconsistent += 1
            bugs.append({
                "test": name,
                "file": str(t),
                "type": "output_mismatch",
                "py_out": py_out,
                "kt_out": kt_out,
                "py_err": py_err,
                "kt_err": kt_err,
            })

        # If both errored but with different messages, note as inconsistency
        if not py_ok and not kt_ok:
            # both failed - check if for similar reasons (syntax errors etc.)
            # treat as consistent if both report errors (we just note)
            pass
        elif not py_ok and kt_ok:
            # Python failed but Kotlin passed
            inconsistent += 1
            bugs.append({
                "test": name,
                "file": str(t),
                "type": "py_fail_kt_pass",
                "py_out": py_out,
                "kt_out": kt_out,
                "py_err": py_err,
                "kt_err": kt_err,
            })
        elif py_ok and not kt_ok:
            # Python passed but Kotlin failed
            inconsistent += 1
            bugs.append({
                "test": name,
                "file": str(t),
                "type": "py_pass_kt_fail",
                "py_out": py_out,
                "kt_out": kt_out,
                "py_err": py_err,
                "kt_err": kt_err,
            })

        print(f"  PY: rc={py_rc} out={py_out!r} err={py_err!r}")
        print(f"  KT: rc={kt_rc} out={kt_out!r} err={kt_err!r}")
        if match is False:
            print(f"  !! OUTPUT MISMATCH")
        print()

        results.append({
            "test": name,
            "py_rc": py_rc, "py_out": py_out, "py_err": py_err,
            "kt_rc": kt_rc, "kt_out": kt_out, "kt_err": kt_err,
            "match": match,
        })

    # Test the official --emit-bc workflow
    print("=== Testing official --emit-bc workflow ===")
    sample = TESTS[1] if len(TESTS) > 1 else TESTS[0]
    rc, out, err = run_official_emit_bc(sample, sample.stem + "_official")
    print(f"  Sample: {sample.name}")
    print(f"  rc={rc}")
    print(f"  out={out!r}")
    print(f"  err={err!r}")
    if "missing 'modules'" in err:
        bugs.append({
            "test": "official_emit_bc_workflow",
            "file": "hsharp.py --emit-bc",
            "type": "emit_bc_format_incompatible",
            "description": "hsharp.py --emit-bc generates flat .hbc without 'modules' wrapper; Kotlin HVM rejects with \"Invalid HBC: missing 'modules' object\"",
            "py_out": out,
            "kt_out": "",
            "py_err": "",
            "kt_err": err,
        })
        inconsistent += 1
    print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Test cases: {len(TESTS)}")
    print(f"Python VM pass: {py_pass}/{len(TESTS)}")
    print(f"Kotlin HVM pass: {kt_pass}/{len(TESTS)}")
    print(f"Behavior inconsistencies: {inconsistent}")
    print()
    if bugs:
        print("BUGS / ISSUES:")
        for i, b in enumerate(bugs, 1):
            print(f"  [{i}] test={b['test']} type={b['type']}")
            print(f"      file={b['file']}")
            if 'description' in b:
                print(f"      desc={b['description']}")
            print(f"      PY out: {b.get('py_out','')!r}")
            print(f"      KT out: {b.get('kt_out','')!r}")
            print(f"      PY err: {b.get('py_err','')!r}")
            print(f"      KT err: {b.get('kt_err','')!r}")

    # Save detailed results
    with open(OUT_DIR / "results.json", "w") as f:
        json.dump({"results": results, "bugs": bugs,
                   "summary": {"tests": len(TESTS), "py_pass": py_pass,
                               "kt_pass": kt_pass, "inconsistent": inconsistent}},
                  f, indent=2, default=str)
    print(f"\nDetailed results: {OUT_DIR / 'results.json'}")

if __name__ == "__main__":
    main()
