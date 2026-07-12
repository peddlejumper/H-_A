#!/usr/bin/env python3
"""
Stress test runner for 09_parallel_channel.
Compiles each .hto to .hbc, runs on the Kotlin HVM, parses PASS/FAIL.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/Users/peddlejumper/H#/v0.4")
WORK = ROOT / "stress_test" / "09_parallel_channel"
HBC_DIR = WORK / "hbc"
OUT_DIR = WORK / "out"
HBC_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

COMPILER_TEST = ROOT / "HSharp_v0.4_Tests" / "compile_test.py"
KT_JAR = ROOT / "hsharp-kotlin-compiler" / "build" / "libs" / "hsharp-kotlin-compiler.jar"

TIMEOUT = 60  # seconds per test

def collect_tests():
    tests = sorted(WORK.glob("[0-9][0-9]_*.hto"))
    return tests

def compile_one(hto_path):
    hbc_path = HBC_DIR / (hto_path.stem + ".hbc")
    proc = subprocess.run(
        ["python3", str(COMPILER_TEST), str(hto_path), str(hbc_path)],
        capture_output=True, text=True, timeout=30,
    )
    return proc.returncode == 0, proc.stdout + proc.stderr, hbc_path

def run_one(hbc_path):
    proc = subprocess.run(
        ["java", "-jar", str(KT_JAR), "run", str(hbc_path)],
        capture_output=True, text=True, timeout=TIMEOUT,
    )
    return proc.returncode, proc.stdout, proc.stderr

def parse_pass_fail(stdout):
    m = re.search(r"PC_TEST\s*:\s*PASS=(\d+)\s+FAIL=(\d+)", stdout)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None

def main():
    tests = collect_tests()
    if not tests:
        print("no tests found")
        return 1
    print(f"running {len(tests)} tests\n")
    results = []
    total_pass = 0
    total_fail = 0
    for hto in tests:
        name = hto.stem
        print(f"=== {name} ===")
        # compile
        try:
            ok, cerr, hbc_path = compile_one(hto)
        except subprocess.TimeoutExpired:
            print("  COMPILE TIMEOUT")
            results.append((name, "compile-timeout", 0, 0, "", ""))
            continue
        if not ok:
            print("  COMPILE FAILED:")
            print(cerr)
            results.append((name, "compile-fail", 0, 0, cerr, ""))
            continue
        # run
        t0 = time.time()
        try:
            rc, stdout, stderr = run_one(hbc_path)
        except subprocess.TimeoutExpired:
            elapsed = time.time() - t0
            print(f"  RUN TIMEOUT ({elapsed:.1f}s)")
            results.append((name, "run-timeout", 0, 0, "", ""))
            continue
        elapsed = time.time() - t0
        p, f = parse_pass_fail(stdout)
        if p is None:
            print(f"  NO PASS/FAIL LINE (rc={rc}, {elapsed:.2f}s)")
            if stdout.strip():
                print("  --- stdout (tail) ---")
                for line in stdout.strip().splitlines()[-15:]:
                    print("    " + line)
            if stderr.strip():
                print("  --- stderr (tail) ---")
                for line in stderr.strip().splitlines()[-15:]:
                    print("    " + line)
            results.append((name, "no-summary", 0, 0, stdout, stderr))
            continue
        total_pass += p
        total_fail += f
        status = "PASS" if f == 0 else "FAIL"
        print(f"  {status}  PASS={p} FAIL={f}  ({elapsed:.2f}s)")
        if f > 0:
            # print FAIL lines
            for line in stdout.splitlines():
                if line.startswith("FAIL "):
                    print("    " + line)
            if stderr.strip():
                print("  --- stderr (tail) ---")
                for line in stderr.strip().splitlines()[-10:]:
                    print("    " + line)
        # save full output
        out_path = OUT_DIR / (name + ".out")
        out_path.write_text(stdout + ("\n--- stderr ---\n" + stderr if stderr else ""))
        results.append((name, status, p, f, stdout, stderr))
    print()
    print("=" * 60)
    print(f"TOTAL: PASS={total_pass} FAIL={total_fail}")
    print("=" * 60)
    print()
    # summary table
    print(f"{'test':<40} {'status':<12} {'pass':>5} {'fail':>5}")
    print("-" * 65)
    for name, status, p, f, _, _ in results:
        print(f"{name:<40} {status:<12} {p:>5} {f:>5}")
    return 0 if total_fail == 0 and all(r[1] in ("PASS",) for r in results) else 1

if __name__ == "__main__":
    sys.exit(main())
