#!/usr/bin/env python3
"""Runner: execute each .hto test in tree mode and bytecode mode, compare."""
import os
import subprocess
import sys

ROOT = "/Users/peddlejumper/H#/v0.4"
WORK = os.path.join(ROOT, "stress_test/03_python_vm")
OUT = os.path.join(WORK, "out")
HSHARP = os.path.join(ROOT, "hsharp.py")
os.makedirs(OUT, exist_ok=True)

tests = sorted(f for f in os.listdir(WORK) if f.startswith("t") and f.endswith(".hto"))

TIMEOUT = 90


def run(cmd, cwd=WORK):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "TIMEOUT after %ds" % TIMEOUT
    except Exception as e:
        return 125, "", "RUNNER ERROR: %s" % e


summary = []
for t in tests:
    base = t[:-4]
    tree_log = ["===== TREE ====="]
    rc, out, err = run([sys.executable, HSHARP, t])
    tree_log.append("$?=%d" % rc)
    if out:
        tree_log.append(out)
    if err:
        tree_log.append("[stderr]\n" + err)
    with open(os.path.join(OUT, base + ".tree.txt"), "w") as f:
        f.write("\n".join(tree_log))

    bc_log = ["===== EMIT ====="]
    rc1, out1, err1 = run([sys.executable, HSHARP, "--emit-bc", t])
    bc_log.append("$?=%d" % rc1)
    if out1:
        bc_log.append(out1)
    if err1:
        bc_log.append("[stderr]\n" + err1)

    bc_log.append("===== RUNBC =====")
    hbc = os.path.join(WORK, base + ".hbc")
    rc2, out2, err2 = run([sys.executable, HSHARP, "--run-bc", hbc])
    bc_log.append("$?=%d" % rc2)
    if out2:
        bc_log.append(out2)
    if err2:
        bc_log.append("[stderr]\n" + err2)
    with open(os.path.join(OUT, base + ".bc.txt"), "w") as f:
        f.write("\n".join(bc_log))

    status = "OK" if (rc == 0 and rc2 == 0 and out == out2) else "DIFF/ERR"
    summary.append((t, rc, rc2, status))
    print("%-32s tree=%d bc=%d  %s" % (t, rc, rc2, status))

print("\n==== SUMMARY ====")
for t, r1, r2, s in summary:
    print("%-32s tree_rc=%d bc_rc=%d  %s" % (t, r1, r2, s))
