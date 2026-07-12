#!/usr/bin/env python3
"""
Test all new H# features and modules
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_optimizations():
    """Test compiler optimizations"""
    print("="*60)
    print("Testing Compiler Optimizations")
    print("="*60)
    
    from lexer import Lexer
    from parser import Parser
    from compiler_optimizations import Optimizer
    
    # Test constant folding
    code = """
    let x = 2 + 3;
    let y = 10 * 5;
    let z = "Hello" + " " + "World";
    print(x);
    print(y);
    print(z);
    """
    
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    
    optimizer = Optimizer()
    optimized = optimizer.optimize(program)
    
    stats = optimizer.get_stats()
    print(f"Constants folded: {stats['constants_folded']}")
    print(f"Dead code removed: {stats['dead_code_removed']}")
    print("✅ Optimization test passed\n")

def test_io_module():
    """Test IO module functions"""
    print("="*60)
    print("Testing IO Module")
    print("="*60)
    
    from io_module import (
        io_getcwd, io_listdir, io_file_exists
    )
    
    # Test getcwd
    cwd = io_getcwd()
    print(f"Current directory: {cwd}")
    
    # Test listdir
    files = io_listdir()
    print(f"Files in directory: {len(files)} items")
    
    # Test file_exists
    exists = io_file_exists(["hsharp.py"])
    print(f"hsharp.py exists: {exists}")
    
    print("✅ IO module test passed\n")

def test_datetime_module():
    """Test DateTime module functions"""
    print("="*60)
    print("Testing DateTime Module")
    print("="*60)
    
    from datetime_module import (
        dt_now, dt_year, dt_month, dt_day, 
        dt_hour, dt_minute, dt_second, dt_iso_format
    )
    
    # Test current time
    now = dt_now()
    print(f"Current timestamp: {now}")
    
    # Test date components
    print(f"Year: {dt_year()}")
    print(f"Month: {dt_month()}")
    print(f"Day: {dt_day()}")
    print(f"Hour: {dt_hour()}")
    print(f"Minute: {dt_minute()}")
    print(f"Second: {dt_second()}")
    
    # Test ISO format
    iso = dt_iso_format()
    print(f"ISO format: {iso}")
    
    print("✅ DateTime module test passed\n")

def test_debugger():
    """Test debugger support"""
    print("="*60)
    print("Testing Debugger Support")
    print("="*60)
    
    from debugger import Debugger
    
    dbg = Debugger()
    
    # Test breakpoint setting
    dbg.set_breakpoint(10)
    dbg.set_breakpoint(20)
    print(f"Breakpoints set: {dbg.breakpoints}")
    
    # Test enable/disable
    dbg.enable()
    print(f"Debugger enabled: {dbg.enabled}")
    
    dbg.disable()
    print(f"Debugger disabled: {dbg.enabled}")
    
    # Test clear
    dbg.clear_breakpoint(10)
    print(f"After clearing one: {dbg.breakpoints}")
    
    dbg.clear_all_breakpoints()
    print(f"After clearing all: {dbg.breakpoints}")
    
    print("✅ Debugger test passed\n")

def test_enhanced_compiler():
    """Test enhanced compiler with optimizations"""
    print("="*60)
    print("Testing Enhanced Compiler with Optimizations")
    print("="*60)
    
    from lexer import Lexer
    from parser import Parser
    from enhanced_compiler import EnhancedCompiler
    from compiler_optimizations import Optimizer
    
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
    
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    
    # Apply optimizations
    optimizer = Optimizer()
    optimized_program = optimizer.optimize(program)
    
    # Compile
    compiler = EnhancedCompiler()
    bytecode = compiler.compile(optimized_program)
    
    print(f"Instructions: {len(bytecode['instructions'])}")
    print(f"Constants: {len(bytecode['consts'])}")
    print(f"Functions: {bytecode['functions']}")
    
    stats = optimizer.get_stats()
    print(f"Optimizations applied:")
    print(f"  - Constants folded: {stats['constants_folded']}")
    print(f"  - Dead code removed: {stats['dead_code_removed']}")
    
    print("✅ Enhanced compiler test passed\n")

def main():
    print("\n" + "="*60)
    print("H# New Features Comprehensive Test")
    print("="*60 + "\n")
    
    tests = [
        ("Compiler Optimizations", test_optimizations),
        ("IO Module", test_io_module),
        ("DateTime Module", test_datetime_module),
        ("Debugger Support", test_debugger),
        ("Enhanced Compiler", test_enhanced_compiler),
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
