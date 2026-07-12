#!/usr/bin/env python3
"""
Test runner for new H# standard library modules
Tests datetime, io, and fs modules
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter


def test_module_loading(module_name, module_file):
    """Test that a module can be loaded and parsed successfully"""
    print(f"\nTesting module: {module_name}")
    print("-" * 50)

    try:
        with open(module_file, 'r', encoding='utf-8') as f:
            code = f.read()

        # Lexical analysis and parsing
        lexer = Lexer(code)
        parser = Parser(lexer)
        ast = parser.parse()

        # Count functions defined in module
        function_count = 0
        if hasattr(ast, 'statements'):
            for stmt in ast.statements:
                if hasattr(stmt, '__class__') and stmt.__class__.__name__ == 'Function':
                    function_count += 1

        print(f"  Code size: {len(code)} bytes")
        print(f"  AST nodes: Generated successfully")
        print(f"  Functions defined: {function_count}")
        print(f"  Status: PASS")
        return True

    except Exception as e:
        print(f"  Error: {e}")
        print(f"  Status: FAIL")
        return False


def test_host_functions():
    """Test that new host functions are registered"""
    print("\nTesting Host Functions Registration")
    print("-" * 50)

    try:
        interpreter = Interpreter()

        required_functions = [
            # Date/Time
            'date_now', 'date_timestamp', 'date_format', 'date_parse',
            # File System
            'fs_exists', 'fs_is_file', 'fs_is_dir', 'fs_mkdir',
            'fs_remove', 'fs_list_dir', 'fs_get_cwd', 'fs_chdir',
            'fs_join_path', 'fs_get_ext', 'fs_get_basename', 'fs_get_dirname',
            # IO helpers
            'io_append_file', 'io_read_lines', 'io_write_lines'
        ]

        missing = []
        for func_name in required_functions:
            if func_name not in interpreter.builtins:
                missing.append(func_name)

        if len(missing) == 0:
            print(f"  All {len(required_functions)} host functions registered")
            print(f"  Status: PASS")
            return True
        else:
            print(f"  Missing functions: {', '.join(missing)}")
            print(f"  Status: FAIL")
            return False

    except Exception as e:
        print(f"  Error: {e}")
        print(f"  Status: FAIL")
        return False


def test_basic_execution(test_file):
    """Test basic execution of a test file"""
    print(f"\nExecuting test file: {test_file}")
    print("-" * 50)

    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            code = f.read()

        # Create interpreter
        interpreter = Interpreter()

        # Parse and execute
        lexer = Lexer(code)
        parser = Parser(lexer)
        ast = parser.parse()

        # Execute (this will print output)
        result = interpreter.interpret(ast)

        print(f"  Execution completed")
        print(f"  Status: PASS")
        return True

    except Exception as e:
        print(f"  Error: {e}")
        print(f"  Status: FAIL")
        return False


def main():
    print("=" * 60)
    print("H# Standard Library Module Tests")
    print("=" * 60)

    results = {}

    # Test 1: Module loading
    modules = [
        ("DateTime Module", "bootstrap/datetime_module.hto"),
        ("IO Module", "bootstrap/io_module.hto"),
        ("FileSystem Module", "bootstrap/fs_module.hto"),
    ]

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for name, path in modules:
        full_path = os.path.join(base_dir, path)
        results[name] = test_module_loading(name, full_path)

    # Test 2: Host functions
    results["Host Functions"] = test_host_functions()

    # Test 3: Execute comprehensive test
    test_file = os.path.join(base_dir, "bootstrap/test_standard_libs.hto")
    results["Test Execution"] = test_basic_execution(test_file)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\nAll tests passed! New standard library modules are working correctly.")
        return 0
    else:
        print(f"\n{total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
