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


class ConstantPropagation:
    """
    常量传播 pass
    在 AST 层跟踪 `let x = <常量>` 与 `x = <常量>` 赋值，把对 x 的引用替换为字面量。
    遇到非 const 赋值、函数调用、print、成员写入等可能改变 x 的语句时，淘汰对应绑定。
    """

    def __init__(self):
        self.replaced_count = 0
        # 可能产生副作用、从而保守淘汰所有绑定的语句类型
        self._side_effect_stmts = (PrintStatement,)

    def run(self, node, env=None):
        env = {} if env is None else env
        return self._visit(node, env)

    def _is_literal(self, n):
        return isinstance(n, (NumberLiteral, StringLiteral, BooleanLiteral, NullLiteral))

    def _literal_value(self, n):
        if isinstance(n, NullLiteral):
            return None
        return n.value

    def _make_literal(self, val):
        if isinstance(val, bool):
            return BooleanLiteral(val)
        if isinstance(val, (int, float)):
            return NumberLiteral(val)
        if isinstance(val, str):
            return StringLiteral(val)
        if val is None:
            return NullLiteral()
        return None

    def _visit(self, node, env):
        if node is None:
            return None

        if isinstance(node, Program):
            local = dict(env)
            new_stmts = []
            for s in node.statements:
                ns = self._visit_stmt(s, local)
                new_stmts.append(ns)
            node.statements = new_stmts
            return node

        # 单独的语句/块
        return self._visit_stmt(node, env)

    def _assigned_in(self, node):
        """收集 stmt 树中所有被赋值（AssignmentIdentifier / LetStatement / ForStatement）的变量名集合，
        用于 while 循环的安全处理——不跨 Function 作用域下钻。"""
        names = set()
        if node is None:
            return names
        if isinstance(node, Function):
            return names
        if isinstance(node, AssignmentIdentifier):
            names.add(node.name)
        elif isinstance(node, LetStatement):
            names.add(node.name)
        elif isinstance(node, ForStatement):
            names.add(node.var1)
            if getattr(node, 'var2', None):
                names.add(node.var2)
        elif isinstance(node, list):
            for x in node:
                names |= self._assigned_in(x)
            return names
        if hasattr(node, '__dict__'):
            for attr, v in vars(node).items():
                if isinstance(v, Function):
                    continue
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, AST) and not isinstance(item, Function):
                            names |= self._assigned_in(item)
                elif isinstance(v, AST) and not isinstance(v, Function):
                    names |= self._assigned_in(v)
        return names

    def _visit_stmt(self, stmt, env):
        if stmt is None:
            return None

        if isinstance(stmt, LetStatement):
            stmt.value = self._visit_expr(stmt.value, env)
            if self._is_literal(stmt.value):
                env[stmt.name] = self._literal_value(stmt.value)
            else:
                env.pop(stmt.name, None)
            return stmt

        if isinstance(stmt, AssignmentIdentifier):
            stmt.value = self._visit_expr(stmt.value, env)
            if self._is_literal(stmt.value):
                env[stmt.name] = self._literal_value(stmt.value)
            else:
                env.pop(stmt.name, None)
            return stmt

        if isinstance(stmt, AssignmentMember) or isinstance(stmt, AssignmentIndex):
            # 成员/下标写入：保守淘汰所有绑定（无法静态确认是否被别名引用）
            stmt.value = self._visit_expr(stmt.value, env)
            self._visit_expr(stmt.left if hasattr(stmt, 'left') else stmt.array, env)
            env.clear()
            return stmt

        if isinstance(stmt, PrintStatement):
            stmt.expr = self._visit_expr(stmt.expr, env)
            return stmt

        if isinstance(stmt, ReturnStatement):
            stmt.expr = self._visit_expr(stmt.expr, env)
            return stmt

        if isinstance(stmt, IfStatement):
            stmt.condition = self._visit_expr(stmt.condition, env)
            # 分支使用副本环境，合并时不保留分支内新绑定
            stmt.consequence = self._visit(stmt.consequence, dict(env))
            if stmt.alternative:
                stmt.alternative = self._visit(stmt.alternative, dict(env))
            return stmt

        if isinstance(stmt, WhileStatement):
            # 循环体可能多次执行并改写 loop 变量，因此在条件与循环体里把被赋值的变量
            # 从常量环境中剔除，避免把 `i` 折叠成初值后 `while (i < N)` 变成 `while True` 死循环。
            # 循环结束后，这些变量已不再是编译期常量，必须从外层 env 剔除，否则后续
            # `return s` / `print(s)` 会被替换成循环前的初值字面量（如 `return ""`）。
            assigned = self._assigned_in(stmt.body)
            cond_env = dict(env)
            for a in assigned:
                cond_env.pop(a, None)
            stmt.condition = self._visit_expr(stmt.condition, cond_env)
            body_env = dict(env)
            for a in assigned:
                body_env.pop(a, None)
            self._visit(stmt.body, body_env)
            for k in list(body_env.keys()):
                env.pop(k, None)
            for a in assigned:
                env.pop(a, None)
            return stmt

        if isinstance(stmt, ForStatement):
            # 循环体可能多次执行并改写内部变量，因此在条件与循环体里把被赋值的变量
            # 从常量环境中剔除，避免把循环外初值（如 `let sum = 0`）当常量代入循环体，
            # 否则 `sum = sum + d[k]` 会被折叠成 `sum = d[k]`（丢失累加）。
            assigned = self._assigned_in(stmt.body)
            iter_env = dict(env)
            for a in assigned:
                iter_env.pop(a, None)
            self._visit_expr(stmt.iterable, iter_env)
            iter_env.pop(stmt.var1, None)
            if getattr(stmt, 'var2', None):
                iter_env.pop(stmt.var2, None)
            self._visit(stmt.body, iter_env)
            for a in assigned:
                env.pop(a, None)
            env.pop(stmt.var1, None)
            if getattr(stmt, 'var2', None):
                env.pop(stmt.var2, None)
            return stmt

        if isinstance(stmt, TryStatement):
            # try/catch 区块内对变量的赋值（含 catch 处理器把 caught 改写为 true）
            # 必须让 try 之后的同名变量不再是编译期常量，否则后续 `if (caught)`
            # 会被折叠成 `if (false)` 而跳过本应在 catch 命中时执行的代码（v0.4.6）。
            assigned = self._assigned_in(stmt.body) | self._assigned_in(stmt.handler)
            if stmt.exception_name:
                assigned.add(stmt.exception_name)
            self._visit(stmt.body, dict(env))
            handler_env = dict(env)
            if stmt.exception_name:
                handler_env.pop(stmt.exception_name, None)
            self._visit(stmt.handler, handler_env)
            for a in assigned:
                env.pop(a, None)
            return stmt

        if isinstance(stmt, BlockStatement):
            local = dict(env)
            for s in stmt.statements:
                self._visit_stmt(s, local)
            return stmt

        if isinstance(stmt, Function):
            # 函数体是独立作用域，不继承外层常量绑定
            self._visit(stmt.body, {})
            return stmt

        if isinstance(stmt, (BreakStatement, ContinueStatement, DeleteStatement)):
            return stmt

        # 兜底：递归处理子 AST
        for attr, v in vars(stmt).items():
            if isinstance(v, AST):
                self._visit_expr(v, env)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, AST):
                        self._visit_expr(item, env)
        return stmt

    def _visit_expr(self, expr, env):
        if expr is None:
            return None

        if isinstance(expr, Identifier):
            if expr.name in env:
                lit = self._make_literal(env[expr.name])
                if lit is not None:
                    self.replaced_count += 1
                    return lit
            return expr

        if isinstance(expr, BinaryOp):
            expr.left = self._visit_expr(expr.left, env)
            expr.right = self._visit_expr(expr.right, env)
            return expr

        if isinstance(expr, UnaryOp):
            expr.operand = self._visit_expr(expr.operand, env)
            return expr

        if isinstance(expr, TernaryOp):
            expr.condition = self._visit_expr(expr.condition, env)
            expr.true_expr = self._visit_expr(expr.true_expr, env)
            expr.false_expr = self._visit_expr(expr.false_expr, env)
            return expr

        if isinstance(expr, CallExpression):
            expr.func = self._visit_expr(expr.func, env)
            expr.args = [self._visit_expr(a, env) for a in expr.args]
            # 函数调用可能有副作用，保守清除所有常量绑定
            env.clear()
            return expr

        if isinstance(expr, MemberExpression):
            expr.left = self._visit_expr(expr.left, env)
            return expr

        if isinstance(expr, IndexExpression):
            expr.left = self._visit_expr(expr.left, env)
            expr.index = self._visit_expr(expr.index, env)
            return expr

        if isinstance(expr, ArrayLiteral):
            expr.elements = [self._visit_expr(e, env) for e in expr.elements]
            return expr

        if isinstance(expr, DictLiteral):
            expr.pairs = [(self._visit_expr(k, env), self._visit_expr(v, env)) for k, v in expr.pairs]
            return expr

        return expr


class RangeAnalysis:
    """
    范围分析 pass
    推断整数变量的取值区间 [lo, hi]（None 表示无界）。
    利用范围信息做两类优化：
      1. 静态可判定的比较折叠（如 x < 10 且 x 上界为 5 → true）
      2. 代数化简：x * 1 → x, x + 0 → x, x * 0 → 0（仅当 x 确为 int 范围时）
    """

    def __init__(self):
        self.folded_count = 0

    def _assigned_in(self, node):
        """收集 stmt 树中被赋值的变量名集合（不跨 Function 作用域下钻）。"""
        names = set()
        if node is None:
            return names
        if isinstance(node, Function):
            return names
        if isinstance(node, AssignmentIdentifier):
            names.add(node.name)
        elif isinstance(node, LetStatement):
            names.add(node.name)
        elif isinstance(node, ForStatement):
            names.add(node.var1)
            if getattr(node, 'var2', None):
                names.add(node.var2)
        elif isinstance(node, list):
            for x in node:
                names |= self._assigned_in(x)
            return names
        if hasattr(node, '__dict__'):
            for attr, v in vars(node).items():
                if isinstance(v, Function):
                    continue
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, AST) and not isinstance(item, Function):
                            names |= self._assigned_in(item)
                elif isinstance(v, AST) and not isinstance(v, Function):
                    names |= self._assigned_in(v)
        return names

    def run(self, program):
        if not isinstance(program, Program):
            return program
        for s in program.statements:
            self._visit_stmt(s, {})
        return program

    def _visit_stmt(self, stmt, ranges):
        if stmt is None:
            return

        if isinstance(stmt, LetStatement):
            r = self._expr_range(stmt.value, ranges)
            stmt.value = self._simplify(stmt.value, ranges)
            if r is not None:
                ranges[stmt.name] = r
            else:
                ranges.pop(stmt.name, None)
            return

        if isinstance(stmt, AssignmentIdentifier):
            r = self._expr_range(stmt.value, ranges)
            stmt.value = self._simplify(stmt.value, ranges)
            if r is not None:
                ranges[stmt.name] = r
            else:
                ranges.pop(stmt.name, None)
            return

        if isinstance(stmt, IfStatement):
            stmt.condition = self._simplify(stmt.condition, ranges)
            self._visit_stmt(stmt.consequence, dict(ranges))
            if stmt.alternative:
                self._visit_stmt(stmt.alternative, dict(ranges))
            return

        if isinstance(stmt, WhileStatement):
            # 循环体会改写 loop 变量，条件里的比较不能用「进入循环前的范围」折叠
            # （否则 `i < 500` 在 i 初值 0 时会被折叠成 true → 死循环）。
            # 把循环体内被赋值的变量从范围表中剔除，条件与循环体按无界处理。
            assigned = self._assigned_in(stmt.body)
            loop_ranges = dict(ranges)
            for a in assigned:
                loop_ranges.pop(a, None)
            stmt.condition = self._simplify(stmt.condition, loop_ranges)
            self._visit_stmt(stmt.body, loop_ranges)
            for a in assigned:
                ranges.pop(a, None)
            return

        if isinstance(stmt, ForStatement):
            self._visit_expr(stmt.iterable, ranges)
            # 循环变量范围无法精确推断，保守清除
            ranges.pop(stmt.var1, None)
            if getattr(stmt, 'var2', None):
                ranges.pop(stmt.var2, None)
            self._visit_stmt(stmt.body, dict(ranges))
            return

        if isinstance(stmt, TryStatement):
            # 与 ConstantPropagation 同理：try/catch 内被赋值的变量在 try 之后
            # 不再是编译期常量，从范围表中剔除（避免范围分析错误折叠）。
            assigned = self._assigned_in(stmt.body) | self._assigned_in(stmt.handler)
            if stmt.exception_name:
                assigned.add(stmt.exception_name)
            self._visit_stmt(stmt.body, dict(ranges))
            handler_ranges = dict(ranges)
            if stmt.exception_name:
                handler_ranges.pop(stmt.exception_name, None)
            self._visit_stmt(stmt.handler, handler_ranges)
            for a in assigned:
                ranges.pop(a, None)
            return

        if isinstance(stmt, BlockStatement):
            local = dict(ranges)
            for s in stmt.statements:
                self._visit_stmt(s, local)
            return

        if isinstance(stmt, Function):
            self._visit_stmt(stmt.body, {})
            return

        if isinstance(stmt, (ReturnStatement, PrintStatement)):
            if hasattr(stmt, 'expr') and stmt.expr is not None:
                stmt.expr = self._simplify(stmt.expr, ranges)
            return

        # 兜底
        for attr, v in vars(stmt).items():
            if isinstance(v, AST):
                self._visit_expr(v, ranges)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, AST):
                        self._visit_expr(item, ranges)

    def _visit_expr(self, expr, ranges):
        if expr is None:
            return
        if isinstance(expr, BinaryOp):
            self._visit_expr(expr.left, ranges)
            self._visit_expr(expr.right, ranges)
        elif isinstance(expr, UnaryOp):
            self._visit_expr(expr.operand, ranges)
        elif isinstance(expr, CallExpression):
            self._visit_expr(expr.func, ranges)
            for a in expr.args:
                self._visit_expr(a, ranges)
        elif isinstance(expr, MemberExpression):
            self._visit_expr(expr.left, ranges)
        elif isinstance(expr, IndexExpression):
            self._visit_expr(expr.left, ranges)
            self._visit_expr(expr.index, ranges)
        elif isinstance(expr, ArrayLiteral):
            for e in expr.elements:
                self._visit_expr(e, ranges)
        elif isinstance(expr, DictLiteral):
            for k, v in expr.pairs:
                self._visit_expr(k, ranges)
                self._visit_expr(v, ranges)

    def _expr_range(self, expr, ranges):
        """返回 (lo, hi) 或 None；lo/hi 为 None 表示无界。"""
        if isinstance(expr, NumberLiteral):
            if isinstance(expr.value, bool):
                return None
            if isinstance(expr.value, int):
                return (expr.value, expr.value)
            return None  # float 不参与整数范围分析
        if isinstance(expr, BooleanLiteral):
            return (int(expr.value), int(expr.value))
        if isinstance(expr, Identifier):
            return ranges.get(expr.name)
        if isinstance(expr, BinaryOp):
            lr = self._expr_range(expr.left, ranges)
            rr = self._expr_range(expr.right, ranges)
            op_name = expr.op.name if hasattr(expr.op, 'name') else str(expr.op)
            if lr and rr and lr[0] is not None and lr[1] is not None and rr[0] is not None and rr[1] is not None:
                a_lo, a_hi = lr
                b_lo, b_hi = rr
                try:
                    if op_name == 'PLUS':
                        return (a_lo + b_lo, a_hi + b_hi)
                    if op_name == 'MINUS':
                        return (a_lo - b_hi, a_hi - b_lo)
                    if op_name == 'STAR':
                        vals = [a_lo * b_lo, a_lo * b_hi, a_hi * b_lo, a_hi * b_hi]
                        return (min(vals), max(vals))
                except Exception:
                    return None
            return None
        if isinstance(expr, UnaryOp):
            op_name = expr.op.name if hasattr(expr.op, 'name') else str(expr.op)
            r = self._expr_range(expr.operand, ranges)
            if r and r[0] is not None and r[1] is not None and op_name == 'MINUS':
                return (-r[1], -r[0])
            return None
        return None

    def _simplify(self, expr, ranges):
        if isinstance(expr, BinaryOp):
            expr.left = self._simplify(expr.left, ranges)
            expr.right = self._simplify(expr.right, ranges)
            op_name = expr.op.name if hasattr(expr.op, 'name') else str(expr.op)
            lr = self._expr_range(expr.left, ranges)
            rr = self._expr_range(expr.right, ranges)

            # 代数化简：仅当操作数确为整数范围时
            if op_name == 'PLUS':
                if isinstance(expr.right, NumberLiteral) and not isinstance(expr.right.value, bool) and expr.right.value == 0:
                    self.folded_count += 1
                    return expr.left
                if isinstance(expr.left, NumberLiteral) and not isinstance(expr.left.value, bool) and expr.left.value == 0:
                    self.folded_count += 1
                    return expr.right
            elif op_name == 'STAR':
                if isinstance(expr.right, NumberLiteral) and not isinstance(expr.right.value, bool) and expr.right.value == 1 and lr is not None:
                    self.folded_count += 1
                    return expr.left
                if isinstance(expr.left, NumberLiteral) and not isinstance(expr.left.value, bool) and expr.left.value == 1 and rr is not None:
                    self.folded_count += 1
                    return expr.right
                if isinstance(expr.right, NumberLiteral) and not isinstance(expr.right.value, bool) and expr.right.value == 0 and lr is not None:
                    self.folded_count += 1
                    return NumberLiteral(0)
                if isinstance(expr.left, NumberLiteral) and not isinstance(expr.left.value, bool) and expr.left.value == 0 and rr is not None:
                    self.folded_count += 1
                    return NumberLiteral(0)

            # 比较折叠：当两侧范围可静态判定时
            if op_name in ('LT', 'GT', 'LTE', 'GTE', 'EQEQ', 'BANGEQ') and lr and rr:
                a_lo, a_hi = lr
                b_lo, b_hi = rr
                if a_lo is not None and a_hi is not None and b_lo is not None and b_hi is not None:
                    if op_name == 'LT' and a_hi < b_lo:
                        self.folded_count += 1
                        return BooleanLiteral(True)
                    if op_name == 'LT' and a_lo >= b_hi:
                        self.folded_count += 1
                        return BooleanLiteral(False)
                    if op_name == 'GT' and a_lo > b_hi:
                        self.folded_count += 1
                        return BooleanLiteral(True)
                    if op_name == 'GT' and a_hi <= b_lo:
                        self.folded_count += 1
                        return BooleanLiteral(False)
            return expr

        if isinstance(expr, UnaryOp):
            expr.operand = self._simplify(expr.operand, ranges)
            return expr
        if isinstance(expr, TernaryOp):
            expr.condition = self._simplify(expr.condition, ranges)
            expr.true_expr = self._simplify(expr.true_expr, ranges)
            expr.false_expr = self._simplify(expr.false_expr, ranges)
            return expr
        if isinstance(expr, CallExpression):
            expr.func = self._simplify(expr.func, ranges)
            expr.args = [self._simplify(a, ranges) for a in expr.args]
            return expr
        if isinstance(expr, MemberExpression):
            expr.left = self._simplify(expr.left, ranges)
            return expr
        if isinstance(expr, IndexExpression):
            expr.left = self._simplify(expr.left, ranges)
            expr.index = self._simplify(expr.index, ranges)
            return expr
        if isinstance(expr, ArrayLiteral):
            expr.elements = [self._simplify(e, ranges) for e in expr.elements]
            return expr
        if isinstance(expr, DictLiteral):
            expr.pairs = [(self._simplify(k, ranges), self._simplify(v, ranges)) for k, v in expr.pairs]
            return expr
        return expr


class Optimizer:
    """
    Main optimizer that applies multiple optimization passes
    """

    def __init__(self):
        self.constant_folder = ConstantFolder()
        self.dead_code_eliminator = DeadCodeEliminator()
        self.constant_propagation = ConstantPropagation()
        self.range_analysis = RangeAnalysis()
        self.stats = {
            'constants_folded': 0,
            'dead_code_removed': 0,
            'constants_propagated': 0,
            'range_folded': 0,
        }

    def optimize(self, program):
        """Apply all optimization passes to a program"""
        # Pass 1: 常量传播（先于 folding，把变量替换为字面量后 folding 更有效）
        program = self.constant_propagation.run(program)
        self.stats['constants_propagated'] = self.constant_propagation.replaced_count

        # Pass 2: Constant folding on expressions
        program = self._apply_constant_folding(program)
        self.stats['constants_folded'] = self.constant_folder.optimized_count

        # Pass 3: 范围分析 + 代数化简
        program = self.range_analysis.run(program)
        self.stats['range_folded'] = self.range_analysis.folded_count

        # Pass 4: Dead code elimination
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
