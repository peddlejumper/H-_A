# Python 3 Benchmark 3: String Concatenation
# Build a long string by concatenation
# Equivalent to bench_string.hto

import time

n = 50000
s = ""
i = 0
t0 = time.perf_counter()
while i < n:
    s = s + "abcdef"
    i = i + 1
elapsed = time.perf_counter() - t0
print("len=" + str(len(s)))
print("time_ms=" + str(round(elapsed * 1000, 3)))
