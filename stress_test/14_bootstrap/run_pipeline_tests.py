#!/usr/bin/env python3
"""
H# Bootstrap 自举管线测试驱动
================================
加载 H# 自举模块 (tokenize.hto / parser.hto / compiler.hto / interpreter.hto)
到 Python Interpreter 中，然后对每个测试 .hto 文件运行完整管线:
    H# tokenize(src) -> H# parse(tokens) -> H# compile(ast) -> H# execute(bytecode, env)
并捕获 H# execute 打印的 stdout。

同时用 `python3 hsharp.py <file>` (Python 解释器) 交叉验证同一份源码的输出。
"""

import os
import sys
import io
import contextlib
import traceback

ROOT = "/Users/peddlejumper/H#/v0.4"
BOOT = os.path.join(ROOT, "bootstrap")
WORK = os.path.join(ROOT, "stress_test", "14_bootstrap")

sys.path.insert(0, ROOT)

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from bytecode import VM
from h_ast import (
    Program, Identifier, CallExpression, ArrayLiteral, DictLiteral,
    StringLiteral, NumberLiteral, BooleanLiteral, NullLiteral,
)

# ---------------------------------------------------------------------------
# 1. 加载 H# 自举模块到 Python Interpreter
# ---------------------------------------------------------------------------

def host_read_file(args):
    try:
        with open(args[0], "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None

def host_write_file(args):
    try:
        with open(args[0], "w", encoding="utf-8") as f:
            f.write(args[1])
        return True
    except Exception:
        return False

def host_time_now(args):
    import time
    return int(time.time() * 1000)

def load_bootstrap_modules(interp):
    """按依赖顺序加载 4 个自举核心模块到 interp 中。"""
    modules = ["tokenize.hto", "parser.hto", "compiler.hto", "interpreter.hto"]
    for m in modules:
        path = os.path.join(BOOT, m)
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        lex = Lexer(code)
        p = Parser(lex)
        prog = p.parse()
        interp.interpret(prog)
    return interp

# ---------------------------------------------------------------------------
# 2. Python 对象 -> h_ast 字面量节点 (供 visit_CallExpression 调用 H# 函数)
# ---------------------------------------------------------------------------

def to_hast(obj):
    if obj is None:
        return NullLiteral()
    if isinstance(obj, bool):
        return BooleanLiteral(obj)
    if isinstance(obj, (int, float)):
        return NumberLiteral(obj)
    if isinstance(obj, str):
        return StringLiteral(obj)
    if isinstance(obj, list):
        return ArrayLiteral([to_hast(e) for e in obj])
    if isinstance(obj, dict):
        pairs = [(StringLiteral(str(k)), to_hast(v)) for k, v in obj.items()]
        return DictLiteral(pairs)
    return StringLiteral(str(obj))

def call_hsharp(interp, fname, *args):
    """调用 interp 中已加载的 H# 函数 fname(*args)。"""
    arg_nodes = [to_hast(a) for a in args]
    call = CallExpression(Identifier(fname), arg_nodes)
    return interp.visit_CallExpression(call, interp.global_env)

# ---------------------------------------------------------------------------
# 3. 完整自举管线: tokenize -> parse -> compile -> execute
# ---------------------------------------------------------------------------

def run_bootstrap_pipeline(interp, src):
    """
    用 H# 自举的 tokenize/parse/compile/execute 处理 src。
    返回 (ok, output, stage_info)。
    output 为 H# execute() 期间打印到 stdout 的文本。

    注意：H# execute() (interpreter.hto) 因闭包作用域问题 (嵌套函数无法访问
    外层 stack 变量) 当前无法运行，因此本函数同时用 Python VM 运行 H# 编译
    产生的字节码 (与 use_tokenize.py 相同的路径)，作为 "H# 前端 + Python 后端"
    的验证。
    """
    info = {}

    # Step 1: tokenize (H#)
    try:
        tokens = call_hsharp(interp, "tokenize", src)
        info["tokens"] = len(tokens) if isinstance(tokens, list) else "n/a"
    except Exception as e:
        return False, "", {"stage": "tokenize", "error": f"{type(e).__name__}: {e}"}

    # Step 2: parse (H#)
    try:
        ast = call_hsharp(interp, "parse", tokens)
        info["ast_type"] = ast[0] if isinstance(ast, list) and ast else "n/a"
    except Exception as e:
        return False, "", {"stage": "parse", "error": f"{type(e).__name__}: {e}"}

    # Step 3: compile (H#)
    try:
        bc = call_hsharp(interp, "compile", ast)
        info["ninstrs"] = len(bc.get("instructions", [])) if isinstance(bc, dict) else "n/a"
    except Exception as e:
        return False, "", {"stage": "compile", "error": f"{type(e).__name__}: {e}"}

    # Step 4a: execute (H#) — 捕获 stdout (预期会因闭包问题失败)
    buf = io.StringIO()
    ok_hexec = True
    hexec_err = ""
    try:
        with contextlib.redirect_stdout(buf):
            call_hsharp(interp, "execute", bc, {})
    except Exception as e:
        ok_hexec = False
        hexec_err = f"{type(e).__name__}: {e}"
    out_hexec = buf.getvalue()
    info["h#_execute_ok"] = ok_hexec
    info["h#_execute_error"] = hexec_err

    # Step 4b: 用 Python VM 运行 H# 编译的字节码 (H# 前端 + Python 后端)
    buf2 = io.StringIO()
    ok_pyvm = True
    pyvm_err = ""
    try:
        with contextlib.redirect_stdout(buf2):
            vm = VM(bc)
            vm.run()
    except Exception as e:
        ok_pyvm = False
        pyvm_err = f"{type(e).__name__}: {e}"
    out_pyvm = buf2.getvalue()
    info["py_vm_ok"] = ok_pyvm
    info["py_vm_error"] = pyvm_err

    info["stage"] = "execute"
    # 综合判定：Python VM 路径成功即视为 H# 前端 (tokenize/parse/compile) 正确
    return ok_pyvm, out_pyvm, info

# ---------------------------------------------------------------------------
# 4. 交叉验证: 用 Python hsharp.py 直接运行同一源码
# ---------------------------------------------------------------------------

def run_python_reference(src):
    """用 Python Interpreter 直接解释执行 src，返回 stdout。"""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            lex = Lexer(src)
            p = Parser(lex)
            prog = p.parse()
            interp2 = Interpreter()
            interp2.builtins["read_file"] = host_read_file
            interp2.builtins["write_file"] = host_write_file
            interp2.builtins["time_now"] = host_time_now
            interp2.interpret(prog)
        return True, buf.getvalue()
    except Exception as e:
        return False, buf.getvalue() + f"\n[Python ref error: {type(e).__name__}: {e}]"

# ---------------------------------------------------------------------------
# 5. 主流程
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("H# Bootstrap 自举管线测试 (tokenize → parse → compile → execute)")
    print("=" * 70)

    # 加载自举模块
    interp = Interpreter()
    interp.builtins["read_file"] = host_read_file
    interp.builtins["write_file"] = host_write_file
    interp.builtins["time_now"] = host_time_now

    load_buf = io.StringIO()
    with contextlib.redirect_stdout(load_buf):
        try:
            load_bootstrap_modules(interp)
        except Exception as e:
            print("加载自举模块失败:", e)
            traceback.print_exc()
            return 1
    print("自举模块加载完成。已注册 H# 函数:",
          [n for n in ["tokenize", "parse", "compile", "execute"] if n in interp.functions])
    print()

    test_files = sorted(
        f for f in os.listdir(WORK)
        if f.startswith("t") and f.endswith(".hto")
    )
    if not test_files:
        print("未找到测试 .hto 文件")
        return 1

    passed = 0
    failed = 0
    results = []

    for tf in test_files:
        path = os.path.join(WORK, tf)
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()

        print(f"--- {tf} ---")
        ok_pipe, out_pipe, info = run_bootstrap_pipeline(interp, src)
        ok_ref, out_ref = run_python_reference(src)

        # 归一化: 去除首尾空白
        out_pipe_n = out_pipe.strip()
        out_ref_n = out_ref.strip()

        match = (out_pipe_n == out_ref_n) and ok_pipe and ok_ref
        status = "PASS" if match else "FAIL"
        if match:
            passed += 1
        else:
            failed += 1

        hexec_ok = info.get("h#_execute_ok", False)
        print(f"  H# tokenize→parse→compile: {'OK' if ok_pipe else 'ERR'}  "
              f"(tokens={info.get('tokens')}, instrs={info.get('ninstrs')})")
        print(f"  H# execute (H# VM): {'OK' if hexec_ok else 'FAIL'}  "
              f"{info.get('h#_execute_error', '')}")
        print(f"  Python VM 运行 H# 字节码: {'OK' if ok_pipe else 'ERR'}  | 输出: {out_pipe_n!r}")
        print(f"  Python 解释器参考: {'OK' if ok_ref else 'ERR'}  | 输出: {out_ref_n!r}")
        print(f"  状态: {status}")
        print()
        results.append((tf, status, out_pipe_n, out_ref_n, info, ok_pipe, ok_ref, hexec_ok))

    # 汇总
    print("=" * 70)
    print("汇总")
    print("=" * 70)
    for tf, status, op, oref, info, okp, okr, hexec_ok in results:
        hvm = "OK" if hexec_ok else "FAIL"
        line = (f"  {status:4}  {tf:28s}  H#VM={hvm:4}  "
                f"PyVM={op!r:14s}  PyRef={oref!r}")
        print(line)
    print("-" * 70)
    print(f"通过 (H#前端+PyVM == Py参考): {passed}/{len(results)}   "
          f"失败: {failed}/{len(results)}")
    hvm_pass = sum(1 for r in results if r[7])
    print(f"H# execute (纯 H# VM) 成功: {hvm_pass}/{len(results)}")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
