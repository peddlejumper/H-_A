import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

code = '''
# create two coroutines and schedule them
coro fn a() {
    print(1);
    coro_yield();
    print(3);
}

coro fn b() {
    print(2);
    coro_yield();
    print(4);
}

let A = a();
let B = b();

scheduler_run([A, B]);
'''

lexer = Lexer(code)
parser = Parser(lexer)
program = parser.parse()
interp = Interpreter()
interp.interpret(program)
print('scheduler done')
