#!/usr/bin/env python3
"""H# Benchmark Suite - Python 3 Implementation"""
import time, random

# ── Benchmark 1: Recursive Fibonacci ──
def fib(n):
    if n < 2: return n
    return fib(n - 1) + fib(n - 2)

def bench_fib():
    n = 30
    start = time.perf_counter()
    result = fib(n)
    elapsed = (time.perf_counter() - start) * 1000
    return result, elapsed

# ── Benchmark 2: Sieve of Eratosthenes ──
def bench_sieve():
    limit = 100000
    start = time.perf_counter()
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False
    p = 2
    while p * p <= limit:
        if is_prime[p]:
            for j in range(p * p, limit + 1, p):
                is_prime[j] = False
        p += 1
    count = sum(1 for x in is_prime if x)
    elapsed = (time.perf_counter() - start) * 1000
    return count, elapsed

# ── Benchmark 3: Merge Sort ──
def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] < right[j]:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

def merge_sort(arr):
    if len(arr) < 2: return arr
    mid = len(arr) // 2
    return merge(merge_sort(arr[:mid]), merge_sort(arr[mid:]))

def bench_sort():
    start = time.perf_counter()
    arr = list(range(10000, 0, -1))
    result = merge_sort(arr)
    ok = 1 if result[0] == 1 and result[-1] == 10000 else 0
    elapsed = (time.perf_counter() - start) * 1000
    return ok, elapsed

# ── Benchmark 4: Matrix Multiply ──
def bench_matrix():
    n = 100
    start = time.perf_counter()
    a = [[j + 1 for j in range(n)] for _ in range(n)]
    b = [[n - j for j in range(n)] for _ in range(n)]
    c = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            s = 0
            for k in range(n):
                s += a[i][k] * b[k][j]
            c[i][j] = s
    elapsed = (time.perf_counter() - start) * 1000
    return c[0][0], elapsed

# ── Benchmark 5: String Build ──
def bench_string():
    n = 20000
    start = time.perf_counter()
    s = ""
    for _ in range(n):
        s += "hello"
    elapsed = (time.perf_counter() - start) * 1000
    return len(s), elapsed

# ── Benchmark 6: Hash Map ──
def bench_hash():
    n = 5000
    start = time.perf_counter()
    d = {i: i * i for i in range(n)}
    s = sum(d[j] for j in range(n))
    elapsed = (time.perf_counter() - start) * 1000
    return s, elapsed

# ── Run all ──
if __name__ == '__main__':
    print("Python 3 Benchmark Results")
    print("==========================")
    r1 = bench_fib();  print(f"1. Fibonacci(30)  = {r1[0]:<10} | {r1[1]:.2f} ms")
    r2 = bench_sieve();print(f"2. Prime Sieve    = {r2[0]:<10} | {r2[1]:.2f} ms")
    r3 = bench_sort(); print(f"3. Merge Sort     = ok={r3[0]}      | {r3[1]:.2f} ms")
    r4 = bench_matrix();print(f"4. Matrix(100)    = {r4[0]:<10} | {r4[1]:.2f} ms")
    r5 = bench_string();print(f"5. String Build   = {r5[0]:<10} | {r5[1]:.2f} ms")
    r6 = bench_hash(); print(f"6. Hash Map       = sum={r6[0]:<10} | {r6[1]:.2f} ms")
    print("\nDone.")