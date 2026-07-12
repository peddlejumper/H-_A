// C++ Benchmark 2: Loop / Iteration
// Count primes up to N (naive trial division)
// Equivalent to bench_primes.hto
// Build: g++ -O2 -o bench_primes bench_primes.cpp

#include <cstdio>
#include <chrono>

int main() {
    const int n = 30000;
    int count = 0;
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int i = 2; i <= n; i = i + 1) {
        bool is_prime = true;
        for (int j = 2; j * j <= i; j = j + 1) {
            if (i % j == 0) {
                is_prime = false;
            }
        }
        if (is_prime) {
            count = count + 1;
        }
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    printf("primes=%d\n", count);
    printf("time_ms=%.3f\n", ms);
    return 0;
}
