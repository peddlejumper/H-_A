/* ═══════════════════════════════════════════════════════════════
 * H# Benchmark Suite - C++ Implementation
 * ═══════════════════════════════════════════════════════════════ */
#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <chrono>

using namespace std;
using Clock = chrono::high_resolution_clock;

double elapsed(Clock::time_point start) {
    return chrono::duration<double, milli>(Clock::now() - start).count();
}

// ── Benchmark 1: Recursive Fibonacci ──
long fib(int n) {
    if (n < 2) return n;
    return fib(n - 1) + fib(n - 2);
}

// ── Benchmark 2: Sieve of Eratosthenes ──
// ── Benchmark 3: Merge Sort ──
void merge(vector<int>& arr, vector<int>& tmp, int l, int m, int r) {
    int i = l, j = m, k = l;
    while (i < m && j < r) tmp[k++] = arr[i] < arr[j] ? arr[i++] : arr[j++];
    while (i < m) tmp[k++] = arr[i++];
    while (j < r) tmp[k++] = arr[j++];
    for (i = l; i < r; i++) arr[i] = tmp[i];
}
void msort(vector<int>& arr, vector<int>& tmp, int l, int r) {
    if (r - l < 2) return;
    int m = (l + r) / 2;
    msort(arr, tmp, l, m); msort(arr, tmp, m, r); merge(arr, tmp, l, m, r);
}

// ── Benchmark 4: Matrix Multiply ──
// ── Benchmark 5: String Build ──
// ── Benchmark 6: Hash Map ──

int main() {
    cout << "C++ Benchmark Results" << endl;
    cout << "====================" << endl << endl;

    // Fib
    auto t = Clock::now();
    long fr = fib(30);
    cout << "1. Fibonacci(30)  = " << fr << "         | " << elapsed(t) << " ms" << endl;

    // Sieve
    t = Clock::now();
    int limit = 100000;
    vector<char> p(limit + 1, 1);
    p[0] = p[1] = 0;
    for (int i = 2; i * i <= limit; i++)
        if (p[i])
            for (int j = i * i; j <= limit; j += i) p[j] = 0;
    long pc = 0;
    for (int i = 0; i <= limit; i++) if (p[i]) pc++;
    cout << "2. Prime Sieve    = " << pc << "        | " << elapsed(t) << " ms" << endl;

    // Sort
    t = Clock::now();
    vector<int> arr(10000);
    for (int i = 0; i < 10000; i++) arr[i] = 10000 - i;
    vector<int> tmp(10000);
    msort(arr, tmp, 0, 10000);
    cout << "3. Merge Sort     = ok=" << (arr[0] == 1 && arr[9999] == 10000 ? 2 : 0)
         << "      | " << elapsed(t) << " ms" << endl;

    // Matrix
    t = Clock::now();
    int n = 100;
    vector<vector<double>> a(n, vector<double>(n)), b(n, vector<double>(n)), c(n, vector<double>(n, 0));
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            a[i][j] = j + 1, b[i][j] = n - j;
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            for (int k = 0; k < n; k++)
                c[i][j] += a[i][k] * b[k][j];
    cout << "4. Matrix(100)    = " << c[0][0] << "      | " << elapsed(t) << " ms" << endl;

    // String
    t = Clock::now();
    string s;
    s.reserve(20000 * 5);
    for (int i = 0; i < 20000; i++) s += "hello";
    cout << "5. String Build   = " << s.length() << "       | " << elapsed(t) << " ms" << endl;

    // Hash
    t = Clock::now();
    unordered_map<int, long> m;
    for (int i = 0; i < 5000; i++) m[i] = (long)i * i;
    long sum = 0;
    for (int j = 0; j < 5000; j++) sum += m[j];
    cout << "6. Hash Map       = sum=" << sum << "   | " << elapsed(t) << " ms" << endl;

    cout << "\nDone." << endl;
    return 0;
}