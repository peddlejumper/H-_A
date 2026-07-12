#!/usr/bin/env python3
"""Run all 13_worker_pool .hbc tests through the Kotlin HVM with per-test timeout."""
import subprocess, sys, time, os, glob, re

JAR = "/Users/peddlejumper/H#/v0.4/hsharp-kotlin-compiler/build/libs/hsharp-kotlin-compiler.jar"
DIR = "/Users/peddlejumper/H#/v0.4/stress_test/13_worker_pool"
TIMEOUT = 45

def main():
    hbcs = sorted(glob.glob(os.path.join(DIR, "[0-9][0-9]_*.hbc")))
    results = []
    for hbc in hbcs:
        name = os.path.basename(hbc)
        t0 = time.time()
        try:
            p = subprocess.run(["java", "-jar", JAR, "run", hbc],
                               capture_output=True, text=True, timeout=TIMEOUT)
            dt = time.time() - t0
            results.append((name, p.returncode, dt, p.stdout, p.stderr, False))
        except subprocess.TimeoutExpired as e:
            dt = time.time() - t0
            out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            err = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            results.append((name, -9, dt, out, err + f"\n[TIMEOUT {TIMEOUT}s]", True))
    # print details
    for name, rc, dt, out, err, to in results:
        print("=" * 70)
        print(f"### {name}  rc={rc}  dt={dt:.2f}s  timeout={to}")
        print("--- stdout ---")
        print(out)
        if err.strip():
            print("--- stderr ---")
            print(err)
    # summary
    print("=" * 70)
    print("### SUMMARY")
    total_pass = 0
    total_fail = 0
    for name, rc, dt, out, err, to in results:
        m = re.search(r"PASS=(\d+)\s+FAIL=(\d+)", out)
        if m:
            p, f = int(m.group(1)), int(m.group(2))
            total_pass += p
            total_fail += f
            status = "OK" if (rc == 0 and f == 0 and not to) else "ISSUE"
            print(f"  {status:5} {name:45} P={p:3} F={f:3} rc={rc} dt={dt:.1f}s {'TIMEOUT' if to else ''}")
        else:
            total_fail += 1
            print(f"  CRASH {name:45} (no summary line) rc={rc} dt={dt:.1f}s {'TIMEOUT' if to else ''}")
    print(f"\nTOTAL: PASS={total_pass} FAIL={total_fail}")

if __name__ == "__main__":
    main()
