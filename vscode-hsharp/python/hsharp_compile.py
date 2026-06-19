"""
hsharp_compile.py — H# .hto → .hbc compiler entry point used by the VS Code
extension. Bundled with the extension in `python/`, so the extension does
NOT need an external `HSharp_v0.4_Tests/` checkout.

Usage:
    python3 hsharp_compile.py <input.hto> <output.hbc> [module_name]

The script writes a JSON .hbc file. Errors are printed to stderr and
the process exits with a non-zero code on failure.
"""
import sys, json, time, traceback, os

def main():
    if len(sys.argv) < 3:
        sys.stderr.write("usage: hsharp_compile.py <input.hto> <output.hbc> [module_name]\n")
        return 2
    in_path = sys.argv[1]
    out_path = sys.argv[2]
    mod_name = sys.argv[3] if len(sys.argv) > 3 else "main"
    try:
        # Local imports: the bundling host is expected to invoke us from the
        # directory where lexer.py / parser.py / compiler.py / tokens.py live.
        from lexer import Lexer
        from parser import Parser
        from compiler import Compiler
        with open(in_path, "r", encoding="utf-8") as f:
            src = f.read()
        p = Parser(Lexer(src))
        program = p.parse()
        c = Compiler()
        c.compile(program)
        hbc = {
            "version": "v0.4",
            "modules": {mod_name: {"instructions": c.instructions, "consts": c.consts}},
            "built_at": int(time.time()),
        }
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(hbc, f)
        sys.stdout.write("compiled " + in_path + " -> " + out_path + "\n")
        return 0
    except Exception as e:
        sys.stderr.write("compile error: " + str(e) + "\n")
        traceback.print_exc(file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
