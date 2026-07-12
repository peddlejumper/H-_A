"""Compile test_curry.hto to a .hbc bundle and run it via hsvm."""
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

src = open(f'{ROOT}/bootstrap/test_curry.hto').read()
prog = parser_mod.Parser(lexer_mod.Lexer(src)).parse()
bc = compiler_mod.Compiler().compile(prog)
bundle = {"version": "v0.4", "modules": {"test_curry": bc}, "built_at": 0}
out = f'{ROOT}/bootstrap/test_curry.hbc'
with open(out, 'w') as f:
    json.dump(bundle, f)
print(f'OK: test_curry.hbc  {len(bc["instructions"]):5d} instrs')
print(f'Bundle: {out}')
