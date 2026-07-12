# Python 3 Benchmark 4: List Operations (sum only, no list storage)
# Sum of arithmetic series 0..N-1 = N*(N-1)/2
# Equivalent to bench_list.hto

import time

n = 10000000
total = 0
i = 0
t0 = time.perf_counter()
while i < n:
    total = total + i
    i = i + 1
elapsed = time.perf_counter() - t0
print("sum=" + str(total))
print("time_ms=" + str(round(elapsed * 1000, 3)))
