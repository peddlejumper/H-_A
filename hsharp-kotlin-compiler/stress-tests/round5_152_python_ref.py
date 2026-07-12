#!/usr/bin/env python3
"""Python 对照语义脚本 — 验证 round5_152 关键 bug case 的预期值。
H# 的语义以 Python 3 为基准。此脚本只验证有疑义的 case。
"""
import sys

def py_eq_fn():
    # S15-C2: lambda 引用相等
    l1 = lambda: 1
    l2 = lambda: 1
    l3 = l1
    print(f"S15-C2 l1==l1: {l1 == l1}")  # True
    print(f"S15-C2 l1==l2: {l1 == l2}")  # False (不同实例, id 比较)
    print(f"S15-C2 l1==l3: {l1 == l3}")  # True

def py_s10_c6():
    # S10-C6: 模块级 let 捕获 + 外层重赋值
    gx = 10
    gf = lambda: gx
    print(f"S10-C6: {gf()}")   # 10
    gx = 20
    print(f"S10-C6: {gx}")     # 20
    print(f"S10-C6: {gf()}")   # 20 (by-ref: lambda 看到 gx 的新值)

def py_s10_c7():
    # S10-C7: 捕获函数参数, 然后修改参数
    def cap_then_mod(a):
        g = lambda: a
        a = 100
        return g()
    print(f"S10-C7: {cap_then_mod(1)}")  # 100 (by-ref: a 被修改, g 看到 100)

def py_s11_c2():
    # S11-C2: 多闭包共享同一变量
    def make_pair():
        n = 0
        def inc():
            nonlocal n
            n = n + 1
            return n
        def get():
            return n
        return [inc, get]
    p = make_pair()
    inc_f, get_f = p[0], p[1]
    print(f"S11-C2: {inc_f()}")  # 1
    print(f"S11-C2: {inc_f()}")  # 2
    print(f"S11-C2: {inc_f()}")  # 3
    print(f"S11-C2: {get_f()}")  # 3 (共享 n)

def py_s11_c3():
    # S11-C3: 模块级 let + 闭包修改
    # 注意: Python 模块级变量在闭包中只能读, 不能写 (除非 global 声明)
    # 但 H# 允许闭包内修改捕获变量. 这里测试的是读取.
    captured = 0
    get_captured = lambda: captured
    print(f"S11-C3: {get_captured()}")  # 0
    captured = 99
    print(f"S11-C3: {captured}")         # 99
    print(f"S11-C3: {get_captured()}")   # 99 (by-ref: lambda 看到 captured 的新值)
    captured = 200
    print(f"S11-C3: {get_captured()}")   # 200

def py_s11_c4():
    # S11-C4: 闭包内修改捕获变量, 外层读取
    def mk_bag():
        n = 0
        def inc():
            nonlocal n
            n = n + 5
            return n
        inc()
        return n  # 外层读取被闭包修改的变量
    print(f"S11-C4: {mk_bag()}")  # 5 (共享 n)

def py_s11_c6():
    # S11-C6: dict of fns 共享变量
    def make_obj(x):
        def get():
            return x
        def set_(v):
            nonlocal x
            x = v
            return x
        def add(d):
            nonlocal x
            x = x + d
            return x
        return {"get": get, "set": set_, "add": add}
    o = make_obj(10)
    print(f"S11-C6: {o['get']()}")      # 10
    print(f"S11-C6: {o['add'](5)}")     # 15
    print(f"S11-C6: {o['get']()}")      # 15 (共享 x)
    print(f"S11-C6: {o['set'](100)}")   # 100
    print(f"S11-C6: {o['get']()}")      # 100 (共享 x)

def py_s11_c8():
    # S11-C8: withCount 计数
    def slow(x):
        return x * x
    def memoize(f):
        cache = {}
        calls = 0
        def wrapped(n):
            nonlocal calls
            key = str(n)
            if key in cache:
                return cache[key]
            calls = calls + 1
            v = f(n)
            cache[key] = v
            return v
        def get_calls():
            return calls
        return [wrapped, get_calls]
    mp = memoize(slow)
    mf, gc = mp[0], mp[1]
    mf(3); mf(3); mf(4); mf(5)
    print(f"S11-C8: {gc()}")  # 3 (共享 calls)

def py_s10_c4():
    # S10-C4: 捕获循环变量
    fns = []
    for i in [1, 2, 3]:
        fns.append(lambda: i)
    # Python: 所有 lambda 捕获同一个 i (循环变量), 循环结束后 i=3
    # 所以全部返回 3
    print(f"S10-C4 (python late-binding): {fns[0]()}, {fns[1]()}, {fns[2]()}")  # 3,3,3
    # 注意: Python 的 for 循环变量在闭包中是 late-binding, 循环结束后 i=3
    # H# 输出 1,2,3 — 这其实是 Python 3 的"错误"行为被修正了 (每次迭代新绑定)

def py_s10_c5():
    # S10-C5: 捕获循环变量 (range)
    fns = []
    for i in range(0, 3):
        fns.append(lambda: i)
    print(f"S10-C5 (python late-binding): {fns[0]()}, {fns[1]()}, {fns[2]()}")  # 2,2,2

if __name__ == "__main__":
    print("=== Python reference semantics ===")
    py_s10_c4()
    py_s10_c5()
    py_s10_c6()
    py_s10_c7()
    py_s11_c2()
    py_s11_c3()
    py_s11_c4()
    py_s11_c6()
    py_s11_c8()
    py_eq_fn()
