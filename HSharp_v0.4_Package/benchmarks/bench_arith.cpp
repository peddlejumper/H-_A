// C++ Benchmark 1: Arithmetic Operations
// Compute sum of squares 1..N
// Equivalent to bench_arith.hto
// Build: g++ -O2 -o bench_arith bench_arith.cpp

#include <cstdio>
#include <chrono>

int main() {
    const long long n = 1000000LL;
    long long total = 0;
    auto t0 = std::chrono::high_resolution_clock::now();
    for (long long i = 1; i <= n; i = i + 1) {
        total = total + i * i;
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    printf("sum_of_squares=%lld\n", total);
    printf("time_ms=%.3f\n", ms);
    return 0;
}
