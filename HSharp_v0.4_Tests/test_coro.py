import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

code = '''
coro fn c() {
    print(1);
    coro_yield();
    print(2);
    return 42;
}

let x = c();
print(x);
coro_resume(x);
coro_resume(x);
'''

lexer = Lexer(code)
parser = Parser(lexer)
program = parser.parse()
interp = Interpreter()
interp.interpret(program)
print('done')
