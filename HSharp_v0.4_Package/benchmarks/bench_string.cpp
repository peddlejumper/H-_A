// C++ Benchmark 3: String Concatenation
// Build a long string by concatenation
// Equivalent to bench_string.hto
// Build: g++ -O2 -o bench_string bench_string.cpp

#include <cstdio>
#include <chrono>
#include <string>

int main() {
    const int n = 50000;
    std::string s;
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < n; i = i + 1) {
        s = s + "abcdef";
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    printf("len=%zu\n", s.size());
    printf("time_ms=%.3f\n", ms);
    return 0;
}
