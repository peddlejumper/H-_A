#!/usr/bin/env python3
"""
Test runner for H# bootstrap modules
Validates that all new bootstrap components can be loaded and executed
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
parent = os.path.abspath(os.path.join(ROOT, '..'))
if parent not in sys.path:
    sys.path.insert(0, parent)

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

def load_and_test_module(module_name):
    """Load and test a bootstrap module"""
    module_path = os.path.join(ROOT, f'{module_name}.hto')
    
    if not os.path.exists(module_path):
        print(f"❌ Module not found: {module_path}")
        return False
    
    print(f"\n{'='*60}")
    print(f"Testing: {module_name}")
    print(f"{'='*60}")
    
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        print(f"✓ File loaded ({len(code)} bytes)")
        
        # Parse the module
        lexer = Lexer(code)
        parser = Parser(lexer)
        program = parser.parse()
        
        print(f"✓ Parsing successful")
        
        # Create interpreter and execute
        interp = Interpreter()
        
        # Add necessary builtins for modules that need them
        def host_read_file(args):
            path = args[0]
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                return None
        
        def host_write_file(args):
            path = args[0]
            data = args[1]
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(data)
                return True
            except Exception:
                return False
        
        def host_time_now(args):
            import time
            return int(time.time() * 1000)
        
        interp.builtins['read_file'] = host_read_file
        interp.builtins['write_file'] = host_write_file
        interp.builtins['time_now'] = host_time_now
        
        # Execute the module
        result = interp.interpret(program)
        
        print(f"✓ Execution successful")
        
        # Check what functions were defined
        func_count = len(interp.functions)
        print(f"✓ Functions defined: {func_count}")
        
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Runtime Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print("H# Bootstrap Module Test Suite")
    print("="*60)
    
    modules_to_test = [
        'env_optimized',
        'perf_monitor',
        'string_utils',
        'array_utils',
        'math_utils',
        'formatter',
        'linter',
    ]
    
    results = {}
    
    for module in modules_to_test:
        success = load_and_test_module(module)
        results[module] = success
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for module, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} - {module}")
    
    print("="*60)
    print(f"Total: {passed}/{total} modules passed")
    print("="*60)
    
    if passed == total:
        print("\n🎉 All bootstrap modules loaded successfully!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} module(s) failed to load")
        return 1

if __name__ == '__main__':
    sys.exit(main())
