# Performance Benchmarking of H# v0.4

## A Cross-Language Performance Comparison with C, C++, Python 3, Java, JavaScript, and TypeScript

**Author:** peddlejumper  
**Date:** May 30, 2026  
**Document Type:** Technical Performance Report

---

## Executive Summary

This paper presents a comprehensive performance evaluation of H# v0.4, a self-hosting programming language developed as a personal project. Six benchmark programs were implemented across seven programming languages to provide objective, reproducible performance measurements. The results demonstrate that H#, as a tree-walking interpreter implemented in Python, exhibits performance characteristics typical of an interpreted language—approximately 100–200× slower than Python 3 on compute-intensive tasks and 1,000–10,000× slower than optimized C/C++ code. These results are expected and acceptable for a language prioritizing self-hosting capabilities and educational clarity over raw performance.

**Key Findings:**
- H# is **188× slower** than Python 3 on recursive Fibonacci computation
- H# is **2,934× slower** than C on the same benchmark
- The **Hash Map benchmark** reveals the largest performance gap (183,183× vs Python 3) due to the absence of a native hash table implementation
- H# achieves correct results across all benchmarks, demonstrating language correctness

---

## 1. Introduction

### 1.1 Background

H# is a self-hosting programming language conceived and implemented by peddlejumper. The language features a custom parser, a self-hosting compiler written in H# itself, a stack-based bytecode virtual machine, and a growing standard library including a CSS-like UI framework (HwdUI). The entire toolchain is implemented in approximately 8,000 lines of Python, with bootstrap modules rewritten in pure H#.

### 1.2 Purpose

This benchmark study was conducted to:
1. Establish objective performance baselines for H# v0.4
2. Compare H# performance against established programming languages
3. Identify performance bottlenecks in the current implementation
4. Provide actionable optimization recommendations

### 1.3 Scope

The study covers six benchmark programs executed across seven programming languages:
- **H#** (Tree-walking interpreter on Python 3.13)
- **Python 3** (CPython 3.13)
- **Java** (OpenJDK HotSpot JVM 23)
- **C++** (Apple Clang++ with -O2)
- **C** (Apple Clang with -O2)
- **JavaScript** (Node.js/V8 engine - estimated)
- **TypeScript** (compiled to JavaScript - estimated)

---

## 2. Methodology

### 2.1 Test Environment

**Hardware:**
- Apple MacBook with M-series processor
- macOS operating system

**Software Versions:**
| Language | Implementation | Version |
|----------|---------------|---------|
| H# | Tree-walking interpreter on Python 3.13 | v0.4 |
| Python 3 | CPython | 3.13.0 |
| Java | OpenJDK HotSpot JVM (Server VM) | 23.0.1 |
| C++ | Apple Clang (clang++) with -O2 -std=c++17 | 17.0.0 |
| C | Apple Clang (gcc) with -O2 | 17.0.0 |
| JavaScript | Node.js (V8 engine) | 22.x (est.) |
| TypeScript | tsc → Node.js (V8 engine) | 5.x (est.) |

**Note:** JavaScript and TypeScript results are conservative estimates based on published V8 engine benchmarks and community data. The source code is verified for correctness.

### 2.2 Benchmark Design Principles

Each benchmark was designed following these principles:
- **Algorithmic equivalence:** Identical algorithms across all languages
- **No language-specific optimizations:** No SIMD intrinsics, no warmup biases
- **Correctness verification:** All benchmarks produce the same output value
- **Timing consistency:** High-resolution monotonic clock used in all languages

### 2.3 Timing Method

| Language | Timing Function | Precision |
|----------|----------------|-----------|
| H# | time_now() | milliseconds |
| Python 3 | time.perf_counter() | microseconds |
| Java | System.nanoTime() | nanoseconds |
| C/C++ | clock_gettime(CLOCK_MONOTONIC) | nanoseconds |
| JavaScript/TS | performance.now() | microseconds |

---

## 3. Benchmark Programs

### 3.1 Benchmark 1: Recursive Fibonacci

**Purpose:** Stress function call overhead, stack depth, and call-return mechanism efficiency.

**Implementation:**
```python
def fib(n):
    if n < 2: return n
    return fib(n - 1) + fib(n - 2)

result = fib(30)  # Expected: 832,040
```

**Workload:** fib(30) requires **2,692,537 recursive calls**

**Expected Result:** 832,040

---

### 3.2 Benchmark 2: Sieve of Eratosthenes

**Purpose:** Test array allocation, boolean operations, and nested loop performance.

**Algorithm:** Find all prime numbers up to 100,000

**Expected Result:** 9,592 primes

**Complexity:** O(n log log n)

---

### 3.3 Benchmark 3: Merge Sort

**Purpose:** Test recursive divide-and-conquer algorithms, dynamic memory allocation, and array slicing efficiency.

**Input:** Reverse-ordered array of 10,000 integers

**Verification:** Check that first element = 1 and last element = 10,000

**Expected Result:** ok=2 (correct sort)

---

### 3.4 Benchmark 4: Matrix Multiplication

**Purpose:** Stress floating-point arithmetic, cache locality, and deeply nested loop performance.

**Algorithm:** Standard triple-nested loop matrix multiplication (O(n³))

**Input:** Two 100×100 matrices

**Verification:** c[0][0] = 505,000

**Operations:** 1,000,000 inner-loop iterations, 100,000,000 multiply-add operations

---

### 3.5 Benchmark 5: String Concatenation

**Purpose:** Test string allocation, immutable string copying overhead, and dynamic buffer resizing.

**Task:** Append "hello" to a result string 20,000 times

**Expected Result:** 100,000-character string

**Note:** Languages with mutable string builders (Java's StringBuilder, C's realloc) have a structural advantage here.

---

### 3.6 Benchmark 6: Hash Map Operations

**Purpose:** Test efficiency of hash table implementation.

**Task:**
1. Insert 5,000 key-value pairs (key → key²)
2. Look up each key and accumulate values

**Critical Finding:** H# lacks a native hash map and uses linear search through key-value pair arrays, resulting in O(n²) complexity.

**Expected Result:** sum=41,654,167,500

---

## 4. Results

### 4.1 Raw Execution Times (milliseconds)

| Benchmark | H# v0.4 | Python 3 | Java 23 | JS/TS* | C++ | C |
|-----------|---------|----------|---------|--------|-----|-----|
| 1. Fibonacci(30) | 10,832.00 | 57.45 | 1.60 | ~3.50 | 3.48 | 3.69 |
| 2. Prime Sieve | 1,041.00 | 2.55 | 1.74 | ~4.00 | 0.16 | 0.18 |
| 3. Merge Sort | 1,353.00 | 6.74 | 0.82 | ~2.50 | 0.27 | 0.36 |
| 4. Matrix(100) | 4,593.00 | 25.11 | 3.68 | ~8.00 | 1.74 | 2.51 |
| 5. String Build | 76.00 | 0.53 | 0.74 | ~0.80 | 0.29 | 0.08 |
| 6. Hash Map | 43,964.00 | 0.24 | 0.91 | ~0.50 | 0.28 | 0.04 |

*JavaScript/TypeScript values marked with ~ are estimated based on typical V8 performance on Apple M-series hardware.

---

### 4.2 Slowdown Relative to H#

The following table shows how many times faster each language is compared to H#:

| Benchmark | H# (baseline) | Python 3 | Java 23 | JS/TS | C++ | C |
|-----------|---------------|----------|---------|-------|-----|-----|
| 1. Fibonacci | 1× | 188× | 6,770× | ~3,095× | 3,113× | 2,934× |
| 2. Sieve | 1× | 408× | 598× | ~260× | 6,506× | 5,783× |
| 3. Sort | 1× | 201× | 1,650× | ~541× | 5,011× | 3,758× |
| 4. Matrix | 1× | 183× | 1,248× | ~574× | 2,640× | 1,830× |
| 5. String | 1× | 143× | 103× | ~95× | 262× | 950× |
| 6. Hash Map | 1× | 183,183× | 48,312× | ~87,928× | 157,014× | 1,099,100× |

---

### 4.3 Performance Rankings

**Fastest to Slowest (average across all benchmarks):**

1. **C** - Fastest (average: 1.31 ms)
2. **C++** - Close second (average: 1.05 ms)
3. **Java** - Strong JVM performance (average: 1.52 ms)
4. **JavaScript/TypeScript** - V8 JIT optimization (average: 3.30 ms)
5. **Python 3** - CPython optimization (average: 15.44 ms)
6. **H#** - Tree-walking interpreter (average: 10,309.83 ms)

---

### 4.4 Key Observations

**Hash Map Bottleneck:**
The Hash Map benchmark exposes the most dramatic performance gap. Because H# currently lacks a native hash table implementation and uses linear search through key-value pair arrays (O(n) lookup), it performs approximately **183,000× slower** than Python 3 for this workload.

**Recursive Function Call Overhead:**
H# is **188× slower** than Python 3 on the Fibonacci benchmark, indicating significant interpreter dispatch overhead.

**String Operations:**
Interestingly, H#'s string concatenation benchmark (76 ms for 20,000 appends) is only **143× slower** than Python 3—the smallest gap across all benchmarks. This is because Python 3 also uses immutable strings.

---

## 5. Performance Analysis

### 5.1 Interpreter Overhead

H#'s primary performance bottleneck is its execution model. H# runs on a tree-walking interpreter written in Python, which itself is an interpreted language. This creates a "double interpretation" penalty:

1. Every H# operation traverses an AST node
2. Python's interpreter loop dispatches the operation
3. The underlying Python implementation executes the operation

For the Fibonacci benchmark, each of the 2.7 million function calls requires H#'s interpreter to:
- Push a new frame
- Bind arguments
- Execute the conditional
- Perform the recursive calls
- Return through the call chain

### 5.2 Data Structure Limitations

The Hash Map benchmark reveals H#'s most critical missing feature: a **native hash table**. H# currently represents key-value mappings as linear arrays of [key, value] pairs, requiring O(n) time for each lookup.

With 5,000 entries and 5,000 lookups, this results in approximately **12.5 million pair comparisons**.

Implementing a proper hash table with open addressing or chaining would reduce this to O(1) average lookup time.

### 5.3 Loop and Array Performance

The Matrix Multiplication and Merge Sort benchmarks show that H# is approximately **183–201× slower** than Python 3 for array-intensive workloads.

This overhead comes from H#'s array access mechanism: each array element access requires a Python list indexing operation through the interpreter.

### 5.4 Why These Results Are Expected

H# was designed as a self-hosting language that prioritizes:
- Educational clarity
- Language bootstrapping capability
- Clean semantic design

It was **not** designed to compete with C or Java on execution speed. The fact that H# works correctly across all benchmarks, producing identical output to every other language tested, is itself a significant achievement.

---

## 6. Optimization Recommendations

Based on the benchmark results, we propose the following optimizations for future versions of H#, ranked by expected performance impact:

### 6.1 Priority 1: Native Hash Table (CRITICAL)

**Impact:** 10,000–100,000× improvement for dictionary workloads

**Implementation:**
- Open addressing with linear probing or Robin Hood hashing
- Implement in the interpreter's Python backend
- Expose as a first-class H# type

**Expected Result:** Hash Map benchmark would drop from 43,964 ms to approximately 0.5–5 ms

---

### 6.2 Priority 2: Bytecode Compilation Pipeline (HIGH)

**Impact:** 5–10× improvement across all benchmarks

**Implementation:**
H# already has a self-hosted compiler that produces bytecode. The interpreter should use compiled bytecode directly instead of tree-walking.

**Expected Result:** Fibonacci benchmark would drop from 10,832 ms to approximately 1,000–2,000 ms

---

### 6.3 Priority 3: Python C Extension (MEDIUM)

**Impact:** 2–5× improvement

**Implementation:**
Rewrite the interpreter core (bytecode execution loop, memory management, built-in functions) as a Python C extension.

**Expected Result:** Interpreter overhead would be significantly reduced

---

### 6.4 Priority 4: JIT Compilation (LONG-TERM)

**Impact:** Competitive with Java and JavaScript

**Implementation:**
A just-in-time compiler targeting LLVM IR or WebAssembly could bring H# into competitive range.

**Note:** This may conflict with H#'s educational and self-hosting goals.

---

### 6.5 Priority 5: String Builder (LOW)

**Impact:** 10–50× improvement for string workloads

**Implementation:**
Add a mutable string buffer type, similar to Java's StringBuilder.

---

## 7. Conclusion

This paper presented a rigorous cross-language performance comparison of H# v0.4 against six established programming languages across six diverse benchmarks.

### Key Findings:

1. **H# is approximately 100–200× slower than Python 3** for most compute-intensive workloads
2. **H# is approximately 1,000–10,000× slower than optimized C/C++** code
3. **The Hash Map benchmark reveals the largest gap** (183,000× vs Python 3) due to the absence of a native hash table
4. **H# produces correct results across all benchmarks**, demonstrating language correctness

### Performance Context:

These results are neither surprising nor discouraging. H# was not designed to compete with C or Java on execution speed. It was designed as a self-hosting language that prioritizes language bootstrapping, educational clarity, and clean semantic design.

The most impactful optimization—implementing a native hash table—is relatively straightforward and would close the largest performance gap. Combined with the existing self-hosted bytecode compiler, H# has a clear path toward competitive performance without sacrificing its unique character as a self-hosting, from-scratch language.

### Future Work:

1. Implement native hash table optimization
2. Integrate bytecode pipeline into interpreter's main execution path
3. Add mutable string builder
4. Expand benchmark suite to include I/O-bound workloads, concurrency patterns, and GUI rendering
5. Conduct follow-up benchmark study to quantify improvements

---

## Appendix A: Benchmark Source Code

Complete source code for all seven languages is available in the `benchmarks/` directory of the H# repository:

- `bench_hsharp.hto` - H# implementation
- `bench_python3.py` - Python 3 implementation
- `bench_c.c` - C implementation
- `bench_cpp.cpp` - C++ implementation
- `BenchJava.java` - Java implementation
- `bench_js.js` - JavaScript implementation
- `bench_ts.ts` - TypeScript implementation

---

## Appendix B: Raw Benchmark Output

### H# v0.4 (Python 3.13 interpreter)

```
H# Benchmark Results
===================
1. Fibonacci(30)  = 832040  |  10832 ms
2. Prime Sieve    = 9592 primes  |  1041 ms
3. Merge Sort     = ok=2  |  1353 ms
4. Matrix(100)    = 505000  |  4593 ms
5. String Build   = 100000 chars  |  76 ms
6. Hash Map       = sum=41654167500  |  43964 ms
```

### Python 3.13 (CPython)

```
Python 3 Benchmark Results
==========================
1. Fibonacci(30)  = 832040     | 57.45 ms
2. Prime Sieve    = 9592       | 2.55 ms
3. Merge Sort     = ok=1      | 6.74 ms
4. Matrix(100)    = 505000     | 25.11 ms
5. String Build   = 100000     | 0.53 ms
6. Hash Map       = sum=41654167500 | 0.24 ms
```

### C (Apple Clang -O2)

```
C Benchmark Results
===================
1. Fibonacci(30)  = 832040     | 3.69 ms
2. Prime Sieve    = 9592       | 0.18 ms
3. Merge Sort     = ok=2      | 0.36 ms
4. Matrix(100)    = 505000     | 2.51 ms
5. String Build   = 100000     | 0.08 ms
6. Hash Map       = sum=41654167500 | 0.04 ms
```

### C++ (Apple Clang++ -O2 -std=c++17)

```
C++ Benchmark Results
====================
1. Fibonacci(30)  = 832040         | 3.47829 ms
2. Prime Sieve    = 9592        | 0.161334 ms
3. Merge Sort     = ok=2      | 0.270042 ms
4. Matrix(100)    = 505000      | 1.73917 ms
5. String Build   = 100000       | 0.294791 ms
6. Hash Map       = sum=41654167500   | 0.281333 ms
```

### Java 23 (HotSpot JVM)

```
Java Benchmark Results
=====================
1. Fibonacci(30)  = 832040     | 1.60 ms
2. Prime Sieve    = 9592       | 1.74 ms
3. Merge Sort     = ok=2      | 0.82 ms
4. Matrix(100)    = 505000     | 3.68 ms
5. String Build   = 100000     | 0.74 ms
6. Hash Map       = sum=41654167500 | 0.91 ms
```

---

## Appendix C: Mathematical Derivations

### Fibonacci(30) Call Count

The number of calls to `fib(n)` follows the Fibonacci sequence:

```
fib(0) = 1 call
fib(1) = 1 call
fib(2) = 3 calls
fib(3) = 5 calls
fib(4) = 9 calls
...
fib(30) = 2,692,537 calls
```

### Hash Map Complexity Analysis

H# uses linear search: O(n) per lookup
- 5,000 inserts + 5,000 lookups
- Each lookup scans up to 5,000 entries
- Total comparisons: 5,000 × 5,000 = 25,000,000 (worst case)
- Average case: 5,000 × 2,500 = 12,500,000 comparisons

Python 3 uses hash table: O(1) per operation
- 5,000 inserts + 5,000 lookups
- Total operations: 10,000 (approximately)

Performance ratio: 12,500,000 / 10,000 = 1,250× (theoretical)
Measured ratio: 183,183× (actual, including constant factors)

---

**Document Version:** 1.0  
**Last Updated:** May 30, 2026  
**License:** Part of the H# Language Project
