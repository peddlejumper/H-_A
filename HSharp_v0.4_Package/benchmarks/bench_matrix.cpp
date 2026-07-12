// C++ Benchmark 6: Nested Loop (Matrix Multiplication)
// 100x100 matrix multiplication
// Equivalent to bench_matrix.hto
// Build: g++ -O2 -o bench_matrix bench_matrix.cpp

#include <cstdio>
#include <chrono>

int main() {
    const int n = 100;
    long long total = 0;
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < n; i = i + 1) {
        for (int j = 0; j < n; j = j + 1) {
            long long s = 0;
            for (int k = 0; k < n; k = k + 1) {
                s = s + (long long)(i + k) * (long long)(k * j + 1);
            }
            total = total + s;
        }
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    printf("total=%lld\n", total);
    printf("time_ms=%.3f\n", ms);
    return 0;
}
