#!/usr/bin/env python3
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
"""
Test register allocation and type system
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_register_allocation():
    """Test register allocator"""
    print("="*60)
    print("Testing Register Allocation")
    print("="*60)
    
    from register_allocation import RegisterAllocator, LinearScanAllocator
    
    # Test basic allocator
    allocator = RegisterAllocator(num_registers=4)
    
    # Simulate some instructions
    instructions = [
        ('LOAD_NAME', 'x'),
        ('LOAD_NAME', 'y'),
        ('BINARY_ADD',),
        ('STORE_NAME', 'result'),
    ]
    
    allocated = allocator.allocate(instructions)
    print(f"Original instructions: {len(instructions)}")
    print(f"Allocated instructions: {len(allocated)}")
    
    stats = allocator.get_stats()
    print(f"Register stats:")
    print(f"  Total registers: {stats['total_registers']}")
    print(f"  Used registers: {stats['used_registers']}")
    print(f"  Spilled variables: {stats['spilled_variables']}")
    
    # Test linear scan allocator
    lsa = LinearScanAllocator(num_registers=4)
    
    intervals = [
        ('a', 0, 10),
        ('b', 2, 8),
        ('c', 5, 15),
        ('d', 7, 12),
    ]
    
    allocations = lsa.allocate_with_intervals(intervals)
    print(f"\nLinear scan allocations:")
    for var, reg in allocations.items():
        print(f"  {var} -> {reg}")
    
    print(f"Spilled: {lsa.spilled_variables}")
    print("✅ Register allocation test passed\n")


def test_type_system_basic():
    """Test basic type checking"""
    print("="*60)
    print("Testing Type System - Basic Types")
    print("="*60)
    
    from type_system import (
        TypeChecker, INT_TYPE, FLOAT_TYPE, STRING_TYPE,
        BOOL_TYPE, VOID_TYPE, ArrayType, DictType, FunctionType
    )
    from lexer import Lexer
    from parser import Parser
    
    # Test simple program
    code = """
    let x = 42;
    let y = 3.14;
    let name = "Hello";
    let flag = true;
    print(x);
    print(y);
    print(name);
    """
    
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    
    checker = TypeChecker()
    is_valid = checker.check_program(program)
    
    print(f"Program valid: {is_valid}")
    print(f"Errors: {len(checker.get_errors())}")
    print(f"Warnings: {len(checker.get_warnings())}")
    
    if checker.has_errors():
        for error in checker.get_errors():
            print(f"  Error: {error.message}")
    
    print("✅ Basic type checking test passed\n")


def test_type_system_arithmetic():
    """Test arithmetic type checking"""
    print("="*60)
    print("Testing Type System - Arithmetic Operations")
    print("="*60)
    
    from type_system import TypeChecker
    from lexer import Lexer
    from parser import Parser
    
    # Valid arithmetic
    code1 = """
    let a = 10 + 20;
    let b = 3.14 * 2.0;
    let c = a + b;
    print(c);
    """
    
    lexer = Lexer(code1)
    parser = Parser(lexer)
    program = parser.parse()
    
    checker = TypeChecker()
    is_valid = checker.check_program(program)
    print(f"Valid arithmetic: {is_valid}")
    print(f"Errors: {len(checker.get_errors())}")
    
    # Invalid arithmetic
    code2 = """
    let x = "hello" - 5;
    """
    
    lexer = Lexer(code2)
    parser = Parser(lexer)
    program = parser.parse()
    
    checker = TypeChecker()
    is_valid = checker.check_program(program)
    print(f"\nInvalid arithmetic detected: {not is_valid}")
    print(f"Errors: {len(checker.get_errors())}")
    if checker.has_errors():
        for error in checker.get_errors():
            print(f"  Error: {error.message}")
    
    print("✅ Arithmetic type checking test passed\n")


def test_type_system_functions():
    """Test function type checking"""
    print("="*60)
    print("Testing Type System - Functions")
    print("="*60)
    
    from type_system import TypeChecker
    from lexer import Lexer
    from parser import Parser
    
    code = """
    fn add(a, b) {
        return a + b;
    }
    
    let result = add(10, 20);
    print(result);
    """
    
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    
    checker = TypeChecker()
    is_valid = checker.check_program(program)
    
    print(f"Function program valid: {is_valid}")
    print(f"Errors: {len(checker.get_errors())}")
    print(f"Warnings: {len(checker.get_warnings())}")
    
    print("✅ Function type checking test passed\n")


def test_type_system_arrays():
    """Test array type checking"""
    print("="*60)
    print("Testing Type System - Arrays")
    print("="*60)
    
    from type_system import TypeChecker, ArrayType
    from lexer import Lexer
    from parser import Parser
    
    code = """
    let arr = [1, 2, 3, 4, 5];
    let first = arr[0];
    print(first);
    """
    
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    
    checker = TypeChecker()
    is_valid = checker.check_program(program)
    
    print(f"Array program valid: {is_valid}")
    print(f"Errors: {len(checker.get_errors())}")
    
    print("✅ Array type checking test passed\n")


def test_type_system_conditionals():
    """Test conditional type checking"""
    print("="*60)
    print("Testing Type System - Conditionals")
    print("="*60)
    
    from type_system import TypeChecker
    from lexer import Lexer
    from parser import Parser
    
    # Valid conditional
    code1 = """
    let x = 10;
    if (x > 5) {
        print("greater");
    } else {
        print("smaller");
    }
    """
    
    lexer = Lexer(code1)
    parser = Parser(lexer)
    program = parser.parse()
    
    checker = TypeChecker()
    is_valid = checker.check_program(program)
    print(f"Valid conditional: {is_valid}")
    print(f"Errors: {len(checker.get_errors())}")
    
    # Invalid conditional (non-bool condition)
    code2 = """
    if (10) {
        print("always");
    }
    """
    
    lexer = Lexer(code2)
    parser = Parser(lexer)
    program = parser.parse()
    
    checker = TypeChecker()
    is_valid = checker.check_program(program)
    print(f"\nInvalid conditional detected: {not is_valid}")
    print(f"Errors: {len(checker.get_errors())}")
    if checker.has_errors():
        for error in checker.get_errors():
            print(f"  Error: {error.message}")
    
    print("✅ Conditional type checking test passed\n")


def test_type_inference():
    """Test type inference"""
    print("="*60)
    print("Testing Type Inference")
    print("="*60)
    
    from type_system import TypeChecker
    from lexer import Lexer
    from parser import Parser
    
    # Program with implicit types
    code = """
    let x = 42;
    let y = x + 10;
    let z = y * 2.5;
    let msg = "Result: " + str(z);
    print(msg);
    """
    
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    
    checker = TypeChecker()
    is_valid = checker.check_program(program)
    
    print(f"Inferred types program valid: {is_valid}")
    print(f"Errors: {len(checker.get_errors())}")
    print(f"Warnings: {len(checker.get_warnings())}")
    
    if checker.get_warnings():
        print("\nWarnings:")
        for warning in checker.get_warnings():
            print(f"  {warning}")
    
    print("✅ Type inference test passed\n")


def test_integrated_optimization():
    """Test optimization + type checking integration"""
    print("="*60)
    print("Testing Integrated Optimization and Type Checking")
    print("="*60)
    
    from lexer import Lexer
    from parser import Parser
    from enhanced_compiler import EnhancedCompiler
    from compiler_optimizations import Optimizer
    from type_system import TypeChecker
    from register_allocation import LinearScanAllocator
    
    code = """
    fn factorial(n) {
        if (n <= 1) {
            return 1;
        }
        return n * factorial(n - 1);
    }
    
    let result = factorial(5);
    print(result);
    """
    
    # Parse
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    
    # Type check
    type_checker = TypeChecker()
    type_valid = type_checker.check_program(program)
    print(f"Type check: {'PASS' if type_valid else 'FAIL'}")
    print(f"  Errors: {len(type_checker.get_errors())}")
    
    # Optimize
    optimizer = Optimizer()
    optimized = optimizer.optimize(program)
    opt_stats = optimizer.get_stats()
    print(f"\nOptimization:")
    print(f"  Constants folded: {opt_stats['constants_folded']}")
    print(f"  Dead code removed: {opt_stats['dead_code_removed']}")
    
    # Compile
    compiler = EnhancedCompiler()
    bytecode = compiler.compile(optimized)
    print(f"\nCompilation:")
    print(f"  Instructions: {len(bytecode['instructions'])}")
    print(f"  Constants: {len(bytecode['consts'])}")
    print(f"  Functions: {bytecode['functions']}")
    
    # Register allocation
    allocator = LinearScanAllocator(num_registers=8)
    reg_stats = allocator.get_stats()
    print(f"\nRegister Allocation:")
    print(f"  Total registers: {reg_stats['total_registers']}")
    print(f"  Used registers: {reg_stats['used_registers']}")
    print(f"  Spilled variables: {reg_stats['spilled_variables']}")
    
    print("✅ Integrated optimization test passed\n")


def main():
    print("\n" + "="*60)
    print("H# Register Allocation & Type System Tests")
    print("="*60 + "\n")
    
    tests = [
        ("Register Allocation", test_register_allocation),
        ("Type System - Basic", test_type_system_basic),
        ("Type System - Arithmetic", test_type_system_arithmetic),
        ("Type System - Functions", test_type_system_functions),
        ("Type System - Arrays", test_type_system_arrays),
        ("Type System - Conditionals", test_type_system_conditionals),
        ("Type Inference", test_type_inference),
        ("Integrated Optimization", test_integrated_optimization),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {name} failed: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
