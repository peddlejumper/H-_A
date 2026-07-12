"""Run all H# / Python / C++ benchmarks and collect timings into benchmark_results.json"""
import subprocess, time, json, os

ROOT = "/Users/peddlejumper/H#/v0.4/HSharp_v0.4_Package"
BENCH = "/Users/peddlejumper/H#/v0.4/HSharp_v0.4_Package/benchmarks"

CASES = [
    ('bench_arith',  'sum_of_squares'),
    ('bench_primes', 'primes'),
    ('bench_string', 'len'),
    ('bench_list',   'sum'),
    ('bench_fib',    'fib(30)'),
    ('bench_matrix', 'total'),
]

def time_run(cmd, label, runs=3):
    """Run a command 'runs' times and return median time in ms."""
    times = []
    for i in range(runs):
        t0 = time.perf_counter()
        r = subprocess.run(cmd, capture_output=True, text=True)
        t1 = time.perf_counter()
        if r.returncode != 0:
            print(f"  ERROR running {label}: {r.stderr}")
            return None
        times.append((t1 - t0) * 1000.0)
    times.sort()
    median = times[len(times) // 2]
    return round(median, 3)

results = {}

# H# C VM (hsvm)
print("\n=== H# C VM (hsvm) ===")
for name, _ in CASES:
    label = f"hsvm_{name}"
    print(f"Running {label}...")
    cmd = [f"{ROOT}/hsvm", f"{BENCH}/{name}.hbc"]
    ms = time_run(cmd, label, runs=3)
    r = subprocess.run(cmd, capture_output=True, text=True)
    output = r.stdout.strip().split('\n')[0]
    results[label] = {"time_ms": ms, "output": output}
    print(f"  {output}  -> {ms} ms")

# Python 3
print("\n=== Python 3 ===")
for name, _ in CASES:
    label = f"python_{name}"
    print(f"Running {label}...")
    cmd = ["python3", f"{BENCH}/{name}.py"]
    ms = time_run(cmd, label, runs=3)
    r = subprocess.run(cmd, capture_output=True, text=True)
    output = r.stdout.strip().split('\n')[0]
    results[label] = {"time_ms": ms, "output": output}
    print(f"  {output}  -> {ms} ms")

# C++ (-O2)
print("\n=== C++ (-O2) ===")
for name, _ in CASES:
    label = f"cpp_{name}"
    print(f"Running {label}...")
    cmd = [f"{BENCH}/{name}_cpp"]
    ms = time_run(cmd, label, runs=3)
    r = subprocess.run(cmd, capture_output=True, text=True)
    output = r.stdout.strip().split('\n')[0]
    results[label] = {"time_ms": ms, "output": output}
    print(f"  {output}  -> {ms} ms")

with open(f"{BENCH}/benchmark_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\n=== Summary ===")
print(f"{'Benchmark':<14} {'H# hsvm':>12} {'Python3':>12} {'C++ -O2':>12}")
print("-" * 56)
for name, _ in CASES:
    h_ms = results[f"hsvm_{name}"]["time_ms"]
    p_ms = results[f"python_{name}"]["time_ms"]
    c_ms = results[f"cpp_{name}"]["time_ms"]
    print(f"{name:<14} {h_ms:>10.2f}ms {p_ms:>10.2f}ms {c_ms:>10.2f}ms")

print(f"\nResults saved to {BENCH}/benchmark_results.json")
