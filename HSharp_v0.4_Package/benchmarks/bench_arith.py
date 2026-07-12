# Python 3 Benchmark 1: Arithmetic Operations
# Compute sum of squares 1..N
# Equivalent to bench_arith.hto

import time

n = 1000000
total = 0
i = 1
t0 = time.perf_counter()
while i <= n:
    total = total + i * i
    i = i + 1
elapsed = time.perf_counter() - t0
print("sum_of_squares=" + str(total))
print("time_ms=" + str(round(elapsed * 1000, 3)))
