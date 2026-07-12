#!/usr/bin/env python3
"""HbcReader + fixForLoopJumps + MiniJson 高强度测试 runner.

对比 PY-OPT (Python 字节码 VM, 参考真相) 与 Kotlin HVM 输出。
重点找 fixForLoopJumps 未正确触发导致的死循环/越界。
"""
import json
import os
import subprocess
import sys
import time

ROOT = "/Users/peddlejumper/H#/v0.4"
HSHARP = os.path.join(ROOT, "hsharp.py")
KT_JAR = os.path.join(ROOT, "hsharp-kotlin-compiler", "build", "libs", "hsharp-kotlin-compiler.jar")
WRAP = os.path.join(ROOT, "stress_test", "15_cli_packager", "wrap_hbc.py")
WORKDIR = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 10  # seconds — short, since infinite loops are exactly what we hunt


def run(cmd, **kw):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=TIMEOUT, cwd=WORKDIR, **kw)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "<TIMEOUT after %ds — likely infinite loop>" % TIMEOUT
    except Exception as e:
        return 125, "", "<runner error: %r>" % e


def run_py_vm(flat_hbc):
    """Python 字节码 VM (bytecode.py) 直接跑 flat .hbc — 任务指定的参考真相。
    Python VM 的 FOR_ITER 兼容 JUMP P+1 与 JUMP P 两种回边，不需要 fix。"""
    return run(["python3", HSHARP, "--run-bc", flat_hbc])


def run_kotlin(hbc):
    return run(["java", "-jar", KT_JAR, "run", hbc])


def classify(rc, out, err):
    if rc == 0:
        return "OK"
    if rc == 124:
        return "TIMEOUT"
    low = (err + out).lower()
    if "indexoutofbound" in low:
        return "CRASH:IndexOOB"
    if "numberformatexception" in low:
        return "CRASH:NumberFormat"
    if "nullpointerexception" in low:
        return "CRASH:NPE"
    if "classcastexception" in low:
        return "CRASH:ClassCast"
    if "illegalargumentexception" in low:
        return "CRASH:IllegalArg"
    if "stackoverflow" in low:
        return "CRASH:StackOverflow"
    if "exception" in low or "error" in low:
        return "ERR(rc=%d)" % rc
    return "ERR(rc=%d)" % rc


def main():
    tests = sorted(f for f in os.listdir(WORKDIR) if f.endswith(".hto"))
    if not tests:
        print("no .hto tests found in", WORKDIR)
        return
    print("=" * 78)
    print("HbcReader + fixForLoopJumps 测试 — 共 %d 个用例" % len(tests))
    print("=" * 78)

    rows = []
    for t in tests:
        hto = os.path.join(WORKDIR, t)
        name = os.path.splitext(t)[0]
        flat_hbc = os.path.join(WORKDIR, name + ".flat.hbc")
        hbc = os.path.join(WORKDIR, name + ".hbc")
        # 1) emit-bc -> flat .hbc (Python compiler 原始输出)
        rc, o, e = run(["python3", HSHARP, "--emit-bc", hto])
        if rc != 0 or not os.path.exists(flat_hbc):
            # emit-bc writes to <name>.hbc; rename to .flat.hbc
            if os.path.exists(hbc):
                os.replace(hbc, flat_hbc)
            else:
                rows.append((t, (1, o, e), (1, "", "EMIT-BC FAILED")))
                continue
        else:
            # emit-bc wrote to <name>.hbc; move to .flat.hbc
            if os.path.exists(hbc) and not os.path.exists(flat_hbc):
                os.replace(hbc, flat_hbc)
        # 2) PY-VM: run-bc on flat
        pyvm = run_py_vm(flat_hbc)
        # 3) wrap flat -> modules format -> KT run
        run(["python3", WRAP, flat_hbc, hbc])
        kt = run_kotlin(hbc)
        rows.append((t, pyvm, kt))

    print()
    diffs = []
    for t, pyvm, kt in rows:
        ptag = classify(*pyvm)
        ktag = classify(*kt)
        py_out = pyvm[1].strip()
        kt_out = kt[1].strip()
        match = "MATCH" if (kt_out == py_out and ktag == "OK" and ptag == "OK") else "DIFF"
        if match == "DIFF":
            diffs.append((t, pyvm, kt))
        print("[%s] %-30s PY-VM=%-16s KT=%-22s"
              % (match, t, ptag, ktag))

    if diffs:
        print()
        print("=" * 78)
        print("不一致/崩溃/超时详情 (%d 个)" % len(diffs))
        print("=" * 78)
        for t, pyvm, kt in diffs:
            print("\n---- %s ----" % t)
            print("PY-VM(rc=%s) [参考真相]:" % pyvm[0])
            print("  OUT: %r" % pyvm[1][:500])
            if pyvm[2].strip():
                print("  ERR: %r" % pyvm[2][:300])
            print("KT-HVM(rc=%s):" % kt[0])
            print("  OUT: %r" % kt[1][:500])
            if kt[2].strip():
                print("  ERR: %r" % kt[2][:700])
    else:
        print("\n所有用例 KT 与 PY-VM 一致。")

    print()
    print("=" * 78)
    print("汇总")
    print("=" * 78)
    crash = [r for r in rows if "CRASH" in classify(*r[2])]
    timeout = [r for r in rows if classify(*r[2]) == "TIMEOUT"]
    diffs_n = len(diffs)
    print("总用例: %d" % len(rows))
    print("Kotlin 崩溃 (JVM 异常): %d" % len(crash))
    print("Kotlin 超时 (疑似死循环): %d" % len(timeout))
    print("KT 与 PY-VM 不一致: %d" % diffs_n)
    if crash:
        print("\nKotlin 崩溃列表:")
        for t, _, kt in crash:
            print("  - %s : %s" % (t, classify(*kt)))
    if timeout:
        print("\nKotlin 超时列表 (fixForLoopJumps 嫌疑):")
        for t, _, kt in timeout:
            print("  - %s : %s" % (t, classify(*kt)))


if __name__ == "__main__":
    main()
