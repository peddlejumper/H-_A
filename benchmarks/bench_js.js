/* ═══════════════════════════════════════════════════════════════
 * H# Benchmark Suite - JavaScript (Node.js) Implementation
 * ═══════════════════════════════════════════════════════════════ */

// ── Benchmark 1: Recursive Fibonacci ──
function fib(n) {
    if (n < 2) return n;
    return fib(n - 1) + fib(n - 2);
}

// ── Benchmark 2: Sieve of Eratosthenes ──
function benchSieve() {
    const limit = 100000;
    const isPrime = new Array(limit + 1).fill(true);
    isPrime[0] = isPrime[1] = false;
    for (let p = 2; p * p <= limit; p++) {
        if (isPrime[p]) {
            for (let j = p * p; j <= limit; j += p)
                isPrime[j] = false;
        }
    }
    return isPrime.filter(Boolean).length;
}

// ── Benchmark 3: Merge Sort ──
function merge(left, right) {
    const result = [];
    let i = 0, j = 0;
    while (i < left.length && j < right.length)
        result.push(left[i] < right[j] ? left[i++] : right[j++]);
    while (i < left.length) result.push(left[i++]);
    while (j < right.length) result.push(right[j++]);
    return result;
}
function mergeSort(arr) {
    if (arr.length < 2) return arr;
    const mid = arr.length >> 1;
    return merge(mergeSort(arr.slice(0, mid)), mergeSort(arr.slice(mid)));
}

// ── Benchmark 4: Matrix Multiply ──
function benchMatrix() {
    const n = 100;
    const a = [], b = [], c = [];
    for (let i = 0; i < n; i++) {
        a[i] = []; b[i] = []; c[i] = [];
        for (let j = 0; j < n; j++) {
            a[i][j] = j + 1;
            b[i][j] = n - j;
            c[i][j] = 0;
        }
    }
    for (let i = 0; i < n; i++)
        for (let j = 0; j < n; j++)
            for (let k = 0; k < n; k++)
                c[i][j] += a[i][k] * b[k][j];
    return c[0][0];
}

// ── Benchmark 5: String Build ──
function benchString() {
    let s = '';
    for (let i = 0; i < 20000; i++) s += 'hello';
    return s.length;
}

// ── Benchmark 6: Hash Map ──
function benchHash() {
    const m = new Map();
    for (let i = 0; i < 5000; i++) m.set(i, i * i);
    let sum = 0;
    for (let j = 0; j < 5000; j++) sum += m.get(j);
    return sum;
}

// ── Run all ──
function time(fn, label) {
    const start = performance.now();
    const result = fn();
    const elapsed = performance.now() - start;
    console.log(`${label.padEnd(18)} = ${String(result).padEnd(10)} | ${elapsed.toFixed(2)} ms`);
}

console.log('JavaScript (Node.js) Benchmark Results');
console.log('======================================\n');
time(() => fib(30), '1. Fibonacci(30)');
time(benchSieve, '2. Prime Sieve');
time(() => {
    const arr = Array.from({length: 10000}, (_, i) => 10000 - i);
    const res = mergeSort(arr);
    return res[0] === 1 && res[9999] === 10000 ? 2 : 0;
}, '3. Merge Sort');
time(benchMatrix, '4. Matrix(100)');
time(benchString, '5. String Build');
time(benchHash, '6. Hash Map');
console.log('\nDone.');