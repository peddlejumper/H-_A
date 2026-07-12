#!/usr/bin/env python3
"""
HNativeBridge 202 native 函数边界测试 runner。

对每个 .hto 测试文件，分别用两条路径执行并对比：

  PY : python3 hsharp.py <file>            (Python 解释器, 任务指定参考真相)
  KT : emit-bc -> wrap -> java -jar run    (Kotlin HVM, HNativeBridge.kt)

重点找 Kotlin native 实现缺失 / 行为不一致 / 崩溃 (JVM 异常)。
"""
import json
import os
import subprocess
import sys
import time

ROOT = "/Users/peddlejumper/H#/v0.4"
HSHARP = os.path.join(ROOT, "hsharp.py")
KT_JAR = os.path.join(ROOT, "hsharp-kotlin-compiler", "build", "libs",
                      "hsharp-kotlin-compiler.jar")
WORKDIR = os.path.dirname(os.path.abspath(__file__))

TIMEOUT = 20  # seconds


def run(cmd, **kw):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=TIMEOUT, cwd=WORKDIR, **kw)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "<TIMEOUT after %ds>" % TIMEOUT
    except Exception as e:
        return 125, "", "<runner error: %r>" % e


def run_py(hto):
    return run(["python3", HSHARP, hto])


def run_kotlin(hto):
    """emit-bc -> wrap into modules format -> java -jar run"""
    name = os.path.splitext(os.path.basename(hto))[0]
    hbc = os.path.join(WORKDIR, name + ".hbc")
    rc, out, err = run(["python3", HSHARP, "--emit-bc", hto])
    if rc != 0 or not os.path.exists(hbc):
        return rc, out, "EMIT-BC FAILED: " + err + out
    try:
        with open(hbc, "r", encoding="utf-8") as f:
            flat = json.load(f)
    except Exception as e:
        return 126, "", "HBC READ FAILED: %r" % e
    # Python --emit-bc 输出 flat {instructions,consts}; Kotlin 需 modules 包裹
    if not isinstance(flat, dict) or "modules" not in flat:
        bundle = {"version": "v0.4",
                  "modules": {"main": flat},
                  "built_at": int(time.time())}
        with open(hbc, "w", encoding="utf-8") as f:
            json.dump(bundle, f)
    return run(["java", "-jar", KT_JAR, "run", hbc])


def classify(rc, out, err):
    if rc == 0:
        return "OK"
    if rc == 124:
        return "TIMEOUT"
    low = (err + " " + out).lower()
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
    if "stringindexoutofbound" in low:
        return "CRASH:StringIndexOOB"
    if "stackoverflow" in low:
        return "CRASH:StackOverflow"
    if "arithmeticexception" in low:
        return "CRASH:Arithmetic"
    if "nosuchelement" in low:
        return "CRASH:NoSuchElement"
    if "exception" in low or "error" in low:
        return "ERR(rc=%d)" % rc
    return "ERR(rc=%d)" % rc


def main():
    tests = sorted(
        f for f in os.listdir(WORKDIR)
        if f.endswith(".hto") and f != "t00_sanity.hto"
    )
    if not tests:
        print("no .hto tests found in", WORKDIR)
        return
    print("=" * 78)
    print("HNativeBridge native 函数边界测试 — 共 %d 个用例" % len(tests))
    print("PY = python3 hsharp.py (Interpreter)   KT = java -jar run (Kotlin HVM)")
    print("=" * 78)

    rows = []
    for t in tests:
        hto = os.path.join(WORKDIR, t)
        prc, po, pe = run_py(hto)
        krc, ko, ke = run_kotlin(hto)
        rows.append((t, (prc, po, pe), (krc, ko, ke)))

    # 逐用例结果
    print()
    diffs = []
    crashes = []
    for t, py, kt in rows:
        ptag = classify(*py)
        ktag = classify(*kt)
        po = py[1].strip()
        ko = kt[1].strip()
        match = "MATCH" if (ko == po and ktag == ptag) else "DIFF"
        if match == "DIFF":
            diffs.append((t, py, kt))
        if "CRASH" in ktag:
            crashes.append((t, kt, ktag))
        print("[%s] %-26s PY=%-16s KT=%-22s"
              % (match, t, ptag, ktag))

    # diff 详情
    if diffs:
        print()
        print("=" * 78)
        print("不一致/崩溃详情 (%d 个)" % len(diffs))
        print("=" * 78)
        for t, py, kt in diffs:
            print("\n---- %s ----" % t)
            print("PY-INTERP (rc=%s):" % py[0])
            print("  OUT: %r" % py[1][:500])
            if py[2].strip():
                print("  ERR: %r" % py[2][:300])
            print("KT-HVM (rc=%s):" % kt[0])
            print("  OUT: %r" % kt[1][:500])
            if kt[2].strip():
                print("  ERR: %r" % kt[2][:600])

    # 汇总
    print()
    print("=" * 78)
    print("汇总")
    print("=" * 78)
    print("总用例: %d" % len(rows))
    print("Kotlin 崩溃 (JVM 异常): %d" % len(crashes))
    print("PY 与 KT 不一致: %d" % len(diffs))
    if crashes:
        print("\nKotlin 崩溃列表:")
        for t, kt, ktag in crashes:
            print("  - %s : %s" % (t, ktag))


if __name__ == "__main__":
    main()
