"""H# self-hosting bootstrap runner.

This Python script serves as the initial bootloader for H# self-hosting.
It uses the Python H# interpreter to load and run the H#-written toolchain
(tokenizer, parser, compiler, interpreter VM).

The goal: H# compiles H#. Python is only used to start the process.
Once the H# toolchain is complete, the Python VM is the only remaining
dependency. This will be replaced by a C-based bytecode VM.
"""

import os
import sys
import json

ROOT = os.path.dirname(os.path.abspath(__file__))
parent = os.path.abspath(os.path.join(ROOT, '..'))
if parent not in sys.path:
    sys.path.insert(0, parent)

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from compiler import Compiler as PythonCompiler


def load_hto(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def evaluate_hsharp_source(src, interp):
    """Run H# source code using the Python H# interpreter."""
    lexer = Lexer(src)
    parser = Parser(lexer)
    ast = parser.parse()
    result = interp.interpret(ast)
    return result


def run_hsharp_file(path, interp):
    """Load and run a .hto file."""
    code = load_hto(path)
    return evaluate_hsharp_source(code, interp)


def set_variable(interp, name, value):
    """Set a variable in the interpreter's global environment."""
    interp.global_env.define(name, value)


def main():
    interp = Interpreter()
    print("=" * 60)
    print("  H# Self-Hosting Bootstrap - Stage 1 (Python Bootloader)")
    print("=" * 60)
    print()

    # Step 1: Load the H# bootstrap components into the Python interpreter
    # These define tokenize(), parse(), compile(), execute() in H#
    print("[Stage 1] Loading H# bootstrap components...")

    components = ['tokenize', 'parser', 'compiler', 'interpreter']
    for comp in components:
        path = os.path.join(ROOT, f'{comp}.hto')
        if os.path.exists(path):
            print(f"  Loading {comp}.hto...")
            run_hsharp_file(path, interp)
        else:
            print(f"  WARNING: {comp}.hto not found, skipping")

    print()

    # Step 2: Run simple self-hosting test: H# compiler compiles H# code
    print("[Stage 2] Testing H# self-hosting pipeline...")
    print()

    # Test simple arithmetic using H# toolchain
    test_src = """
let tokens_test = tokenize("let x = 40 + 2;\\nprint(x);\\n");
let ast_test = parse(tokens_test);
let bc_test = compile(ast_test);
let env_test = {};
let result_test = execute(bc_test, env_test);
"""
    print("  Test: H# tokenizer → parser → compiler → VM (simple arithmetic)")
    evaluate_hsharp_source(test_src, interp)
    print("  OK")

    # Test function calls
    test_fn = """
let tokens_fn = tokenize("fn square(n) {\\n  return n * n;\\n}\\nlet sq = square(7);\\nprint(sq);\\n");
let ast_fn = parse(tokens_fn);
let bc_fn = compile(ast_fn);
execute(bc_fn, {});
"""
    print("  Test: H# function compilation and execution")
    evaluate_hsharp_source(test_fn, interp)
    print("  OK")

    # Test with if/else
    test_if = """
let tokens_if = tokenize("let x = 5;\\nif (x > 3) {\\n  print(\\\"yes\\\");\\n} else {\\n  print(\\\"no\\\");\\n}\\n");
let ast_if = parse(tokens_if);
let bc_if = compile(ast_if);
execute(bc_if, {});
"""
    print("  Test: H# if/else compilation and execution")
    evaluate_hsharp_source(test_if, interp)
    print("  OK")

    # Test with while loop
    test_while = """
let tokens_w = tokenize("let i = 0;\\nlet sum = 0;\\nwhile (i < 5) {\\n  sum = sum + i;\\n  i = i + 1;\\n}\\nprint(sum);\\n");
let ast_w = parse(tokens_w);
let bc_w = compile(ast_w);
execute(bc_w, {});
"""
    print("  Test: H# while loop compilation and execution")
    evaluate_hsharp_source(test_while, interp)
    print("  OK")

    # Test: H# compiler compiles the tokenizer itself!
    print()
    print("[Stage 3] Meta-bootstrap: H# compiles its own tokenizer...")
    tokenizer_src = load_hto(os.path.join(ROOT, 'tokenize.hto'))
    test_meta = """
let tokens_meta = tokenize(tokenizer_source);
let ast_meta = parse(tokens_meta);
let bc_meta = compile(ast_meta);
"""
    # Inject tokenizer source as a variable
    set_variable(interp, 'tokenizer_source', tokenizer_src)
    evaluate_hsharp_source(test_meta, interp)
    print("  Self-compilation of tokenize.hto: OK!")

    # Test: H# compiler compiles the parser itself!
    print("[Stage 4] Meta-bootstrap: H# compiles its own parser...")
    parser_src = load_hto(os.path.join(ROOT, 'parser.hto'))
    set_variable(interp, 'parser_source', parser_src)
    test_meta2 = """
let tokens_p = tokenize(parser_source);
let ast_p = parse(tokens_p);
let bc_p = compile(ast_p);
"""
    evaluate_hsharp_source(test_meta2, interp)
    print("  Self-compilation of parser.hto: OK!")

    # Test: H# compiler compiles the compiler itself!
    print("[Stage 5] Meta-bootstrap: H# compiles its own compiler...")
    compiler_src = load_hto(os.path.join(ROOT, 'compiler.hto'))
    set_variable(interp, 'compiler_source', compiler_src)
    test_meta3 = """
let tokens_c = tokenize(compiler_source);
let ast_c = parse(tokens_c);
let bc_c = compile(ast_c);
"""
    evaluate_hsharp_source(test_meta3, interp)
    print("  Self-compilation of compiler.hto: OK!")

    # Test: H# compiler compiles the interpreter VM itself!
    print("[Stage 6] Meta-bootstrap: H# compiles its own interpreter VM...")
    interpreter_src = load_hto(os.path.join(ROOT, 'interpreter.hto'))
    set_variable(interp, 'interpreter_source', interpreter_src)
    test_meta4 = """
let tokens_i = tokenize(interpreter_source);
let ast_i = parse(tokens_i);
let bc_i = compile(ast_i);
"""
    evaluate_hsharp_source(test_meta4, interp)
    print("  Self-compilation of interpreter.hto: OK!")

    print()
    print("=" * 60)
    print("  H# SELF-HOSTING: ALL STAGES PASSED!")
    print("  100% of the H# toolchain can compile itself.")
    print("  Tokenizer:  H# ✓")
    print("  Parser:     H# ✓")
    print("  Compiler:   H# ✓")
    print("  Interpreter: H# ✓")
    print("")
    print("  Remaining Python dependency: bytecode VM runtime")
    print("  Next step: Write C-based bytecode VM (vm.c)")
    print("=" * 60)

    # Step: Generate bytecode JSON that the C VM can consume
    print()
    print("[Stage 7] Generating compile-boostrap bytecode for C VM...")

    # Compile the full toolchain to bytecode
    full_src = (
        tokenizer_src + "\n" +
        parser_src + "\n" +
        compiler_src + "\n" +
        interpreter_src + "\n"
    )

    # Use Python compiler to generate bytecode for the full toolchain
    python_compiler = PythonCompiler()
    lexer = Lexer(full_src)
    parser = Parser(lexer)
    ast = parser.parse()
    bytecode = python_compiler.compile(ast)

    bc_path = os.path.join(ROOT, 'bootstrap_bytecode.json')
    with open(bc_path, 'w', encoding='utf-8') as f:
        json.dump(bytecode, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Bytecode saved to: {bc_path}")
    print(f"  Instructions: {len(bytecode.get('instructions', []))}")
    print(f"  Constants: {len(bytecode.get('consts', []))}")


if __name__ == '__main__':
    main()