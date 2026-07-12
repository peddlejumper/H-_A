"""
H# Compiler Optimizations
Implements various optimization passes for the H# bytecode compiler
"""

from h_ast import *

class ConstantFolder:
    """
    Constant Folding Optimization
    Evaluates constant expressions at compile time
    """
    
    def __init__(self):
        self.optimized_count = 0
    
    def fold(self, node):
        """Apply constant folding to an AST node"""
        if isinstance(node, BinaryOp):
            return self.fold_binary_op(node)
        elif isinstance(node, UnaryOp):
            return self.fold_unary_op(node)
        else:
            return node
    
    def fold_binary_op(self, node):
        """Fold binary operations with constant operands"""
        # First, recursively fold children
        left = self.fold(node.left)
        right = self.fold(node.right)
        
        # Check if both operands are constants
        if self.is_constant(left) and self.is_constant(right):
            left_val = self.get_value(left)
            right_val = self.get_value(right)
            
            result = self.evaluate_binary(node.op, left_val, right_val)
            if result is not None:
                self.optimized_count += 1
                # Return appropriate literal node
                if isinstance(result, bool):
                    return BooleanLiteral(result)
                elif isinstance(result, (int, float)):
                    return NumberLiteral(result)
                elif isinstance(result, str):
                    return StringLiteral(result)
                elif result is None:
                    return NullLiteral()
        
        # Cannot fold, return modified node
        node.left = left
        node.right = right
        return node
    
    def fold_unary_op(self, node):
        """Fold unary operations with constant operand"""
        operand = self.fold(node.operand)
        
        if self.is_constant(operand):
            val = self.get_value(operand)
            result = self.evaluate_unary(node.op, val)
            if result is not None:
                self.optimized_count += 1
                if isinstance(result, bool):
                    return BooleanLiteral(result)
                elif isinstance(result, (int, float)):
                    return NumberLiteral(result)
                elif isinstance(result, str):
                    return StringLiteral(result)
        
        node.operand = operand
        return node
    
    def is_constant(self, node):
        """Check if a node is a constant literal"""
        return isinstance(node, (NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral))
    
    def get_value(self, node):
        """Extract value from a constant node"""
        if isinstance(node, NumberLiteral):
            return node.value
        elif isinstance(node, StringLiteral):
            return node.value
        elif isinstance(node, BooleanLiteral):
            return node.value
        elif isinstance(node, NullLiteral):
            return None
        return None
    
    def evaluate_binary(self, op, left, right):
        """Evaluate a binary operation on constants"""
        try:
            # Handle string concatenation
            if isinstance(left, str) or isinstance(right, str):
                if hasattr(op, 'name'):
                    op_name = op.name
                else:
                    op_name = str(op)
                
                if op_name == 'PLUS':
                    return str(left) + str(right)
                return None
            
            # Numeric operations
            if hasattr(op, 'name'):
                op_name = op.name
            else:
                op_name = str(op)
            
            if op_name == 'PLUS':
                return left + right
            elif op_name == 'MINUS':
                return left - right
            elif op_name == 'STAR':
                return left * right
            elif op_name == 'SLASH':
                if right == 0:
                    return None  # Division by zero
                return left / right
            elif op_name == 'EQEQ':
                return left == right
            elif op_name == 'BANGEQ':
                return left != right
            elif op_name == 'LT':
                return left < right
            elif op_name == 'GT':
                return left > right
            elif op_name == 'LTE':
                return left <= right
            elif op_name == 'GTE':
                return left >= right
            elif op_name == 'AND':
                return left and right
            elif op_name == 'OR':
                return left or right
        except:
            pass
        
        return None
    
    def evaluate_unary(self, op, operand):
        """Evaluate a unary operation on constant"""
        try:
            if hasattr(op, 'name'):
                op_name = op.name
            else:
                op_name = str(op)
            
            if op_name == 'MINUS':
                return -operand
            elif op_name == 'NOT':
                return not operand
        except:
            pass
        
        return None


class DeadCodeEliminator:
    """
    Dead Code Elimination
    Removes unreachable code and unused variables
    """
    
    def __init__(self):
        self.removed_count = 0
    
    def eliminate(self, program):
        """Apply dead code elimination to a program"""
        if not isinstance(program, Program):
            return program
        
        # Remove unreachable statements after unconditional jumps/returns
        optimized_stmts = []
        unreachable = False
        
        for stmt in program.statements:
            if unreachable:
                # Skip dead code
                self.removed_count += 1
                continue
            
            optimized_stmts.append(stmt)
            
            # Check if this statement makes following code unreachable
            if isinstance(stmt, ReturnStatement):
                unreachable = True
            elif isinstance(stmt, BreakStatement) or isinstance(stmt, ContinueStatement):
                # These only affect loops, handled separately
                pass
        
        program.statements = optimized_stmts
        return program
    
    def eliminate_in_function(self, func_node):
        """Eliminate dead code in function body"""
        if not isinstance(func_node, Function):
            return func_node
        
        if isinstance(func_node.body, BlockStatement):
            optimized = []
            unreachable = False
            
            for stmt in func_node.body.statements:
                if unreachable:
                    self.removed_count += 1
                    continue
                
                optimized.append(stmt)
                
                if isinstance(stmt, ReturnStatement):
                    unreachable = True
            
            func_node.body.statements = optimized
        
        return func_node


class Optimizer:
    """
    Main optimizer that applies multiple optimization passes
    """
    
    def __init__(self):
        self.constant_folder = ConstantFolder()
        self.dead_code_eliminator = DeadCodeEliminator()
        self.stats = {
            'constants_folded': 0,
            'dead_code_removed': 0
        }
    
    def optimize(self, program):
        """Apply all optimization passes to a program"""
        # Pass 1: Constant folding on expressions
        program = self._apply_constant_folding(program)
        self.stats['constants_folded'] = self.constant_folder.optimized_count
        
        # Pass 2: Dead code elimination
        program = self.dead_code_eliminator.eliminate(program)
        self.stats['dead_code_removed'] = self.dead_code_eliminator.removed_count
        
        return program
    
    def _apply_constant_folding(self, node):
        """Recursively apply constant folding to all expressions"""
        if node is None:
            return None
        
        # Apply folding to this node
        folded = self.constant_folder.fold(node)
        
        # Recursively process children
        if isinstance(folded, Program):
            folded.statements = [self._apply_constant_folding(s) for s in folded.statements]
        elif isinstance(folded, LetStatement):
            folded.value = self._apply_constant_folding(folded.value)
        elif isinstance(folded, PrintStatement):
            folded.expr = self._apply_constant_folding(folded.expr)
        elif isinstance(folded, ReturnStatement):
            folded.expr = self._apply_constant_folding(folded.expr)
        elif isinstance(folded, IfStatement):
            folded.condition = self._apply_constant_folding(folded.condition)
            folded.consequence = self._apply_constant_folding(folded.consequence)
            if folded.alternative:
                folded.alternative = self._apply_constant_folding(folded.alternative)
        elif isinstance(folded, WhileStatement):
            folded.condition = self._apply_constant_folding(folded.condition)
            folded.body = self._apply_constant_folding(folded.body)
        elif isinstance(folded, ForStatement):
            folded.iterable = self._apply_constant_folding(folded.iterable)
            folded.body = self._apply_constant_folding(folded.body)
        elif isinstance(folded, BlockStatement):
            folded.statements = [self._apply_constant_folding(s) for s in folded.statements]
        elif isinstance(folded, Function):
            folded.body = self._apply_constant_folding(folded.body)
        elif isinstance(folded, CallExpression):
            folded.func = self._apply_constant_folding(folded.func)
            folded.args = [self._apply_constant_folding(a) for a in folded.args]
        elif isinstance(folded, ArrayLiteral):
            folded.elements = [self._apply_constant_folding(e) for e in folded.elements]
        elif isinstance(folded, DictLiteral):
            folded.pairs = [(self._apply_constant_folding(k), self._apply_constant_folding(v)) 
                           for k, v in folded.pairs]
        elif isinstance(folded, IndexExpression):
            folded.left = self._apply_constant_folding(folded.left)
            folded.index = self._apply_constant_folding(folded.index)
        elif isinstance(folded, MemberExpression):
            folded.left = self._apply_constant_folding(folded.left)
        
        return folded
    
    def get_stats(self):
        """Get optimization statistics"""
        return self.stats
