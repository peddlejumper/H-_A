# Python 3 Benchmark 6: Nested Loop (Matrix Multiplication)
# 100x100 matrix multiplication
# Equivalent to bench_matrix.hto

import time

n = 100
total = 0
i = 0
t0 = time.perf_counter()
while i < n:
    j = 0
    while j < n:
        s = 0
        k = 0
        while k < n:
            s = s + (i + k) * (k * j + 1)
            k = k + 1
        total = total + s
        j = j + 1
    i = i + 1
elapsed = time.perf_counter() - t0
print("total=" + str(total))
print("time_ms=" + str(round(elapsed * 1000, 3)))
