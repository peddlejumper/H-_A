"""
Enhanced H# Bytecode Compiler
Compiles H# AST to bytecode with support for advanced features
"""

from h_ast import *
from tokens import TokenType

class EnhancedCompiler:
    """Advanced bytecode compiler with closure support and optimizations"""
    
    def __init__(self):
        self.consts = []
        self.instructions = []
        self.functions = {}
        self.current_function = None
        self.label_counter = 0
        self.closure_vars = {}
        
    def new_label(self):
        """Generate a unique label"""
        label = f"L{self.label_counter}"
        self.label_counter += 1
        return label
    
    def add_const(self, value):
        """Add constant and return its index"""
        try:
            idx = self.consts.index(value)
        except ValueError:
            idx = len(self.consts)
            self.consts.append(value)
        return idx
    
    def emit(self, opname, arg=None):
        """Emit a bytecode instruction"""
        self.instructions.append((opname, arg))
    
    def emit_label(self, label):
        """Emit a label marker"""
        self.instructions.append(('LABEL', label))
    
    def compile(self, program):
        """Compile a Program AST to bytecode"""
        if not isinstance(program, Program):
            raise CompileError("Expected Program node")
        
        # Compile all top-level statements
        for stmt in program.statements:
            self.compile_stmt(stmt)
        
        # Add HALT instruction
        self.emit('HALT')
        
        return {
            'instructions': self.instructions,
            'consts': self.consts,
            'functions': list(self.functions.keys())
        }
    
    def compile_stmt(self, stmt):
        """Compile a statement"""
        if isinstance(stmt, LetStatement):
            self.compile_let(stmt)
        elif isinstance(stmt, PrintStatement):
            self.compile_print(stmt)
        elif isinstance(stmt, Function):
            self.compile_function(stmt)
        elif isinstance(stmt, ReturnStatement):
            self.compile_return(stmt)
        elif isinstance(stmt, WhileStatement):
            self.compile_while(stmt)
        elif isinstance(stmt, IfStatement):
            self.compile_if(stmt)
        elif isinstance(stmt, ForStatement):
            self.compile_for(stmt)
        elif isinstance(stmt, BlockStatement):
            self.compile_block(stmt)
        elif isinstance(stmt, BreakStatement):
            self.emit('BREAK')
        elif isinstance(stmt, ContinueStatement):
            self.emit('CONTINUE')
        else:
            # Expression statement
            self.compile_expr(stmt)
            self.emit('POP_TOP')
    
    def compile_let(self, stmt):
        """Compile let statement"""
        self.compile_expr(stmt.value)
        self.emit('STORE_NAME', stmt.name)
    
    def compile_print(self, stmt):
        """Compile print statement"""
        self.compile_expr(stmt.expr)
        self.emit('PRINT')
    
    def compile_function(self, stmt):
        """Compile function declaration"""
        # Save current state
        old_instructions = self.instructions
        old_consts = self.consts
        old_label_counter = self.label_counter
        
        # Reset for function body
        self.instructions = []
        self.consts = []
        self.label_counter = 0
        self.current_function = stmt.name
        
        # Compile function body
        if isinstance(stmt.body, BlockStatement):
            for s in stmt.body.statements:
                self.compile_stmt(s)
        else:
            self.compile_stmt(stmt.body)
        
        # Ensure function returns None if no explicit return
        if not self.ends_with_return(stmt.body):
            self.emit('LOAD_CONST', self.add_const(None))
            self.emit('RETURN')
        
        # Store function bytecode
        self.functions[stmt.name] = {
            'params': stmt.params,
            'instructions': self.instructions,
            'consts': self.consts,
            'arity': len(stmt.params)
        }
        
        # Restore state
        self.instructions = old_instructions
        self.consts = old_consts
        self.label_counter = old_label_counter
        self.current_function = None
        
        # In main code, just register the function
        self.emit('MAKE_FUNCTION', stmt.name)
    
    def ends_with_return(self, node):
        """Check if a node ends with a return statement"""
        if isinstance(node, ReturnStatement):
            return True
        if isinstance(node, BlockStatement) and node.statements:
            return self.ends_with_return(node.statements[-1])
        return False
    
    def compile_return(self, stmt):
        """Compile return statement"""
        if stmt.expr:
            self.compile_expr(stmt.expr)
        else:
            self.emit('LOAD_CONST', self.add_const(None))
        self.emit('RETURN')
    
    def compile_while(self, stmt):
        """Compile while loop"""
        start_label = self.new_label()
        end_label = self.new_label()
        
        self.emit_label(start_label)
        self.compile_expr(stmt.condition)
        self.emit('JUMP_IF_FALSE', end_label)
        
        if isinstance(stmt.body, BlockStatement):
            for s in stmt.body.statements:
                self.compile_stmt(s)
        else:
            self.compile_stmt(stmt.body)
        
        self.emit('JUMP', start_label)
        self.emit_label(end_label)
    
    def compile_if(self, stmt):
        """Compile if statement"""
        false_label = self.new_label()
        end_label = self.new_label()
        
        self.compile_expr(stmt.condition)
        self.emit('JUMP_IF_FALSE', false_label)
        
        if isinstance(stmt.consequence, BlockStatement):
            for s in stmt.consequence.statements:
                self.compile_stmt(s)
        else:
            self.compile_stmt(stmt.consequence)
        
        self.emit('JUMP', end_label)
        self.emit_label(false_label)
        
        if stmt.alternative:
            if isinstance(stmt.alternative, BlockStatement):
                for s in stmt.alternative.statements:
                    self.compile_stmt(s)
            else:
                self.compile_stmt(stmt.alternative)
        
        self.emit_label(end_label)
    
    def compile_for(self, stmt):
        """Compile for-in loop"""
        # Evaluate iterable
        self.compile_expr(stmt.iterable)
        
        # Get iterator
        self.emit('GET_ITERATOR')
        
        start_label = self.new_label()
        end_label = self.new_label()
        
        self.emit_label(start_label)
        
        # Get next item
        self.emit('ITER_NEXT', end_label)
        
        # Store in loop variable(s)
        if stmt.var2:
            # Destructuring: for (key, value in dict)
            self.emit('DUP_TOP')
            self.emit('LOAD_CONST', self.add_const(0))
            self.emit('BINARY_SUBSCR')
            self.emit('STORE_NAME', stmt.var1)
            
            self.emit('DUP_TOP')
            self.emit('LOAD_CONST', self.add_const(1))
            self.emit('BINARY_SUBSCR')
            self.emit('STORE_NAME', stmt.var2)
        else:
            self.emit('STORE_NAME', stmt.var1)
        
        # Compile body
        if isinstance(stmt.body, BlockStatement):
            for s in stmt.body.statements:
                self.compile_stmt(s)
        else:
            self.compile_stmt(stmt.body)
        
        self.emit('JUMP', start_label)
        self.emit_label(end_label)
        self.emit('POP_TOP')  # Clean up iterator
    
    def compile_block(self, stmt):
        """Compile block statement"""
        for s in stmt.statements:
            self.compile_stmt(s)
    
    def compile_expr(self, expr):
        """Compile an expression"""
        if isinstance(expr, NumberLiteral):
            self.emit('LOAD_CONST', self.add_const(expr.value))
        elif isinstance(expr, StringLiteral):
            self.emit('LOAD_CONST', self.add_const(expr.value))
        elif isinstance(expr, BooleanLiteral):
            self.emit('LOAD_CONST', self.add_const(expr.value))
        elif isinstance(expr, NullLiteral):
            self.emit('LOAD_CONST', self.add_const(None))
        elif isinstance(expr, Identifier):
            self.emit('LOAD_NAME', expr.name)
        elif isinstance(expr, BinaryOp):
            self.compile_binary_op(expr)
        elif isinstance(expr, UnaryOp):
            self.compile_unary_op(expr)
        elif isinstance(expr, CallExpression):
            self.compile_call(expr)
        elif isinstance(expr, ArrayLiteral):
            self.compile_array(expr)
        elif isinstance(expr, DictLiteral):
            self.compile_dict(expr)
        elif isinstance(expr, IndexExpression):
            self.compile_index(expr)
        elif isinstance(expr, MemberExpression):
            self.compile_member(expr)
        elif isinstance(expr, Lambda):
            self.compile_lambda(expr)
        else:
            raise CompileError(f"Unknown expression type: {type(expr).__name__}")
    
    def compile_binary_op(self, expr):
        """Compile binary operation"""
        self.compile_expr(expr.left)
        self.compile_expr(expr.right)
        
        # Handle both string and TokenType operators
        op = expr.op
        if hasattr(op, 'name'):
            op_name = op.name
        else:
            op_name = str(op)
        
        op_map = {
            'PLUS': 'BINARY_ADD',
            'MINUS': 'BINARY_SUBTRACT',
            'STAR': 'BINARY_MULTIPLY',
            'SLASH': 'BINARY_DIVIDE',
            'EQEQ': 'COMPARE_EQ',
            'BANGEQ': 'COMPARE_NE',
            'LT': 'COMPARE_LT',
            'GT': 'COMPARE_GT',
            'LTE': 'COMPARE_LE',
            'GTE': 'COMPARE_GE',
            'AND': 'LOGICAL_AND',
            'OR': 'LOGICAL_OR',
        }
        
        bytecode_op = op_map.get(op_name)
        if bytecode_op:
            self.emit(bytecode_op)
        else:
            raise CompileError(f"Unknown operator: {op_name}")
    
    def compile_unary_op(self, expr):
        """Compile unary operation"""
        self.compile_expr(expr.operand)
        
        if expr.op == 'MINUS':
            self.emit('UNARY_NEGATIVE')
        elif expr.op == 'NOT':
            self.emit('UNARY_NOT')
        else:
            raise CompileError(f"Unknown unary operator: {expr.op}")
    
    def compile_call(self, expr):
        """Compile function call"""
        # Compile function
        self.compile_expr(expr.func)
        
        # Compile arguments
        for arg in expr.args:
            self.compile_expr(arg)
        
        # Emit call with argument count
        self.emit('CALL_FUNCTION', len(expr.args))
    
    def compile_array(self, expr):
        """Compile array literal"""
        for elem in expr.elements:
            self.compile_expr(elem)
        self.emit('BUILD_LIST', len(expr.elements))
    
    def compile_dict(self, expr):
        """Compile dictionary literal"""
        for key, value in expr.pairs:
            self.compile_expr(key)
            self.compile_expr(value)
        self.emit('BUILD_DICT', len(expr.pairs))
    
    def compile_index(self, expr):
        """Compile index expression"""
        self.compile_expr(expr.left)
        self.compile_expr(expr.index)
        self.emit('BINARY_SUBSCR')
    
    def compile_member(self, expr):
        """Compile member access"""
        self.compile_expr(expr.left)
        self.emit('LOAD_ATTR', expr.name)
    
    def compile_lambda(self, expr):
        """Compile lambda/closure"""
        # Similar to function but creates a closure object
        old_instructions = self.instructions
        old_consts = self.consts
        
        self.instructions = []
        self.consts = []
        
        # Compile body
        if isinstance(expr.body, BlockStatement):
            for s in expr.body.statements:
                self.compile_stmt(s)
        else:
            self.compile_stmt(expr.body)
        
        self.emit('RETURN')
        
        # Create closure
        self.emit('MAKE_CLOSURE', expr.params)
        
        # Restore
        self.instructions = old_instructions
        self.consts = old_consts


class CompileError(Exception):
    """Compilation error"""
    pass
