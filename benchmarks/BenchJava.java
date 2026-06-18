/* ═══════════════════════════════════════════════════════════════
 * H# Benchmark Suite - Java Implementation
 * ═══════════════════════════════════════════════════════════════ */
import java.util.*;

public class BenchJava {
    // ── Benchmark 1: Recursive Fibonacci ──
    static long fib(int n) {
        if (n < 2) return n;
        return fib(n - 1) + fib(n - 2);
    }

    // ── Benchmark 2: Sieve of Eratosthenes ──
    // ── Benchmark 3: Merge Sort ──
    static void merge(int[] arr, int[] tmp, int l, int m, int r) {
        int i = l, j = m, k = l;
        while (i < m && j < r) tmp[k++] = arr[i] < arr[j] ? arr[i++] : arr[j++];
        while (i < m) tmp[k++] = arr[i++];
        while (j < r) tmp[k++] = arr[j++];
        for (i = l; i < r; i++) arr[i] = tmp[i];
    }
    static void msort(int[] arr, int[] tmp, int l, int r) {
        if (r - l < 2) return;
        int m = (l + r) / 2;
        msort(arr, tmp, l, m); msort(arr, tmp, m, r); merge(arr, tmp, l, m, r);
    }

    public static void main(String[] args) {
        System.out.println("Java Benchmark Results");
        System.out.println("=====================");
        System.out.println();

        long t;
        // Fib
        t = System.nanoTime();
        long fr = fib(30);
        System.out.printf("1. Fibonacci(30)  = %-10d | %.2f ms%n", fr, (System.nanoTime() - t) / 1e6);

        // Sieve
        t = System.nanoTime();
        int limit = 100000;
        boolean[] pr = new boolean[limit + 1];
        Arrays.fill(pr, true);
        pr[0] = pr[1] = false;
        for (int i = 2; i * i <= limit; i++)
            if (pr[i])
                for (int j = i * i; j <= limit; j += i) pr[j] = false;
        int pc = 0;
        for (int i = 0; i <= limit; i++) if (pr[i]) pc++;
        System.out.printf("2. Prime Sieve    = %-10d | %.2f ms%n", pc, (System.nanoTime() - t) / 1e6);

        // Sort
        t = System.nanoTime();
        int[] arr = new int[10000], tmp = new int[10000];
        for (int i = 0; i < 10000; i++) arr[i] = 10000 - i;
        msort(arr, tmp, 0, 10000);
        System.out.printf("3. Merge Sort     = ok=%-6d | %.2f ms%n",
            arr[0] == 1 && arr[9999] == 10000 ? 2 : 0, (System.nanoTime() - t) / 1e6);

        // Matrix
        t = System.nanoTime();
        int n = 100;
        double[][] a = new double[n][n], b = new double[n][n], c = new double[n][n];
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++) {
                a[i][j] = j + 1; b[i][j] = n - j;
            }
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                for (int k = 0; k < n; k++)
                    c[i][j] += a[i][k] * b[k][j];
        System.out.printf("4. Matrix(100)    = %-10.0f | %.2f ms%n", c[0][0], (System.nanoTime() - t) / 1e6);

        // String
        t = System.nanoTime();
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 20000; i++) sb.append("hello");
        System.out.printf("5. String Build   = %-10d | %.2f ms%n", sb.length(), (System.nanoTime() - t) / 1e6);

        // Hash
        t = System.nanoTime();
        HashMap<Integer, Long> m = new HashMap<>();
        for (int i = 0; i < 5000; i++) m.put(i, (long)i * i);
        long sum = 0;
        for (int j = 0; j < 5000; j++) sum += m.get(j);
        System.out.printf("6. Hash Map       = sum=%-7d | %.2f ms%n", sum, (System.nanoTime() - t) / 1e6);

        System.out.println("\nDone.");
    }
}