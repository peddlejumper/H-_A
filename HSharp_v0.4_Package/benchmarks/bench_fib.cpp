// C++ Benchmark 5: Recursive Fibonacci
// Compute fib(30) with naive recursion
// Equivalent to bench_fib.hto
// Build: g++ -O2 -o bench_fib bench_fib.cpp

#include <cstdio>
#include <chrono>

long long fib(int n) {
    if (n < 2) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

int main() {
    auto t0 = std::chrono::high_resolution_clock::now();
    long long r = fib(30);
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    printf("fib(30)=%lld\n", r);
    printf("time_ms=%.3f\n", ms);
    return 0;
}
