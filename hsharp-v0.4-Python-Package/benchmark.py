#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
#  H# v0.4 — Comprehensive Performance Benchmark Suite
# ═══════════════════════════════════════════════════════════════

import sys, os, time, json, statistics, subprocess, platform, struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser
from compiler import Compiler
from bytecode import VM as BytecodeVM
from interpreter import Interpreter

BASEDIR = os.path.dirname(os.path.abspath(__file__))
RESULTS = {}
SYSINFO = {
    "os": platform.system(),
    "machine": platform.machine(),
    "processor": platform.processor(),
    "python": platform.python_version(),
    "hostname": platform.node(),
    "cpu_count": os.cpu_count(),
}

# ═══════════════════════════════════════════════════════════════
#  UTILITY
# ═══════════════════════════════════════════════════════════════

def bench(name, fn, warmup=1, iterations=5):
    for _ in range(warmup):
        fn()
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    return min(times), statistics.mean(times), max(times)

def run_hsharp(code):
    """Run H# code through the bytecode VM."""
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    compiler = Compiler()
    bc = compiler.compile(program)
    vm = BytecodeVM(bc)
    return vm.run()

def run_hsharp_interp(code):
    """Run H# code through the tree-walking interpreter."""
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    interp = Interpreter()
    return interp.interpret(program)

def run_cvm(test_code):
    """Run H# code through the C VM (hsvm binary)."""
    import json as _json
    tmppath = "/tmp/hsharp_dzzw_bench"
    # Compile to bundle
    lexer = Lexer(test_code)
    parser = Parser(lexer)
    program = parser.parse()
    compiler = Compiler()
    bc = compiler.compile(program)
    bundle = {"modules": {"main": bc}}
    bundle_path = tmppath + ".hbc"
    with open(bundle_path, "w") as f:
        _json.dump(bundle, f)
    try:
        result = subprocess.run(
            ["./hsvm", bundle_path],
            cwd=BASEDIR,
            capture_output=True, text=True, timeout=30
        )
        return result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    finally:
        if os.path.exists(bundle_path):
            os.remove(bundle_path)

# ═══════════════════════════════════════════════════════════════
#  SECTION 1: LEXER & PARSER
# ═══════════════════════════════════════════════════════════════

def bench_lexer():
    print("  [Lexer] 1000 functions...", end=" ", flush=True)
    code = "".join(
        f"fn test_{i}(x,y,z){{let a=x+y*z-{i};let b=(a>0)?a:-a;return b;}}\n"
        for i in range(1000)
    )
    def do(): Lexer(code)
    mi, av, mx = bench("lexer_1000fns", do, warmup=3, iterations=10)
    RESULTS["lexer_1000fns"] = {"min": round(mi,3), "avg": round(av,3), "max": round(mx,3)}
    print(f"{av:.2f}ms")

def bench_parser():
    print("  [Parser] 500 functions...", end=" ", flush=True)
    code = "".join(
        f"fn test_{i}(x,y,z){{let a=x+y*z-{i};let b=(a>0)?a:-a;return b;}}\n"
        for i in range(500)
    )
    def do():
        Parser(Lexer(code)).parse()
    mi, av, mx = bench("parser_500fns", do, warmup=2, iterations=5)
    RESULTS["parser_500fns"] = {"min": round(mi,3), "avg": round(av,3), "max": round(mx,3)}
    print(f"{av:.2f}ms")

def bench_compiler():
    print("  [Compiler] 500 functions...", end=" ", flush=True)
    code = "".join(
        f"fn test_{i}(x,y,z){{let a=x+y*z-{i};let b=(a>0)?a:-a;return b;}}\n"
        for i in range(500)
    )
    def do():
        Compiler().compile(Parser(Lexer(code)).parse())
    mi, av, mx = bench("compiler_500fns", do, warmup=2, iterations=5)
    RESULTS["compiler_500fns"] = {"min": round(mi,3), "avg": round(av,3), "max": round(mx,3)}
    print(f"{av:.2f}ms")

# ═══════════════════════════════════════════════════════════════
#  SECTION 2: BYTECODE VM
# ═══════════════════════════════════════════════════════════════

def bench_bytecode_arithmetic():
    print("  [Bytecode] Arithmetic 10K...", end=" ", flush=True)
    code = "fn c(){let s=0;let i=0;while(i<10000){s=s+i*2-i/3;i=i+1;}return s;}c();"
    def do(): run_hsharp(code)
    mi, av, mx = bench("bytecode_arith", do, warmup=3, iterations=10)
    RESULTS["bytecode_arithmetic"] = {"min": round(mi,3), "avg": round(av,3), "max": round(mx,3)}
    print(f"{av:.2f}ms")

def bench_bytecode_fib():
    print("  [Bytecode] fib(25)...", end=" ", flush=True)
    code = "fn fib(n){if(n<=1){return n;}return fib(n-1)+fib(n-2);}fib(25);"
    def do(): run_hsharp(code)
    mi, av, mx = bench("bytecode_fib25", do, warmup=2, iterations=5)
    RESULTS["bytecode_fib25"] = {"min": round(mi,3), "avg": round(av,3), "max": round(mx,3)}
    print(f"{av:.2f}ms")

def bench_bytecode_ternary():
    print("  [Bytecode] Ternary 5K...", end=" ", flush=True)
    code = "fn t(){let s=0;let i=0;while(i<5000){s=s+(i%2==0?1:-1);i=i+1;}return s;}t();"
    def do(): run_hsharp(code)
    mi, av, mx = bench("bytecode_ternary", do, warmup=3, iterations=10)
    RESULTS["bytecode_ternary"] = {"min": round(mi,3), "avg": round(av,3), "max": round(mx,3)}
    print(f"{av:.2f}ms")

def bench_bytecode_quaternary():
    print("  [Bytecode] Quaternary 5K...", end=" ", flush=True)
    code = "fn q(){let s=0;let i=0;while(i<5000){let v=(i%3==0)?^1:(i%3==1):2;if(v!=nullptr){s=s+v;}i=i+1;}return s;}q();"
    def do(): run_hsharp(code)
    mi, av, mx = bench("bytecode_quaternary", do, warmup=3, iterations=10)
    RESULTS["bytecode_quaternary"] = {"min": round(mi,3), "avg": round(av,3), "max": round(mx,3)}
    print(f"{av:.2f}ms")

# ═══════════════════════════════════════════════════════════════
#  SECTION 3: TREE-WALKING INTERPRETER (Python)
# ═══════════════════════════════════════════════════════════════

def bench_interp_arithmetic():
    print("  [Interp] Arithmetic 5K...", end=" ", flush=True)
    code = "let s=0;let i=0;while(i<5000){s=s+i*2-i/3;i=i+1;}s;"
    def do(): run_hsharp_interp(code)
    mi, av, mx = bench("interp_arith", do, warmup=2, iterations=5)
    RESULTS["interp_arithmetic"] = {"min": round(mi,3), "avg": round(av,3), "max": round(mx,3)}
    print(f"{av:.2f}ms")

def bench_interp_fib():
    print("  [Interp] fib(20)...", end=" ", flush=True)
    def do(): run_hsharp_interp("fn fib(n){if(n<=1){return n;}return fib(n-1)+fib(n-2);}fib(20);")
    mi, av, mx = bench("interp_fib20", do, warmup=1, iterations=3)
    RESULTS["interp_fib20"] = {"min": round(mi,3), "avg": round(av,3), "max": round(mx,3)}
    print(f"{av:.2f}ms")

def bench_interp_ternary():
    print("  [Interp] Ternary 1K...", end=" ", flush=True)
    code = "let s=0;let i=0;while(i<1000){s=s+(i%2==0?1:-1);i=i+1;}s;"
    def do(): run_hsharp_interp(code)
    mi, av, mx = bench("interp_ternary", do, warmup=2, iterations=5)
    RESULTS["interp_ternary"] = {"min": round(mi,3), "avg": round(av,3), "max": round(mx,3)}
    print(f"{av:.2f}ms")

# ═══════════════════════════════════════════════════════════════
#  SECTION 4: DZZW v2.0 PARALLEL (C VM)
# ═══════════════════════════════════════════════════════════════

def bench_dzzw_spawn_await():
    print("  [DZZW] Spawn/Await 50 tasks...", end=" ", flush=True)
    code = """
fn worker(x) {
    let s = 0;
    let i = 0;
    while (i < 1000) { s = s + i; i = i + 1; }
    return s;
}
fn main() {
    let handles = [];
    let i = 0;
    while (i < 50) {
        let h = dzzw_spawn(worker, [i]);
        push(handles, h);
        i = i + 1;
    }
    let j = 0;
    while (j < 50) {
        let r = dzzw_await(handles[j]);
        j = j + 1;
    }
    return 1;
}
main();
"""
    t0 = time.perf_counter()
    stdout, stderr = run_cvm(code)
    t1 = time.perf_counter()
    elapsed = (t1 - t0) * 1000
    ok = "DZZW v2.0" in stderr
    RESULTS["dzzw_spawn_await"] = {"avg": round(elapsed, 3), "ok": ok}
    print(f"{elapsed:.2f}ms {'OK' if ok else 'ERR'}")

def bench_dzzw_parallel_map():
    print("  [DZZW] parallel_map 100 items...", end=" ", flush=True)
    code = """
fn square(x) { return x * x; }
fn main() {
    let data = [];
    let i = 0;
    while (i < 100) { push(data, i); i = i + 1; }
    let results = dzzw_parallel_map(square, data);
    return 1;
}
main();
"""
    t0 = time.perf_counter()
    stdout, stderr = run_cvm(code)
    t1 = time.perf_counter()
    elapsed = (t1 - t0) * 1000
    ok = "DZZW v2.0" in stderr
    RESULTS["dzzw_parallel_map"] = {"avg": round(elapsed, 3), "ok": ok}
    print(f"{elapsed:.2f}ms {'OK' if ok else 'ERR'}")

def bench_dzzw_channels():
    print("  [DZZW] Channel 100 msgs...", end=" ", flush=True)
    code = """
fn main() {
    let ch = dzzw_channel_create(10);
    fn producer(ch) {
        let i = 0;
        while (i < 100) { dzzw_channel_send(ch, i); i = i + 1; }
        return 1;
    }
    fn consumer(ch) {
        let sum = 0;
        let i = 0;
        while (i < 100) { let v = dzzw_channel_recv(ch); sum = sum + v; i = i + 1; }
        return sum;
    }
    let h1 = dzzw_spawn(producer, [ch]);
    let h2 = dzzw_spawn(consumer, [ch]);
    dzzw_await(h1);
    dzzw_await(h2);
    dzzw_channel_free(ch);
    return 1;
}
main();
"""
    t0 = time.perf_counter()
    stdout, stderr = run_cvm(code)
    t1 = time.perf_counter()
    elapsed = (t1 - t0) * 1000
    ok = "DZZW v2.0" in stderr
    RESULTS["dzzw_channels"] = {"avg": round(elapsed, 3), "ok": ok}
    print(f"{elapsed:.2f}ms {'OK' if ok else 'ERR'}")

def bench_dzzw_mutex():
    print("  [DZZW] Mutex 100 ops...", end=" ", flush=True)
    code = """
fn main() {
    let m = dzzw_mutex_create();
    let counter = [0];
    fn inc(m, counter) {
        dzzw_mutex_lock(m);
        counter[0] = counter[0] + 1;
        dzzw_mutex_unlock(m);
        return 1;
    }
    let handles = [];
    let i = 0;
    while (i < 100) {
        let h = dzzw_spawn(inc, [m, counter]);
        push(handles, h);
        i = i + 1;
    }
    let j = 0;
    while (j < 100) {
        dzzw_await(handles[j]);
        j = j + 1;
    }
    dzzw_mutex_free(m);
    return counter[0];
}
main();
"""
    t0 = time.perf_counter()
    stdout, stderr = run_cvm(code)
    t1 = time.perf_counter()
    elapsed = (t1 - t0) * 1000
    ok = "DZZW v2.0" in stderr
    RESULTS["dzzw_mutex"] = {"avg": round(elapsed, 3), "ok": ok}
    print(f"{elapsed:.2f}ms {'OK' if ok else 'ERR'}")

def bench_dzzw_work_stealing():
    print("  [DZZW] Work-stealing 200 tasks...", end=" ", flush=True)
    code = """
fn tiny(x) { return x + 1; }
fn main() {
    let handles = [];
    let i = 0;
    while (i < 200) {
        let h = dzzw_spawn(tiny, [i]);
        push(handles, h);
        i = i + 1;
    }
    let j = 0;
    while (j < 200) {
        dzzw_await(handles[j]);
        j = j + 1;
    }
    return 1;
}
main();
"""
    t0 = time.perf_counter()
    stdout, stderr = run_cvm(code)
    t1 = time.perf_counter()
    elapsed = (t1 - t0) * 1000
    ok = "DZZW v2.0" in stderr
    # Extract steal stats
    steal_info = ""
    for line in (stderr + stdout).split("\n"):
        if "steals_ok" in line:
            steal_info = line.strip()
    RESULTS["dzzw_work_stealing"] = {"avg": round(elapsed, 3), "ok": ok, "steals": steal_info}
    print(f"{elapsed:.2f}ms {'OK' if ok else 'ERR'}")

# ═══════════════════════════════════════════════════════════════
#  SECTION 5: SEQUENTIAL vs PARALLEL
# ═══════════════════════════════════════════════════════════════

def bench_sequential_heavy():
    print("  [Sequential] 20 heavy tasks...", end=" ", flush=True)
    code = """
fn heavy(x) {
    let s = 0; let i = 0;
    while (i < 10000) { s = s + i * x; i = i + 1; }
    return s;
}
let results = [];
let i = 0;
while (i < 20) {
    push(results, heavy(i));
    i = i + 1;
}
1;
"""
    def do(): run_hsharp(code)
    mi, av, mx = bench("seq_heavy", do, warmup=2, iterations=5)
    RESULTS["sequential_heavy"] = {"min": round(mi,3), "avg": round(av,3), "max": round(mx,3)}
    print(f"{av:.2f}ms")

def bench_parallel_heavy():
    print("  [Parallel] 20 heavy tasks (C VM)...", end=" ", flush=True)
    code = """
fn heavy(x) {
    let s = 0; let i = 0;
    while (i < 10000) { s = s + i * x; i = i + 1; }
    return s;
}
fn main() {
    let handles = [];
    let i = 0;
    while (i < 20) {
        let h = dzzw_spawn(heavy, [i]);
        push(handles, h);
        i = i + 1;
    }
    let j = 0;
    while (j < 20) {
        dzzw_await(handles[j]);
        j = j + 1;
    }
    return 1;
}
main();
"""
    t0 = time.perf_counter()
    stdout, stderr = run_cvm(code)
    t1 = time.perf_counter()
    elapsed = (t1 - t0) * 1000
    ok = "DZZW v2.0" in stderr
    RESULTS["parallel_heavy"] = {"avg": round(elapsed, 3), "ok": ok}
    print(f"{elapsed:.2f}ms {'OK' if ok else 'ERR'}")

# ═══════════════════════════════════════════════════════════════
#  SECTION 6: H#ML
# ═══════════════════════════════════════════════════════════════

def bench_hsml_matrix():
    print("  [H#ML] Matrix 3x3 mult...", end=" ", flush=True)
    code = """
fn mat_mul() {
    let a=[[1,2,3],[4,5,6],[7,8,9]];
    let b=[[9,8,7],[6,5,4],[3,2,1]];
    let r=[[0,0,0],[0,0,0],[0,0,0]];
    let i=0;
    while(i<3){let j=0;while(j<3){let k=0;while(k<3){r[i][j]=r[i][j]+a[i][k]*b[k][j];k=k+1;}j=j+1;}i=i+1;}
    return r;
}
mat_mul();
"""
    def do(): run_hsharp(code)
    mi, av, mx = bench("hsml_matrix", do, warmup=2, iterations=5)
    RESULTS["hsml_matrix"] = {"min": round(mi,3), "avg": round(av,3), "max": round(mx,3)}
    print(f"{av:.2f}ms")

# ═══════════════════════════════════════════════════════════════
#  SECTION 7: C VM OVERALL
# ═══════════════════════════════════════════════════════════════

def bench_cvm_startup():
    print("  [C VM] Startup...", end=" ", flush=True)
    code = "fn main(){return 42;}main();"
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        run_cvm(code)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    av = statistics.mean(times)
    RESULTS["cvm_startup"] = {"avg": round(av, 3)}
    print(f"{av:.2f}ms")

# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def run_all():
    print("=" * 60)
    print("  H# v0.4 — Comprehensive Performance Benchmark")
    print(f"  CPU: {SYSINFO['cpu_count']} cores | {SYSINFO['processor']}")
    print(f"  Python: {SYSINFO['python']} | OS: {SYSINFO['os']} {SYSINFO['machine']}")
    print("=" * 60)

    print("\n--- 1. Frontend: Lexer, Parser, Compiler ---")
    bench_lexer()
    bench_parser()
    bench_compiler()

    print("\n--- 2. Backend: Bytecode VM ---")
    bench_bytecode_arithmetic()
    bench_bytecode_fib()
    bench_bytecode_ternary()
    bench_bytecode_quaternary()

    print("\n--- 3. Backend: Tree-Walking Interpreter ---")
    bench_interp_arithmetic()
    bench_interp_fib()
    bench_interp_ternary()

    print("\n--- 4. DZZW v2.0 Parallel Runtime (C VM) ---")
    bench_cvm_startup()
    bench_dzzw_spawn_await()
    bench_dzzw_parallel_map()
    bench_dzzw_channels()
    bench_dzzw_mutex()
    bench_dzzw_work_stealing()

    print("\n--- 5. Sequential vs Parallel ---")
    bench_sequential_heavy()
    bench_parallel_heavy()

    print("\n--- 6. H#ML ---")
    bench_hsml_matrix()

    # Save
    RESULTS["sysinfo"] = SYSINFO
    RESULTS["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open("benchmark_results.json", "w") as f:
        json.dump(RESULTS, f, indent=2)

    print("\n" + "=" * 60)
    print("  Benchmark complete.  Results → benchmark_results.json")
    print("=" * 60)
    return RESULTS

if __name__ == "__main__":
    run_all()