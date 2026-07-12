# Python 3 Benchmark 5: Recursive Fibonacci
# Compute fib(30) with naive recursion
# Equivalent to bench_fib.hto

import time
import sys

sys.setrecursionlimit(10000)

def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

t0 = time.perf_counter()
r = fib(30)
elapsed = time.perf_counter() - t0
print("fib(30)=" + str(r))
print("time_ms=" + str(round(elapsed * 1000, 3)))
