# Python 3 Benchmark 2: Loop / Iteration
# Count primes up to N (naive trial division)
# Equivalent to bench_primes.hto

import time

n = 30000
count = 0
i = 2
t0 = time.perf_counter()
while i <= n:
    is_prime = True
    j = 2
    while j * j <= i:
        if i % j == 0:
            is_prime = False
        j = j + 1
    if is_prime:
        count = count + 1
    i = i + 1
elapsed = time.perf_counter() - t0
print("primes=" + str(count))
print("time_ms=" + str(round(elapsed * 1000, 3)))
