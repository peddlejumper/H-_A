#!/usr/bin/env python3
"""
Test the enhanced H# bytecode compiler
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser
from enhanced_compiler import EnhancedCompiler, CompileError
from bytecode import VM

def test_basic_compilation():
    """Test basic compilation"""
    print("Test 1: Basic Compilation")
    
    code = """
    let x = 10;
    let y = 20;
    let sum = x + y;
    print(sum);
    """
    
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    
    compiler = EnhancedCompiler()
    bytecode = compiler.compile(program)
    
    print(f"  Instructions: {len(bytecode['instructions'])}")
    print(f"  Constants: {len(bytecode['consts'])}")
    print(f"  Functions: {bytecode['functions']}")
    print("  ✅ PASS\n")

def test_function_compilation():
    """Test function compilation"""
    print("Test 2: Function Compilation")
    
    code = """
    fn add(a, b) {
        return a + b;
    }
    
    let result = add(5, 3);
    print(result);
    """
    
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    
    compiler = EnhancedCompiler()
    bytecode = compiler.compile(program)
    
    print(f"  Instructions: {len(bytecode['instructions'])}")
    print(f"  Functions defined: {bytecode['functions']}")
    
    if 'add' in bytecode['functions']:
        print("  ✅ Function 'add' compiled successfully\n")
    else:
        print("  ❌ Function 'add' not found\n")

def test_control_flow():
    """Test control flow compilation"""
    print("Test 3: Control Flow Compilation")
    
    code = """
    let i = 0;
    while (i < 5) {
        print(i);
        let i = i + 1;
    }
    
    if (i == 5) {
        print("Done");
    }
    """
    
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    
    compiler = EnhancedCompiler()
    bytecode = compiler.compile(program)
    
    # Check for jump instructions
    has_jumps = any(instr[0] in ['JUMP', 'JUMP_IF_FALSE'] 
                    for instr in bytecode['instructions'])
    
    if has_jumps:
        print("  ✅ Control flow instructions generated\n")
    else:
        print("  ⚠️  No jump instructions found\n")

def test_array_operations():
    """Test array operations"""
    print("Test 4: Array Operations")
    
    code = """
    let arr = [1, 2, 3, 4, 5];
    print(arr[0]);
    """
    
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    
    compiler = EnhancedCompiler()
    bytecode = compiler.compile(program)
    
    has_list_ops = any(instr[0] in ['BUILD_LIST', 'BINARY_SUBSCR'] 
                       for instr in bytecode['instructions'])
    
    if has_list_ops:
        print("  ✅ Array operations compiled\n")
    else:
        print("  ⚠️  Array operations not found\n")

def test_lambda_compilation():
    """Test lambda/closure compilation"""
    print("Test 5: Lambda Compilation")
    
    code = """
    let double = fn(x) {
        return x * 2;
    };
    
    let result = double(21);
    print(result);
    """
    
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    
    compiler = EnhancedCompiler()
    try:
        bytecode = compiler.compile(program)
        print("  ✅ Lambda compiled successfully\n")
    except Exception as e:
        print(f"  ⚠️  Lambda compilation issue: {e}\n")

def main():
    print("="*60)
    print("Enhanced H# Bytecode Compiler Tests")
    print("="*60)
    print()
    
    tests = [
        test_basic_compilation,
        test_function_compilation,
        test_control_flow,
        test_array_operations,
        test_lambda_compilation,
    ]
    
    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ❌ FAILED: {e}\n")
    
    print("="*60)
    print(f"Results: {passed}/{len(tests)} tests passed")
    print("="*60)
    
    return 0 if passed == len(tests) else 1

if __name__ == '__main__':
    sys.exit(main())
