/* ═══════════════════════════════════════════════════════════════
 * H# Benchmark Suite - C Implementation
 * ═══════════════════════════════════════════════════════════════ */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

double get_time_ms() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000.0 + ts.tv_nsec / 1000000.0;
}

/* ── Benchmark 1: Recursive Fibonacci ── */
long fib(int n) {
    if (n < 2) return n;
    return fib(n - 1) + fib(n - 2);
}

void bench_fib(long *result, double *elapsed) {
    double start = get_time_ms();
    *result = fib(30);
    *elapsed = get_time_ms() - start;
}

/* ── Benchmark 2: Sieve of Eratosthenes ── */
void bench_sieve(long *result, double *elapsed) {
    double start = get_time_ms();
    int limit = 100000;
    char *is_prime = malloc(limit + 1);
    memset(is_prime, 1, limit + 1);
    is_prime[0] = is_prime[1] = 0;
    for (int p = 2; p * p <= limit; p++) {
        if (is_prime[p]) {
            for (int j = p * p; j <= limit; j += p)
                is_prime[j] = 0;
        }
    }
    long count = 0;
    for (int i = 0; i <= limit; i++)
        if (is_prime[i]) count++;
    free(is_prime);
    *result = count;
    *elapsed = get_time_ms() - start;
}

/* ── Benchmark 3: Merge Sort ── */
void merge(int *arr, int *temp, int left, int mid, int right) {
    int i = left, j = mid, k = left;
    while (i < mid && j < right) {
        if (arr[i] < arr[j]) temp[k++] = arr[i++];
        else temp[k++] = arr[j++];
    }
    while (i < mid) temp[k++] = arr[i++];
    while (j < right) temp[k++] = arr[j++];
    for (i = left; i < right; i++) arr[i] = temp[i];
}

void merge_sort_rec(int *arr, int *temp, int left, int right) {
    if (right - left < 2) return;
    int mid = (left + right) / 2;
    merge_sort_rec(arr, temp, left, mid);
    merge_sort_rec(arr, temp, mid, right);
    merge(arr, temp, left, mid, right);
}

void bench_sort(long *result, double *elapsed) {
    double start = get_time_ms();
    int n = 10000;
    int *arr = malloc(n * sizeof(int));
    int *temp = malloc(n * sizeof(int));
    for (int i = 0; i < n; i++) arr[i] = n - i;
    merge_sort_rec(arr, temp, 0, n);
    *result = (arr[0] == 1 && arr[n-1] == 10000) ? 2 : 0;
    free(arr); free(temp);
    *elapsed = get_time_ms() - start;
}

/* ── Benchmark 4: Matrix Multiply ── */
void bench_matrix(double *result, double *elapsed) {
    double start = get_time_ms();
    int n = 100;
    double **a = malloc(n * sizeof(double*));
    double **b = malloc(n * sizeof(double*));
    double **c = malloc(n * sizeof(double*));
    for (int i = 0; i < n; i++) {
        a[i] = malloc(n * sizeof(double));
        b[i] = malloc(n * sizeof(double));
        c[i] = malloc(n * sizeof(double));
        for (int j = 0; j < n; j++) {
            a[i][j] = j + 1;
            b[i][j] = n - j;
            c[i][j] = 0;
        }
    }
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            for (int k = 0; k < n; k++)
                c[i][j] += a[i][k] * b[k][j];
    *result = c[0][0];
    for (int i = 0; i < n; i++) { free(a[i]); free(b[i]); free(c[i]); }
    free(a); free(b); free(c);
    *elapsed = get_time_ms() - start;
}

/* ── Benchmark 5: String Build ── */
void bench_string(long *result, double *elapsed) {
    double start = get_time_ms();
    int n = 20000;
    int cap = 256;
    char *s = malloc(cap);
    s[0] = '\0';
    int len = 0;
    for (int i = 0; i < n; i++) {
        int add = 5;
        if (len + add + 1 > cap) {
            cap *= 2;
            s = realloc(s, cap);
        }
        memcpy(s + len, "hello", 5);
        len += 5;
        s[len] = '\0';
    }
    *result = len;
    *elapsed = get_time_ms() - start;
    free(s);
}

/* ── Benchmark 6: Hash Map ── */
typedef struct {
    int key;
    int value;
    int occupied;
} Entry;

unsigned int hash_int(int key, int size) {
    return (unsigned int)(key * 2654435761UL) % size;
}

void bench_hash(long *result, double *elapsed) {
    double start = get_time_ms();
    int n = 5000;
    int size = n * 2;
    Entry *table = calloc(size, sizeof(Entry));

    /* Insert */
    for (int i = 0; i < n; i++) {
        unsigned int h = hash_int(i, size);
        while (table[h].occupied) h = (h + 1) % size;
        table[h].key = i;
        table[h].value = i * i;
        table[h].occupied = 1;
    }

    /* Lookup */
    long sum = 0;
    for (int j = 0; j < n; j++) {
        unsigned int h = hash_int(j, size);
        while (table[h].occupied && table[h].key != j)
            h = (h + 1) % size;
        if (table[h].occupied) sum += table[h].value;
    }
    *result = sum;
    *elapsed = get_time_ms() - start;
    free(table);
}

int main() {
    printf("C Benchmark Results\n");
    printf("===================\n\n");

    long lr; double el;
    bench_fib(&lr, &el);
    printf("1. Fibonacci(30)  = %-10ld | %.2f ms\n", lr, el);

    bench_sieve(&lr, &el);
    printf("2. Prime Sieve    = %-10ld | %.2f ms\n", lr, el);

    bench_sort(&lr, &el);
    printf("3. Merge Sort     = ok=%-6ld | %.2f ms\n", lr, el);

    double dr;
    bench_matrix(&dr, &el);
    printf("4. Matrix(100)    = %-10.0f | %.2f ms\n", dr, el);

    bench_string(&lr, &el);
    printf("5. String Build   = %-10ld | %.2f ms\n", lr, el);

    bench_hash(&lr, &el);
    printf("6. Hash Map       = sum=%-7ld | %.2f ms\n", lr, el);

    printf("\nDone.\n");
    return 0;
}