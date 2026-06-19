"""
H# Type System
Implements static type checking and type inference for H#
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Set, Union


class TypeKind(Enum):
    """Type kinds in H#"""
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    BOOL = auto()
    VOID = auto()
    NULL = auto()
    ARRAY = auto()
    DICT = auto()
    FUNCTION = auto()
    UNKNOWN = auto()
    ERROR = auto()


class HType:
    """Base class for all types"""
    
    def __init__(self, kind: TypeKind):
        self.kind = kind
    
    def __eq__(self, other):
        if isinstance(other, HType):
            return self.kind == other.kind
        return False
    
    def __repr__(self):
        return f"HType({self.kind.name})"
    
    def is_subtype_of(self, other: 'HType') -> bool:
        """Check if this type is a subtype of another"""
        if self.kind == other.kind:
            return True
        # int is subtype of float
        if self.kind == TypeKind.INT and other.kind == TypeKind.FLOAT:
            return True
        return False


class ArrayType(HType):
    """Array type with element type"""
    
    def __init__(self, element_type: HType):
        super().__init__(TypeKind.ARRAY)
        self.element_type = element_type
    
    def __eq__(self, other):
        if isinstance(other, ArrayType):
            return self.element_type == other.element_type
        return False
    
    def __repr__(self):
        return f"Array[{self.element_type}]"


class DictType(HType):
    """Dictionary type with key and value types"""
    
    def __init__(self, key_type: HType, value_type: HType):
        super().__init__(TypeKind.DICT)
        self.key_type = key_type
        self.value_type = value_type
    
    def __eq__(self, other):
        if isinstance(other, DictType):
            return (self.key_type == other.key_type and 
                    self.value_type == other.value_type)
        return False
    
    def __repr__(self):
        return f"Dict[{self.key_type}, {self.value_type}]"


class FunctionType(HType):
    """Function type with parameter and return types"""
    
    def __init__(self, param_types: List[HType], return_type: HType):
        super().__init__(TypeKind.FUNCTION)
        self.param_types = param_types
        self.return_type = return_type
    
    def __eq__(self, other):
        if isinstance(other, FunctionType):
            return (self.param_types == other.param_types and 
                    self.return_type == other.return_type)
        return False
    
    def __repr__(self):
        params = ", ".join(str(t) for t in self.param_types)
        return f"Fn({params}) -> {self.return_type}"


# Predefined types
INT_TYPE = HType(TypeKind.INT)
FLOAT_TYPE = HType(TypeKind.FLOAT)
STRING_TYPE = HType(TypeKind.STRING)
BOOL_TYPE = HType(TypeKind.BOOL)
VOID_TYPE = HType(TypeKind.VOID)
NULL_TYPE = HType(TypeKind.NULL)
UNKNOWN_TYPE = HType(TypeKind.UNKNOWN)
ERROR_TYPE = HType(TypeKind.ERROR)


class TypeEnvironment:
    """Type environment mapping variables to their types"""
    
    def __init__(self, parent=None):
        self.types: Dict[str, HType] = {}
        self.parent = parent
    
    def add(self, name: str, htype: HType):
        """Add a variable with its type"""
        self.types[name] = htype
    
    def lookup(self, name: str) -> Optional[HType]:
        """Lookup the type of a variable"""
        if name in self.types:
            return self.types[name]
        if self.parent:
            return self.parent.lookup(name)
        return None
    
    def update(self, name: str, htype: HType):
        """Update the type of a variable"""
        if name in self.types:
            self.types[name] = htype
        elif self.parent:
            self.parent.update(name, htype)
        else:
            self.add(name, htype)


class TypeError(Exception):
    """Type checking error"""
    
    def __init__(self, message: str, line: int = 0):
        self.message = message
        self.line = line
        super().__init__(f"Type Error (line {line}): {message}")


class TypeChecker:
    """
    Static type checker for H# programs
    Performs type checking and type inference
    """
    
    def __init__(self):
        self.errors: List[TypeError] = []
        self.warnings: List[str] = []
    
    def check_program(self, program) -> bool:
        """Type check an entire program"""
        env = TypeEnvironment()
        
        # Add built-in types
        self._add_builtins(env)
        
        # Check each statement
        for stmt in program.statements:
            try:
                self.check_statement(stmt, env)
            except TypeError as e:
                self.errors.append(e)
        
        return len(self.errors) == 0
    
    def check_statement(self, stmt, env: TypeEnvironment) -> HType:
        """Type check a statement"""
        from h_ast import (
            LetStatement, PrintStatement, ReturnStatement,
            IfStatement, WhileStatement, ForStatement,
            BlockStatement, Function
        )
        
        if isinstance(stmt, LetStatement):
            return self.check_let_statement(stmt, env)
        elif isinstance(stmt, PrintStatement):
            return self.check_print_statement(stmt, env)
        elif isinstance(stmt, ReturnStatement):
            return self.check_return_statement(stmt, env)
        elif isinstance(stmt, IfStatement):
            return self.check_if_statement(stmt, env)
        elif isinstance(stmt, WhileStatement):
            return self.check_while_statement(stmt, env)
        elif isinstance(stmt, ForStatement):
            return self.check_for_statement(stmt, env)
        elif isinstance(stmt, BlockStatement):
            return self.check_block_statement(stmt, env)
        elif isinstance(stmt, Function):
            return self.check_function(stmt, env)
        else:
            return UNKNOWN_TYPE
    
    def check_expression(self, expr, env: TypeEnvironment) -> HType:
        """Type check an expression and return its type"""
        from h_ast import (
            NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral,
            Identifier, BinaryOp, UnaryOp, CallExpression,
            ArrayLiteral, DictLiteral, IndexExpression, Lambda
        )
        
        if isinstance(expr, NumberLiteral):
            if isinstance(expr.value, int):
                return INT_TYPE
            else:
                return FLOAT_TYPE
        
        elif isinstance(expr, StringLiteral):
            return STRING_TYPE
        
        elif isinstance(expr, BooleanLiteral):
            return BOOL_TYPE
        
        elif isinstance(expr, NullLiteral):
            return NULL_TYPE
        
        elif isinstance(expr, Identifier):
            htype = env.lookup(expr.name)
            if htype is None:
                self.errors.append(TypeError(
                    f"Undefined variable '{expr.name}'",
                    getattr(expr, 'line', 0)
                ))
                return ERROR_TYPE
            return htype
        
        elif isinstance(expr, BinaryOp):
            return self.check_binary_op(expr, env)
        
        elif isinstance(expr, UnaryOp):
            return self.check_unary_op(expr, env)
        
        elif isinstance(expr, CallExpression):
            return self.check_call_expression(expr, env)
        
        elif isinstance(expr, ArrayLiteral):
            return self.check_array_literal(expr, env)
        
        elif isinstance(expr, DictLiteral):
            return self.check_dict_literal(expr, env)
        
        elif isinstance(expr, IndexExpression):
            return self.check_index_expression(expr, env)
        
        elif isinstance(expr, Lambda):
            return self.check_lambda(expr, env)
        
        else:
            return UNKNOWN_TYPE
    
    def check_binary_op(self, expr, env: TypeEnvironment) -> HType:
        """Type check binary operation"""
        left_type = self.check_expression(expr.left, env)
        right_type = self.check_expression(expr.right, env)
        
        op_name = expr.op.name if hasattr(expr.op, 'name') else str(expr.op)
        
        # Arithmetic operations
        if op_name in ['PLUS', 'MINUS', 'STAR', 'SLASH']:
            if left_type.kind in [TypeKind.INT, TypeKind.FLOAT] and \
               right_type.kind in [TypeKind.INT, TypeKind.FLOAT]:
                # Result is float if either operand is float
                if left_type.kind == TypeKind.FLOAT or right_type.kind == TypeKind.FLOAT:
                    return FLOAT_TYPE
                return INT_TYPE
            elif op_name == 'PLUS' and \
                 (left_type.kind == TypeKind.STRING or right_type.kind == TypeKind.STRING):
                return STRING_TYPE
            else:
                self.errors.append(TypeError(
                    f"Cannot apply '{op_name}' to {left_type} and {right_type}",
                    getattr(expr, 'line', 0)
                ))
                return ERROR_TYPE
        
        # Comparison operations
        elif op_name in ['EQEQ', 'BANGEQ', 'LT', 'GT', 'LTE', 'GTE']:
            if left_type.kind == right_type.kind or \
               (left_type.kind in [TypeKind.INT, TypeKind.FLOAT] and 
                right_type.kind in [TypeKind.INT, TypeKind.FLOAT]):
                return BOOL_TYPE
            else:
                self.errors.append(TypeError(
                    f"Cannot compare {left_type} and {right_type}",
                    getattr(expr, 'line', 0)
                ))
                return ERROR_TYPE
        
        # Logical operations
        elif op_name in ['AND', 'OR']:
            if left_type.kind == TypeKind.BOOL and right_type.kind == TypeKind.BOOL:
                return BOOL_TYPE
            else:
                self.errors.append(TypeError(
                    f"Logical operators require bool operands",
                    getattr(expr, 'line', 0)
                ))
                return ERROR_TYPE
        
        return ERROR_TYPE
    
    def check_unary_op(self, expr, env: TypeEnvironment) -> HType:
        """Type check unary operation"""
        operand_type = self.check_expression(expr.operand, env)
        
        op_name = expr.op.name if hasattr(expr.op, 'name') else str(expr.op)
        
        if op_name == 'MINUS':
            if operand_type.kind in [TypeKind.INT, TypeKind.FLOAT]:
                return operand_type
            else:
                self.errors.append(TypeError(
                    f"Cannot negate {operand_type}",
                    getattr(expr, 'line', 0)
                ))
                return ERROR_TYPE
        
        elif op_name == 'NOT':
            if operand_type.kind == TypeKind.BOOL:
                return BOOL_TYPE
            else:
                self.errors.append(TypeError(
                    f"Cannot apply 'not' to {operand_type}",
                    getattr(expr, 'line', 0)
                ))
                return ERROR_TYPE
        
        return ERROR_TYPE
    
    def check_let_statement(self, stmt, env: TypeEnvironment) -> HType:
        """Type check let statement"""
        value_type = self.check_expression(stmt.value, env)
        # name can be string or Identifier
        var_name = stmt.name if isinstance(stmt.name, str) else stmt.name.value
        env.add(var_name, value_type)
        return VOID_TYPE
    
    def check_print_statement(self, stmt, env: TypeEnvironment) -> HType:
        """Type check print statement"""
        self.check_expression(stmt.expr, env)
        return VOID_TYPE
    
    def check_return_statement(self, stmt, env: TypeEnvironment) -> HType:
        """Type check return statement"""
        if stmt.expr:
            return self.check_expression(stmt.expr, env)
        return VOID_TYPE
    
    def check_if_statement(self, stmt, env: TypeEnvironment) -> HType:
        """Type check if statement"""
        cond_type = self.check_expression(stmt.condition, env)
        if cond_type.kind != TypeKind.BOOL:
            self.errors.append(TypeError(
                f"If condition must be bool, got {cond_type}",
                getattr(stmt, 'line', 0)
            ))
        
        self.check_statement(stmt.consequence, env)
        if stmt.alternative:
            self.check_statement(stmt.alternative, env)
        
        return VOID_TYPE
    
    def check_while_statement(self, stmt, env: TypeEnvironment) -> HType:
        """Type check while statement"""
        cond_type = self.check_expression(stmt.condition, env)
        if cond_type.kind != TypeKind.BOOL:
            self.errors.append(TypeError(
                f"While condition must be bool, got {cond_type}",
                getattr(stmt, 'line', 0)
            ))
        
        self.check_statement(stmt.body, env)
        return VOID_TYPE
    
    def check_for_statement(self, stmt, env: TypeEnvironment) -> HType:
        """Type check for statement"""
        iterable_type = self.check_expression(stmt.iterable, env)
        if iterable_type.kind != TypeKind.ARRAY:
            self.errors.append(TypeError(
                f"For loop requires array, got {iterable_type}",
                getattr(stmt, 'line', 0)
            ))
        
        # Create new scope for loop variable
        loop_env = TypeEnvironment(parent=env)
        # var1 can be string or Identifier
        var_name = stmt.var1 if isinstance(stmt.var1, str) else stmt.var1.value
        loop_env.add(var_name, UNKNOWN_TYPE)
        self.check_statement(stmt.body, loop_env)
        
        return VOID_TYPE
    
    def check_block_statement(self, stmt, env: TypeEnvironment) -> HType:
        """Type check block statement"""
        block_env = TypeEnvironment(parent=env)
        for s in stmt.statements:
            self.check_statement(s, block_env)
        return VOID_TYPE
    
    def check_function(self, func, env: TypeEnvironment) -> HType:
        """Type check function declaration"""
        # Create function environment
        func_env = TypeEnvironment(parent=env)
        
        # Add parameters (params can be strings or Identifiers)
        param_types = []
        for param in func.params:
            param_name = param if isinstance(param, str) else param.value
            func_env.add(param_name, UNKNOWN_TYPE)
            param_types.append(UNKNOWN_TYPE)
        
        # Check body
        self.check_statement(func.body, func_env)
        
        # Register function type
        func_type = FunctionType(param_types, UNKNOWN_TYPE)
        func_name = func.name if isinstance(func.name, str) else func.name.value
        env.add(func_name, func_type)
        
        return func_type
    
    def check_call_expression(self, expr, env: TypeEnvironment) -> HType:
        """Type check function call"""
        func_type = self.check_expression(expr.func, env)
        
        if func_type.kind != TypeKind.FUNCTION:
            self.errors.append(TypeError(
                f"Cannot call non-function type {func_type}",
                getattr(expr, 'line', 0)
            ))
            return ERROR_TYPE
        
        # Check argument count
        if isinstance(func_type, FunctionType):
            if len(expr.args) != len(func_type.param_types):
                self.errors.append(TypeError(
                    f"Expected {len(func_type.param_types)} arguments, got {len(expr.args)}",
                    getattr(expr, 'line', 0)
                ))
            
            # Check argument types
            for i, arg in enumerate(expr.args):
                if i < len(func_type.param_types):
                    arg_type = self.check_expression(arg, env)
                    expected_type = func_type.param_types[i]
                    if not arg_type.is_subtype_of(expected_type):
                        self.warnings.append(
                            f"Argument {i}: expected {expected_type}, got {arg_type}"
                        )
            
            return func_type.return_type
        
        return UNKNOWN_TYPE
    
    def check_array_literal(self, expr, env: TypeEnvironment) -> HType:
        """Type check array literal"""
        if not expr.elements:
            return ArrayType(UNKNOWN_TYPE)
        
        # Infer element type from first element
        elem_type = self.check_expression(expr.elements[0], env)
        
        # Check all elements have compatible types
        for elem in expr.elements[1:]:
            elem_t = self.check_expression(elem, env)
            if elem_t != elem_type:
                self.warnings.append(
                    f"Mixed array element types: {elem_type} and {elem_t}"
                )
        
        return ArrayType(elem_type)
    
    def check_dict_literal(self, expr, env: TypeEnvironment) -> HType:
        """Type check dict literal"""
        if not expr.pairs:
            return DictType(UNKNOWN_TYPE, UNKNOWN_TYPE)
        
        # Infer key and value types
        key_type = self.check_expression(expr.pairs[0][0], env)
        value_type = self.check_expression(expr.pairs[0][1], env)
        
        return DictType(key_type, value_type)
    
    def check_index_expression(self, expr, env: TypeEnvironment) -> HType:
        """Type check index expression"""
        left_type = self.check_expression(expr.left, env)
        index_type = self.check_expression(expr.index, env)
        
        if left_type.kind == TypeKind.ARRAY:
            if index_type.kind != TypeKind.INT:
                self.errors.append(TypeError(
                    f"Array index must be int, got {index_type}",
                    getattr(expr, 'line', 0)
                ))
            if isinstance(left_type, ArrayType):
                return left_type.element_type
        elif left_type.kind == TypeKind.DICT:
            if isinstance(left_type, DictType):
                return left_type.value_type
        else:
            self.errors.append(TypeError(
                f"Cannot index {left_type}",
                getattr(expr, 'line', 0)
            ))
        
        return ERROR_TYPE
    
    def check_lambda(self, expr, env: TypeEnvironment) -> HType:
        """Type check lambda expression"""
        param_types = []
        for param in expr.params:
            param_name = param if isinstance(param, str) else param.value
            param_types.append(UNKNOWN_TYPE)
        return_type = self.check_expression(expr.body, env)
        return FunctionType(param_types, return_type)
    
    def _add_builtins(self, env: TypeEnvironment):
        """Add built-in functions and types"""
        # Built-in functions
        env.add('print', FunctionType([UNKNOWN_TYPE], VOID_TYPE))
        env.add('len', FunctionType([UNKNOWN_TYPE], INT_TYPE))
        env.add('str', FunctionType([UNKNOWN_TYPE], STRING_TYPE))
        env.add('int', FunctionType([UNKNOWN_TYPE], INT_TYPE))
        env.add('float', FunctionType([UNKNOWN_TYPE], FLOAT_TYPE))
        env.add('bool', FunctionType([UNKNOWN_TYPE], BOOL_TYPE))
        env.add('push', FunctionType([ArrayType(UNKNOWN_TYPE), UNKNOWN_TYPE], VOID_TYPE))
        env.add('pop', FunctionType([ArrayType(UNKNOWN_TYPE)], UNKNOWN_TYPE))
    
    def get_errors(self) -> List[TypeError]:
        """Get all type errors"""
        return self.errors
    
    def get_warnings(self) -> List[str]:
        """Get all type warnings"""
        return self.warnings
    
    def has_errors(self) -> bool:
        """Check if there are any type errors"""
        return len(self.errors) > 0
