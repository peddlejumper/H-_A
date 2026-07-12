#!/usr/bin/env python3
"""
Kotlin HVM 高强度测试 runner。
对每个 .hto 测试文件，分别用三条路径执行并对比：

  PY  : python3 hsharp.py <file>            (树遍历解释器, 任务指定参考真相)
  OPT : python3 hsharp.py --opt <file>      (Python 字节码 VM, 与 Kotlin 同语义层)
  KT  : emit-bc -> wrap -> java -jar run    (Kotlin HVM)

重点找 Kotlin 端崩溃 / 输出不一致。
"""
import json
import os
import subprocess
import sys
import time

ROOT = "/Users/peddlejumper/H#/v0.4"
HSHARP = os.path.join(ROOT, "hsharp.py")
KT_JAR = os.path.join(ROOT, "hsharp-kotlin-compiler", "build", "libs", "hsharp-kotlin-compiler.jar")
WORKDIR = os.path.dirname(os.path.abspath(__file__))

TIMEOUT = 15  # seconds


def run(cmd, **kw):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=TIMEOUT, cwd=WORKDIR, **kw)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "<TIMEOUT after %ds>" % TIMEOUT
    except Exception as e:
        return 125, "", "<runner error: %r>" % e


def run_py_direct(hto):
    return run(["python3", HSHARP, hto])


def run_py_opt(hto):
    return run(["python3", HSHARP, "--opt", hto])


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
    # Python --emit-bc 输出的是 flat {instructions,consts}; Kotlin 需要 modules 包裹
    if not isinstance(flat, dict) or "modules" not in flat:
        bundle = {"version": "v0.4", "modules": {"main": flat}, "built_at": int(time.time())}
        with open(hbc, "w", encoding="utf-8") as f:
            json.dump(bundle, f)
    return run(["java", "-jar", KT_JAR, "run", hbc])


def classify(rc, out, err):
    if rc == 0:
        return "OK"
    if rc == 124:
        return "TIMEOUT"
    low = (err + out).lower()
    if "indexoutofbound" in low:
        return "CRASH:IndexOutOfBounds"
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
    tests = sorted(
        f for f in os.listdir(WORKDIR)
        if f.endswith(".hto") and f != "smoke.hto"
    )
    if not tests:
        print("no .hto tests found in", WORKDIR)
        return
    print("=" * 78)
    print("Kotlin HVM opcode 边界测试 — 共 %d 个用例" % len(tests))
    print("=" * 78)

    rows = []
    for t in tests:
        hto = os.path.join(WORKDIR, t)
        prc, po, pe = run_py_direct(hto)
        orc, oo, oe = run_py_opt(hto)
        krc, ko, ke = run_kotlin(hto)
        rows.append((t, (prc, po, pe), (orc, oo, oe), (krc, ko, ke)))

    # 打印逐用例结果
    print()
    diffs = []
    for t, py, opt, kt in rows:
        ptag = classify(*py)
        otag = classify(*opt)
        ktag = classify(*kt)
        # 对比标准: 以 OPT(字节码VM) 为参考真相, 检查 KT 是否一致
        kt_out = kt[1].strip()
        opt_out = opt[1].strip()
        match = "MATCH" if (kt_out == opt_out and ktag == otag) else "DIFF"
        if match == "DIFF":
            diffs.append((t, py, opt, kt))
        print("[%s] %-26s PY=%-18s OPT=%-18s KT=%-22s"
              % (match, t, ptag, otag, ktag))

    # 详细打印 diff
    if diffs:
        print()
        print("=" * 78)
        print("不一致/崩溃详情 (%d 个)" % len(diffs))
        print("=" * 78)
        for t, py, opt, kt in diffs:
            print("\n---- %s ----" % t)
            print("PY-DIRECT rc=%s:" % py[0])
            print("  OUT: %r" % py[1][:400])
            if py[2].strip():
                print("  ERR: %r" % py[2][:400])
            print("PY-OPT(rc=%s) [参考真相]:" % opt[0])
            print("  OUT: %r" % opt[1][:400])
            if opt[2].strip():
                print("  ERR: %r" % opt[2][:400])
            print("KT-HVM(rc=%s):" % kt[0])
            print("  OUT: %r" % kt[1][:400])
            if kt[2].strip():
                print("  ERR: %r" % kt[2][:600])
    else:
        print("\n所有用例 KT 与 OPT 一致。")

    # 汇总
    print()
    print("=" * 78)
    print("汇总")
    print("=" * 78)
    crash = [r for r in rows if "CRASH" in classify(*r[3])]
    diffs_n = len(diffs)
    print("总用例: %d" % len(rows))
    print("Kotlin 崩溃 (JVM 异常): %d" % len(crash))
    print("KT 与 OPT 不一致: %d" % diffs_n)
    if crash:
        print("\nKotlin 崩溃列表:")
        for t, _, _, kt in crash:
            print("  - %s : %s" % (t, classify(*kt)))


if __name__ == "__main__":
    main()
