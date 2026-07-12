"""Compile H# benchmark .hto files to a hsvm-compatible .hbc bundle."""
import sys, os, json, importlib.util

ROOT = "/Users/peddlejumper/H#/v0.4/HSharp_v0.4_Package"

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

load('tokens', f'{ROOT}/tokens.py')
load('ast', f'{ROOT}/ast.py')
load('h_ast', f'{ROOT}/h_ast.py')
lexer_mod = load('lexer', f'{ROOT}/lexer.py')
parser_mod = load('parser', f'{ROOT}/parser.py')
compiler_mod = load('compiler', f'{ROOT}/compiler.py')

BENCH = [
    ('bench_arith', f'{ROOT}/benchmarks/bench_arith.hto'),
    ('bench_primes', f'{ROOT}/benchmarks/bench_primes.hto'),
    ('bench_string', f'{ROOT}/benchmarks/bench_string.hto'),
    ('bench_list', f'{ROOT}/benchmarks/bench_list.hto'),
    ('bench_fib', f'{ROOT}/benchmarks/bench_fib.hto'),
    ('bench_matrix', f'{ROOT}/benchmarks/bench_matrix.hto'),
]

bundle = {"version": "v0.4", "modules": {}, "built_at": 0}
for name, path in BENCH:
    src = open(path).read()
    prog = parser_mod.Parser(lexer_mod.Lexer(src)).parse()
    bc = compiler_mod.Compiler().compile(prog)
    bundle['modules'][name] = bc
    print(f'OK: {name:20s}  {len(bc["instructions"]):5d} instrs, {len(bc["consts"]):3d} consts')

out = f'{ROOT}/benchmarks/benchmarks.hbc'
with open(out, 'w') as f:
    json.dump(bundle, f)
print(f'Bundle: {out}')
