// C++ Benchmark 4: List Operations (sum only, no list storage)
// Sum of arithmetic series 0..N-1 = N*(N-1)/2
// Equivalent to bench_list.hto
// Build: g++ -O2 -o bench_list bench_list.cpp

#include <cstdio>
#include <chrono>

int main() {
    const long long n = 10000000LL;
    long long total = 0;
    auto t0 = std::chrono::high_resolution_clock::now();
    for (long long i = 0; i < n; i = i + 1) {
        total = total + i;
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    printf("sum=%lld\n", total);
    printf("time_ms=%.3f\n", ms);
    return 0;
}
