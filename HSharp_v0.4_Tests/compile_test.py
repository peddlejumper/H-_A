"""Compile an H# .hto file to a .hbc file.

Used to round-trip test the Kotlin runtime against the Python VM.
Usage: python3 compile_test.py <file.hto> <output.hbc>
"""
import json
import sys
import time
import os

# Make sure the test directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tokens import TokenType
from lexer import Lexer
from parser import Parser
from compiler import Compiler
from host_functions import (builtin_time_now, builtin_substring, builtin_ord,
                            builtin_chr, builtin_int, builtin_str)

def compile_file(src_path, out_path):
    with open(src_path) as f:
        text = f.read()
    lexer = Lexer(text)
    parser = Parser(lexer)
    program = parser.parse()
    compiler = Compiler()
    compiler.compile(program)
    hbc = {
        "version": "v0.4",
        "modules": {
            "main": {
                "instructions": compiler.instructions,
                "consts": compiler.consts
            }
        },
        "built_at": int(time.time())
    }
    with open(out_path, "w") as f:
        json.dump(hbc, f, indent=2)
    return hbc

if __name__ == "__main__":
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "out.hbc"
    hbc = compile_file(src, out)
    print(f"compiled {src} -> {out}")
    print(f"  modules: {list(hbc['modules'].keys())}")
    for m, v in hbc['modules'].items():
        print(f"  {m}: {len(v['instructions'])} instrs, {len(v['consts'])} consts")
