import sys
import os
import json
from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from compiler import Compiler
from bytecode import VM

def run(code, filename="<input>"):
    try:
        lexer = Lexer(code)
        parser = Parser(lexer)
        program = parser.parse()
        interpreter = Interpreter()
        interpreter.interpret(program)
    except SyntaxError as e:
        print(f"Syntax Error in {filename}: {e}")
    except Exception as e:
        print(f"Error in {filename}: {e}")


def compile_optimized(code, filename="<input>"):
    """
    完整优化管线：AST 优化 → 编译 → bytecode 优化。
    返回可供 VM 直接运行的 bytecode dict。
    """
    from compiler_optimizations import Optimizer
    from register_allocation import optimize_bytecode

    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()

    # AST 层优化：常量传播 + 常量折叠 + 范围分析 + 死代码消除
    optimizer = Optimizer()
    program = optimizer.optimize(program)

    # 编译到 bytecode
    compiler = Compiler(use_hcompiler=True)
    bc = compiler.compile(program)

    # bytecode 层优化：窥孔 + fast locals 分配
    bc = optimize_bytecode(bc)
    return bc, optimizer.stats, bc.get('opt_stats', {})


def run_optimized(code, filename="<input>"):
    """编译（带优化）并通过字节码 VM 执行。"""
    try:
        bc, _ast_stats, _bc_stats = compile_optimized(code, filename)
        vm = VM(bc)
        vm.run()
    except SyntaxError as e:
        print(f"Syntax Error in {filename}: {e}")
    except Exception as e:
        print(f"Error in {filename}: {e}")


def repl():
    print("H# v0.4 REPL. Type 'exit' to quit.")
    interpreter = Interpreter()
    while True:
        try:
            line = input("h#> ").strip()
            if line == "exit":
                break
            if not line:
                continue
            if not line.endswith(';') and not line.startswith(('let ', 'fn ', 'while ', 'if ', 'for ', 'print ', 'return ', 'import ')):
                line += ';'
            lexer = Lexer(line)
            parser = Parser(lexer)
            program = parser.parse()
            interpreter.interpret(program)
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

def main(argv=None):
    import sys as _sys
    args = list(argv if argv is not None else _sys.argv[1:])

    # simple flags
    if args:
        if args[0] in ('-h', '--help'):
            print('H# CLI\nUsage: hsharp.py [--opt] [--emit-bc file.hto] [--run-bc file.hbc] [file.hto]')
            _sys.exit(0)
        if args[0] in ('-v', '--version'):
            print('H# v0.4')
            _sys.exit(0)

    if not args:
        repl()
        _sys.exit(0)

    # CLI modes:
    # 1) python hsharp.py file.hto
    # 2) python hsharp.py --opt file.hto          -> 优化编译并通过字节码 VM 执行
    # 3) python hsharp.py --emit-bc file.hto      -> writes file.hbc (JSON)
    # 4) python hsharp.py --run-bc file.hbc       -> executes compiled bytecode

    # --opt 标志：启用完整优化管线（AST 优化 + bytecode 优化 + 优化 VM）
    use_opt = False
    if args[0] == '--opt':
        use_opt = True
        args = args[1:]
        if not args:
            print('Usage: hsharp.py --opt file.hto')
            _sys.exit(1)

    if args[0] == '--run-bc':
        if len(args) < 2:
            print('Usage: hsharp.py --run-bc file.hbc')
            _sys.exit(1)
        bcf = args[1]
        if not os.path.exists(bcf):
            print(f'Error: File not found: {bcf}')
            _sys.exit(1)
        with open(bcf, 'r', encoding='utf-8') as f:
            bc = json.load(f)
        # Accept both the flat {instructions,consts} format and the
        # modules-wrapped {version,modules:{main:{...}}} container.
        if isinstance(bc, dict) and 'modules' in bc:
            mods = bc['modules']
            mod = mods.get('main') or next(iter(mods.values()))
            bc = {'instructions': mod['instructions'], 'consts': mod.get('consts', [])}
        vm = VM(bc)
        vm.run()
        _sys.exit(0)

    emit_bc = False
    if args[0] == '--emit-bc':
        emit_bc = True
        if len(args) < 2:
            print('Usage: hsharp.py --emit-bc file.hto')
            _sys.exit(1)
        filepath = args[1]
    else:
        filepath = args[0]

    if not filepath.endswith('.hto'):
        print(f"Warning: H# source files should use .hto extension (got {filepath})")
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        _sys.exit(1)
    with open(filepath, 'r', encoding='utf-8') as f:
        code = f.read()

    if emit_bc:
        try:
            if use_opt:
                bc, _ast_stats, _bc_stats = compile_optimized(code, filepath)
            else:
                lexer = Lexer(code)
                parser = Parser(lexer)
                program = parser.parse()
                # Use H#-backed compiler when available for emitting bytecode
                compiler = Compiler(use_hcompiler=True)
                bc = compiler.compile(program)
            # Wrap in the standard .hbc container format expected by
            # Kotlin HbcReader: {version, modules:{main:{instructions,consts}}, built_at}
            import time as _time
            if isinstance(bc, dict) and 'modules' not in bc and 'instructions' in bc:
                hbc = {
                    'version': 'v0.4',
                    'modules': {
                        'main': {
                            'instructions': bc['instructions'],
                            'consts': bc.get('consts', []),
                        }
                    },
                    'built_at': int(_time.time()),
                }
            else:
                hbc = bc
            out = filepath.rsplit('.', 1)[0] + '.hbc'
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(hbc, f)
            print(f'Wrote bytecode to {out}')
        except Exception as e:
            print(f'Compilation error: {e}')
        _sys.exit(0)

    if use_opt:
        run_optimized(code, filepath)
    else:
        # default: run source via interpreter
        run(code, filepath)


if __name__ == '__main__':
    main()