from h_ast import *
from tokens import TokenType

# Token types for operators that might not be in TokenType yet
_MODULO = getattr(TokenType, '_MOD', getattr(TokenType, 'MODULO', '%'))

class CompileError(Exception):
    pass

class SuperExpression(AST):
    def __init__(self, method_name, args):
        self.method_name = method_name
        self.args = args

class InstanceOfExpression(AST):
    def __init__(self, expr, type_name):
        self.expr = expr
        self.type_name = type_name

class Compiler:
    def _backpatch_breaks(self, target, old_breaks, old_continues):
        for pos in self.pending_breaks:
            self.instructions[pos] = ('JUMP', target)
        self.pending_breaks = old_breaks
        self.pending_continues = old_continues

    def add_const(self, value):
        if isinstance(value, bool):
            for i, v in enumerate(self.consts):
                if v is value:
                    return i
        else:
            for i, v in enumerate(self.consts):
                if type(v) is not bool and v == value:
                    return i
        idx = len(self.consts)
        self.consts.append(value)
        return idx

    def emit(self, opname, arg=None):
        self.instructions.append((opname, arg))

    def compile(self, program):
        # program: Program AST
        for stmt in program.statements:
            self.compile_stmt(stmt)
        self.emit('HALT')
        return {'instructions': self.instructions, 'consts': self.consts}

    def _find_free_vars_in_stmt(self, node, bound):
        """Walk `node` (statement or expression AST) and return the set of
        names that are referenced but **not** bound within `node` itself.

        `bound` is the set of names that are visible from outside `node` —
        i.e. the function's parameters plus everything in the enclosing
        scope.  Names defined inside the function (via `let` or as
        function parameters of an inner function) shadow the outer
        bindings.

        This is a tree walk; it does not understand control flow, so a name
        only used after a `return` will still be reported.  That's fine for
        our purposes — the only thing that matters is that *true* free
        variables are reported (false positives are tolerable; false
        negatives are not).
        """
        from h_ast import (Identifier, LetStatement, Function, Lambda,
                           BlockStatement, CallExpression, MemberExpression,
                           IndexExpression, AssignmentIdentifier,
                           AssignmentMember, AssignmentIndex, IfStatement,
                           WhileStatement, ForStatement, ReturnStatement,
                           PrintStatement, TryStatement, ThrowStatement,
                           UnaryOp, BinaryOp, TernaryOp, QuaternaryOp,
                           StringLiteral, NumberLiteral, BooleanLiteral,
                           NullLiteral, ArrayLiteral, DictLiteral,
                           UnionConstructExpression, NewExpression,
                           SuperExpression, SliceExpression, AST)

        def visit(n, b, free):
            """Walk `n` with currently-bound set `b`.  Returns the (possibly
            augmented) bound set so that callers in a sequential block can
            carry forward the new bindings.  Free-variable findings are
            added to `free` (which the caller can pass in to keep them
            isolated — important for nested lambdas)."""
            if n is None:
                return b
            if isinstance(n, Identifier):
                if n.name not in b:
                    free.add(n.name)
                return b
            if isinstance(n, LetStatement):
                visit(n.value, b, free)
                b = set(b)
                b.add(n.name)
                return b
            if isinstance(n, Function):
                # The function binds its name in the enclosing scope.
                # We do NOT recurse into its body here: the inner
                # function's own free variables are computed separately
                # when that function is compiled.  Recursing here with
                # only the inner function's params would discard the
                # outer scope's bindings, so names bound in the outer
                # scope (e.g. via `let`) would be wrongly reported as
                # free variables of the enclosing function.
                nb = set(b)
                nb.add(n.name)
                return nb
            if isinstance(n, Lambda):
                # Lambda introduces a fresh scope — its body sees only
                # its own params (and what they themselves bind).  Any
                # names it references from the enclosing scope become
                # *its own* free variables, computed separately when the
                # lambda is compiled.  Crucially, those names must NOT
                # leak into the enclosing function's free-variable set
                # (which would falsely make the enclosing function
                # capture them and hide real free-variable errors, and
                # would also force the enclosing function to wrap those
                # names in closure cells needlessly).  Achieved by
                # walking the lambda body with its own `local_free` set.
                #
                # EXCEPTION: the inner lambda's *own* free variables
                # (names that come from beyond this function) DO need to
                # be captured by this function, because creating the
                # inner lambda's closure requires those values to be on
                # the stack.  So names found in `local_free` that are
                # NOT in this function's own bound set get promoted into
                # the outer free set.
                local_free = set()
                inner_b = set(n.params)
                for s in n.body.statements:
                    # IMPORTANT: carry forward the returned bound set
                    # so `let` statements inside the lambda body bind
                    # their name for subsequent statements.
                    inner_b = visit(s, inner_b, local_free)
                # Promote names that the inner lambda needs but this
                # function hasn't bound itself.
                for fv in local_free:
                    if fv not in b:
                        free.add(fv)
                return b
            if isinstance(n, BlockStatement):
                for s in n.statements:
                    b = visit(s, b, free)
                return b
            if isinstance(n, CallExpression):
                visit(n.func, b, free)
                for a in n.args:
                    visit(a, b, free)
                return b
            if isinstance(n, MemberExpression):
                visit(n.left, b, free)
                return b
            if isinstance(n, IndexExpression):
                visit(n.left, b, free)
                visit(n.index, b, free)
                return b
            if isinstance(n, SliceExpression):
                visit(n.start, b, free)
                visit(n.end, b, free)
                visit(n.step, b, free)
                return b
            if isinstance(n, AssignmentIdentifier):
                visit(n.value, b, free)
                return b
            if isinstance(n, AssignmentMember):
                visit(n.left, b, free)
                visit(n.value, b, free)
                return b
            if isinstance(n, AssignmentIndex):
                visit(n.array, b, free)
                visit(n.index, b, free)
                visit(n.value, b, free)
                return b
            if isinstance(n, IfStatement):
                visit(n.condition, b, free)
                if n.consequence is not None:
                    bt = b
                    for s in n.consequence.statements:
                        bt = visit(s, bt, free)
                if n.alternative is not None:
                    if isinstance(n.alternative, IfStatement):
                        # nested if: use the carried-forward bound set
                        # from the consequence so `let` bindings in the
                        # consequence are visible in this nested if
                        # (this is the standard scoping rule).
                        visit(n.alternative, bt, free)
                    else:
                        bt2 = b
                        for s in n.alternative.statements:
                            bt2 = visit(s, bt2, free)
                # The names bound inside the consequence or alternative
                # are NOT visible in the function's outer scope (they
                # only exist in their respective blocks), so we keep
                # returning the original `b`.  However, the inner visits
                # may have used a local copy of `b` to track let-bindings
                # across statements; that local tracking happens in the
                # visitors themselves (visit is recursive).
                return b
            if isinstance(n, WhileStatement):
                visit(n.condition, b, free)
                for s in n.body.statements:
                    b = visit(s, b, free)
                return b
            if isinstance(n, ForStatement):
                nb = set(b)
                nb.add(n.var1)
                if n.var2 is not None: nb.add(n.var2)
                visit(n.iterable, b, free)
                for s in n.body.statements:
                    nb = visit(s, nb, free)
                return b
            if isinstance(n, ReturnStatement):
                visit(n.expr, b, free)
                return b
            if isinstance(n, PrintStatement):
                visit(n.expr, b, free)
                return b
            if isinstance(n, TryStatement):
                for s in n.body.statements:
                    b = visit(s, b, free)
                nb = set(b)
                nb.add(n.exception_name)
                visit(n.handler, nb, free)
                return b
            if isinstance(n, ThrowStatement):
                visit(n.expr, b, free)
                return b
            if isinstance(n, UnaryOp):
                visit(n.operand, b, free)
                return b
            if isinstance(n, BinaryOp):
                visit(n.left, b, free)
                visit(n.right, b, free)
                return b
            if isinstance(n, TernaryOp):
                visit(n.condition, b, free)
                visit(n.true_expr, b, free)
                visit(n.false_expr, b, free)
                return b
            if isinstance(n, QuaternaryOp):
                visit(n.cond1, b, free)
                visit(n.expr1, b, free)
                visit(n.cond2, b, free)
                visit(n.expr2, b, free)
                return b
            if isinstance(n, UnionConstructExpression):
                if hasattr(n, 'type_name'):
                    visit(n.type_name, b, free)
                for v in n.values:
                    visit(v, b, free)
                return b
            if isinstance(n, NewExpression):
                visit(n.class_name, b, free)
                for a in n.args:
                    visit(a, b, free)
                return b
            if isinstance(n, SuperExpression):
                for a in n.args:
                    visit(a, b, free)
                return b
            if isinstance(n, (StringLiteral, NumberLiteral, BooleanLiteral, NullLiteral)):
                return b
            if isinstance(n, ArrayLiteral):
                for e in n.elements:
                    visit(e, b, free)
                return b
            if isinstance(n, DictLiteral):
                for k, v in n.pairs:
                    visit(k, b, free)
                    visit(v, b, free)
                return b
            if isinstance(n, AST):
                for attr, v in vars(n).items():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, AST):
                                visit(item, b, free)
                    elif isinstance(v, AST):
                        visit(v, b, free)
                return b
            return b

        free = set()
        visit(node, set(bound), free)
        return list(free)

    def __init__(self, use_hcompiler=False):
        self.use_hcompiler = use_hcompiler
        self.consts = []
        self.instructions = []
        self._labels = []
        self.interfaces = {}
        self.pending_breaks = []
        self.pending_continues = []
        # Names that are free variables in the *enclosing* function — if we
        # see LOAD/STORE of one of these inside this compilation unit, we
        # must emit LOAD_DEREF/STORE_DEREF instead so the value is read out
        # of (and written back into) the closure cell rather than the local
        # frame's env.
        self.deref_names = set()
        # Names that are bound in this compilation unit (parameters + lets).
        # Used to decide what is a free variable when compiling a nested
        # function.  Empty for the module top level.
        self.bound = set()

    # -- name access helpers ---------------------------------------------
    def emit_load_name(self, name):
        import os
        if os.environ.get('HFVDEBUG') and name in ('f', 'g', 'a', 'b'):
            print(f"  emit_load_name({name}) deref_names={self.deref_names} -> {'LOAD_DEREF' if name in self.deref_names else 'LOAD_NAME'}", flush=True)
        if name in self.deref_names:
            self.emit('LOAD_DEREF', name)
        else:
            self.emit('LOAD_NAME', name)

    def emit_store_name(self, name):
        if name in self.deref_names:
            self.emit('STORE_DEREF', name)
        else:
            self.emit('STORE_NAME', name)

    def compile_stmt(self, stmt):
        from h_ast import ClassDeclaration, AssignmentMember, MemberExpression, NewExpression, UnionDeclaration, UnionConstructExpression
        if isinstance(stmt, LetStatement):
            self.compile_expr(stmt.value)
            self.emit_store_name(stmt.name)
            self.bound.add(stmt.name)
        elif isinstance(stmt, PrintStatement):
            self.compile_expr(stmt.expr)
            self.emit('PRINT')
        elif isinstance(stmt, Function):
            # 1. Compute free variables used inside this function.  The
            #    only things that count as "bound" inside the function are
            #    its own parameters and its own `let`s — anything the
            #    function uses from the enclosing scope is a free var.
            #    The function's *own* name is implicitly bound in the
            #    enclosing scope by this declaration (this is what makes
            #    `fn fact(n) { ... fact(n-1) ... }` recursive work
            #    without `fact` being treated as a free variable of
            #    itself).
            freevars = [
                fv for fv in self._find_free_vars_in_stmt(
                    stmt.body, set(stmt.params) | {stmt.name}
                ) if fv != stmt.name
            ]
            # 2. Compile the body in a fresh compiler that knows which
            #    names are *free* in the enclosing function and must
            #    therefore go through the closure cell.
            comp = Compiler()
            comp.bound = set(stmt.params) | {stmt.name}
            comp.deref_names = set(freevars)
            for s in stmt.body.statements:
                comp.compile_stmt(s)
            comp.emit('RETURN_VALUE')
            func_obj = {
                'args': stmt.params,
                'bytecode': comp.instructions,
                'consts': comp.consts,
                'freevars': list(freevars),
            }
            idx = self.add_const(func_obj)
            # 3. Emit closure construction at the call site.  The VM
            #    pops the function from the top of the stack first, then
            #    pops the freevars below, so the function must be pushed
            #    last (i.e. emitted after the freevars).
            for fv in freevars:
                self.emit_load_name(fv)
            self.emit('LOAD_CONST', idx)
            if freevars:
                self.emit('MAKE_CLOSURE', len(freevars))
            self.emit_store_name(stmt.name)
        elif isinstance(stmt, ReturnStatement):
            if stmt.expr is not None:
                self.compile_expr(stmt.expr)
            else:
                # bare `return;` — push null so RETURN_VALUE has a value
                self.emit('LOAD_CONST', self.add_const(None))
            self.emit('RETURN_VALUE')
        elif isinstance(stmt, WhileStatement):
            start = len(self.instructions)
            self.compile_expr(stmt.condition)
            self.emit('JUMP_IF_FALSE', None)
            jmp_false_pos = len(self.instructions)-1

            old_breaks = self.pending_breaks
            old_continues = self.pending_continues
            self.pending_breaks = []
            self.pending_continues = [start]

            for s in stmt.body.statements:
                self.compile_stmt(s)
            self.emit('JUMP', start)
            end = len(self.instructions)
            self.instructions[jmp_false_pos] = ('JUMP_IF_FALSE', end)

            self._backpatch_breaks(end, old_breaks, old_continues)
        elif isinstance(stmt, IfStatement):
            self.compile_expr(stmt.condition)
            self.emit('JUMP_IF_FALSE', None)
            jmp_false_pos = len(self.instructions)-1
            # consequence
            for s in stmt.consequence.statements:
                self.compile_stmt(s)
            if stmt.alternative:
                self.emit('JUMP', None)
                jmp_end_pos = len(self.instructions)-1
                alt_start = len(self.instructions)
                self.instructions[jmp_false_pos] = ('JUMP_IF_FALSE', alt_start)
                if isinstance(stmt.alternative, IfStatement):
                    self.compile_stmt(stmt.alternative)
                else:
                    for s in stmt.alternative.statements:
                        self.compile_stmt(s)
                end = len(self.instructions)
                self.instructions[jmp_end_pos] = ('JUMP', end)
            else:
                end = len(self.instructions)
                self.instructions[jmp_false_pos] = ('JUMP_IF_FALSE', end)
        elif isinstance(stmt, ImportStatement):
            # Emit import opcodes so the VM can perform imports at runtime.
            # stmt.path may be a string ("file.hto") or an Identifier (module name)
            if isinstance(stmt.path, str):
                self.emit('IMPORT_FILE', stmt.path)
            else:
                # assume Identifier
                self.emit('IMPORT_NAME', stmt.path.name)
            return
        elif isinstance(stmt, ClassDeclaration):
            # compile methods and default fields into a class object constant
            methods = {}
            fields = {}
            private_fields = []
            for s in stmt.body.statements:
                if isinstance(s, Function):
                    comp = Compiler()
                    for sub in s.body.statements:
                        comp.compile_stmt(sub)
                    comp.emit('RETURN_VALUE')
                    func_obj = {'args': s.params, 'bytecode': comp.instructions, 'consts': comp.consts}
                    if getattr(s, 'is_static', False):
                        # store static methods as top-level attributes on the class object
                        # they will be callable via ClassName.method(...)
                        methods.setdefault('__static__', {})[s.name] = func_obj
                    else:
                        methods[s.name] = func_obj
                elif isinstance(s, FieldDeclaration):
                    # only support literal defaults at compile time
                    def eval_literal(node):
                        if isinstance(node, NumberLiteral):
                            return node.value
                        if isinstance(node, StringLiteral):
                            return node.value
                        if isinstance(node, BooleanLiteral):
                            return node.value
                        if isinstance(node, ArrayLiteral):
                            return [eval_literal(e) for e in node.elements]
                        if isinstance(node, DictLiteral):
                            d = {}
                            for k, v in node.pairs:
                                kk = eval_literal(k)
                                vv = eval_literal(v)
                                d[kk] = vv
                            return d
                        return None
                    val = eval_literal(s.value)
                    fields[s.name] = val
                    if s.is_private:
                        private_fields.append(s.name)
            # if class implements interfaces, ensure default methods from interfaces are copied in
            for iface_name in getattr(stmt, 'implements', []) or []:
                iface = self.interfaces.get(iface_name)
                if iface is None:
                    raise CompileError(f"Interface '{iface_name}' not found for class '{stmt.name}'")
                for mname, sig in iface.get('methods', {}).items():
                    if mname not in methods:
                        if sig.get('bytecode') is not None:
                            methods[mname] = sig
                        else:
                            raise CompileError(f"Class '{stmt.name}' does not implement interface method '{mname}' from '{iface_name}'")
                    else:
                        # check arity
                        if len(methods[mname].get('args', [])) != len(sig.get('args', [])):
                            raise CompileError(f"Method '{mname}' in class '{stmt.name}' has wrong arity for interface '{iface_name}'")

            class_obj = {'name': stmt.name, 'methods': methods, 'fields': fields, 'private': private_fields}
            if getattr(stmt, 'base', None):
                class_obj['base'] = stmt.base
            if getattr(stmt, 'implements', None):
                class_obj['implements'] = stmt.implements
            # move any static methods recorded under methods['__static__'] to top-level for runtime
            if '__static__' in class_obj['methods']:
                class_obj['__static__'] = class_obj['methods'].pop('__static__')
            idx = self.add_const(class_obj)
            self.emit('LOAD_CONST', idx)
            self.emit('STORE_NAME', stmt.name)
        elif isinstance(stmt, InterfaceDeclaration):
            # compile interface methods (store defaults) and record in compiler.interfaces
            methods = {}
            for s in stmt.body.statements:
                if isinstance(s, Function):
                    if s.body is None:
                        # signature only
                        methods[s.name] = {'args': s.params, 'bytecode': None, 'consts': []}
                    else:
                        comp = Compiler()
                        for sub in s.body.statements:
                            comp.compile_stmt(sub)
                        comp.emit('RETURN_VALUE')
                        methods[s.name] = {'args': s.params, 'bytecode': comp.instructions, 'consts': comp.consts}
                else:
                    raise CompileError('Invalid member in interface')
            # merge base interfaces
            merged = {}
            for base_name in getattr(stmt, 'bases', []) or []:
                base_iface = self.interfaces.get(base_name)
                if base_iface is None:
                    raise CompileError(f"Interface base '{base_name}' not found for interface '{stmt.name}'")
                merged.update(base_iface.get('methods', {}))
            merged.update(methods)
            iface_obj = {'name': stmt.name, 'methods': merged, 'bases': getattr(stmt, 'bases', []) or []}
            self.interfaces[stmt.name] = iface_obj
        elif isinstance(stmt, UnionDeclaration):
            # compile union as a type descriptor constant
            variants = []
            for v in stmt.variants:
                variants.append({'name': v.name, 'fields': v.fields})
            union_obj = {'name': stmt.name, 'variants': variants, '__type__': 'union'}
            idx = self.add_const(union_obj)
            self.emit('LOAD_CONST', idx)
            self.emit('STORE_NAME', stmt.name)
        elif isinstance(stmt, InterfaceDeclaration):
            # interfaces are a compile-time construct; ignore at bytecode level
            return
        elif isinstance(stmt, BlockStatement):
            for s in stmt.statements:
                self.compile_stmt(s)
        elif isinstance(stmt, TryStatement):
            setup_pos = len(self.instructions)
            self.emit('SETUP_EXCEPT', None)
            for s in stmt.body.statements:
                self.compile_stmt(s)
            self.emit('POP_EXCEPT')
            self.emit('JUMP', None)
            jump_pos = len(self.instructions) - 1
            handler_start = len(self.instructions)
            self.instructions[setup_pos] = ('SETUP_EXCEPT', handler_start)
            self.emit('STORE_NAME', stmt.exception_name)
            for s in stmt.handler.statements:
                self.compile_stmt(s)
            end = len(self.instructions)
            self.instructions[jump_pos] = ('JUMP', end)
        elif isinstance(stmt, ThrowStatement):
            self.compile_expr(stmt.expr)
            self.emit('RAISE')
        elif isinstance(stmt, AssignmentIndex):
            # arr[index] = value
            self.compile_expr(stmt.array)
            self.compile_expr(stmt.index)
            self.compile_expr(stmt.value)
            self.emit('SET_ITEM')
        elif isinstance(stmt, AssignmentMember):
            # obj.attr = value
            self.compile_expr(stmt.left)
            self.compile_expr(stmt.value)
            self.emit('STORE_ATTR', stmt.name)
        elif isinstance(stmt, AssignmentIdentifier):
            self.compile_expr(stmt.value)
            self.emit_store_name(stmt.name)
        elif isinstance(stmt, ForStatement):
            iter_idx = self.add_const(('__ITER__', stmt.var1, stmt.var2))
            self.compile_expr(stmt.iterable)
            self.emit('LOAD_CONST', iter_idx)
            self.emit('FOR_ITER', None)
            for_start = len(self.instructions)

            old_breaks = self.pending_breaks
            old_continues = self.pending_continues
            self.pending_breaks = []
            self.pending_continues = [for_start]

            for s in stmt.body.statements:
                self.compile_stmt(s)
            self.emit('JUMP', for_start)
            for_end = len(self.instructions)
            self.instructions[for_start - 1] = ('FOR_ITER', for_end)

            self._backpatch_breaks(for_end, old_breaks, old_continues)
        elif isinstance(stmt, ModuleDeclaration):
            for s in stmt.body.statements:
                self.compile_stmt(s)
            mod_idx = self.add_const(stmt.name)
            self.emit('MAKE_MODULE', mod_idx)
        elif isinstance(stmt, ConceptDeclaration):
            idx = self.add_const(('concept', stmt.name))
            self.emit('LOAD_CONST', idx)
            self.emit('STORE_NAME', stmt.name)
        elif isinstance(stmt, AsmBlock):
            idx = self.add_const(('asm', stmt.code))
            self.emit('LOAD_CONST', idx)
            self.emit('ASM')
        elif isinstance(stmt, D3SizePowerDeclaration):
            props = []
            for p in stmt.properties:
                if isinstance(p.params, D3CoordinateExpr):
                    props.append((p.name, p.params.params, p.is_public))
                else:
                    props.append((p.name, p.params, p.is_public))
            idx = self.add_const(('3dsizepower', stmt.name, props))
            self.emit('LOAD_CONST', idx)
            self.emit('STORE_NAME', stmt.name)
        elif isinstance(stmt, D3Em3dDeclaration):
            props = []
            for p in stmt.properties:
                if isinstance(p.params, D3CoordinateExpr):
                    props.append((p.name, p.params.params, p.is_public))
                else:
                    props.append((p.name, p.params, p.is_public))
            parent = stmt.parent_d3
            idx = self.add_const(('em3d', stmt.name, parent, props))
            self.emit('LOAD_CONST', idx)
            self.emit('STORE_NAME', stmt.name)
        elif isinstance(stmt, CoroFunction):
            comp = Compiler()
            for s in stmt.body.statements:
                comp.compile_stmt(s)
            comp.emit('RETURN_VALUE')
            func_obj = {'args': stmt.params, 'bytecode': comp.instructions, 'consts': comp.consts, 'is_coro': True}
            idx = self.add_const(func_obj)
            self.emit('LOAD_CONST', idx)
            self.emit('STORE_NAME', stmt.name)
        elif isinstance(stmt, ContinueStatement):
            if self.pending_continues:
                target = self.pending_continues[-1]
                self.emit('JUMP', target)
            else:
                self.emit('CONTINUE', None)
        elif isinstance(stmt, BreakStatement):
            self.pending_breaks.append(len(self.instructions))
            self.emit('BREAK', None)
        else:
            # expression statements
            self.compile_expr(stmt)
            self.emit('POP_TOP')

    def compile_expr(self, expr):
        if isinstance(expr, NumberLiteral):
            idx = self.add_const(expr.value)
            self.emit('LOAD_CONST', idx)
        elif isinstance(expr, StringLiteral):
            idx = self.add_const(expr.value)
            self.emit('LOAD_CONST', idx)
        elif isinstance(expr, BooleanLiteral):
            idx = self.add_const(expr.value)
            self.emit('LOAD_CONST', idx)
        elif isinstance(expr, Identifier):
            self.emit_load_name(expr.name)
        elif isinstance(expr, NullLiteral):
            idx = self.add_const(None)
            self.emit('LOAD_CONST', idx)
        elif isinstance(expr, Lambda):
            # compile lambda into a closure (function + captured free vars)
            freevars = self._find_free_vars_in_stmt(expr.body, set(expr.params))
            comp = Compiler()
            comp.bound = set(expr.params)
            comp.deref_names = set(freevars)
            for s in expr.body.statements:
                comp.compile_stmt(s)
            comp.emit('RETURN_VALUE')
            func_obj = {
                'args': expr.params,
                'bytecode': comp.instructions,
                'consts': comp.consts,
                'freevars': list(freevars),
            }
            idx = self.add_const(func_obj)
            for fv in freevars:
                self.emit_load_name(fv)
            self.emit('LOAD_CONST', idx)
            if freevars:
                self.emit('MAKE_CLOSURE', len(freevars))
        elif isinstance(expr, ArrayLiteral):
            for e in expr.elements:
                self.compile_expr(e)
            self.emit('MAKE_LIST', len(expr.elements))
        elif isinstance(expr, DictLiteral):
            for k, v in expr.pairs:
                self.compile_expr(k)
                self.compile_expr(v)
            self.emit('MAKE_DICT', len(expr.pairs))
        elif isinstance(expr, IndexExpression):
            from h_ast import SliceExpression
            if isinstance(expr.index, SliceExpression):
                # compile as a single SLICE opcode:
                #   push collection, start, end, step
                #   SLICE
                self.compile_expr(expr.left)
                if expr.index.start is not None:
                    self.compile_expr(expr.index.start)
                else:
                    self.emit('LOAD_CONST', self.add_const(None))
                if expr.index.end is not None:
                    self.compile_expr(expr.index.end)
                else:
                    self.emit('LOAD_CONST', self.add_const(None))
                if expr.index.step is not None:
                    self.compile_expr(expr.index.step)
                else:
                    self.emit('LOAD_CONST', self.add_const(None))
                self.emit('SLICE')
            else:
                self.compile_expr(expr.left)
                self.compile_expr(expr.index)
                self.emit('GET_ITEM')
        elif isinstance(expr, MemberExpression):
            # push attribute value: compile left (instance) then load attribute
            self.compile_expr(expr.left)
            self.emit('LOAD_ATTR', expr.name)
        elif isinstance(expr, BinaryOp):
            op = expr.op
            if op in (TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.MOD,
                      TokenType.EQEQ, TokenType.BANGEQ, TokenType.GT, TokenType.LT, TokenType.GTE, TokenType.LTE,
                      TokenType.BITAND, TokenType.BITOR, TokenType.BITXOR, TokenType.LSHIFT, TokenType.RSHIFT):
                # simple binary ops: compile left then right
                self.compile_expr(expr.left)
                self.compile_expr(expr.right)
                if op == TokenType.PLUS:
                    self.emit('BINARY_ADD')
                elif op == TokenType.MINUS:
                    self.emit('BINARY_SUB')
                elif op == TokenType.STAR:
                    self.emit('BINARY_MUL')
                elif op == TokenType.SLASH:
                    self.emit('BINARY_DIV')
                elif op == TokenType.MOD:
                    self.emit('BINARY_MOD')
                elif op == TokenType.BITAND:
                    self.emit('BINARY_BITAND')
                elif op == TokenType.BITOR:
                    self.emit('BINARY_BITOR')
                elif op == TokenType.BITXOR:
                    self.emit('BINARY_BITXOR')
                elif op == TokenType.LSHIFT:
                    self.emit('BINARY_LSHIFT')
                elif op == TokenType.RSHIFT:
                    self.emit('BINARY_RSHIFT')
                else:
                    # comparison
                    self.emit('COMPARE_OP', op.value)
            elif op == TokenType.AND:
                # short-circuit: if left is false -> push False; else evaluate right
                self.compile_expr(expr.left)
                # placeholder
                self.emit('JUMP_IF_FALSE', None)
                jmp_false_pos = len(self.instructions)-1
                # evaluate right (if left true)
                self.compile_expr(expr.right)
                # after right, skip false-constant
                self.emit('JUMP', None)
                jmp_end_pos = len(self.instructions)-1
                false_pos = len(self.instructions)
                idx_false = self.add_const(False)
                self.emit('LOAD_CONST', idx_false)
                end_pos = len(self.instructions)
                self.instructions[jmp_false_pos] = ('JUMP_IF_FALSE', false_pos)
                self.instructions[jmp_end_pos] = ('JUMP', end_pos)
            elif op == TokenType.OR:
                # short-circuit: if left is true -> push True; else evaluate right
                self.compile_expr(expr.left)
                # if left is false, jump to eval right
                self.emit('JUMP_IF_FALSE', None)
                jmp_eval_right = len(self.instructions)-1
                # left was true (did not jump): push True and skip right
                idx_true = self.add_const(True)
                self.emit('LOAD_CONST', idx_true)
                self.emit('JUMP', None)
                jmp_end = len(self.instructions)-1
                eval_right_pos = len(self.instructions)
                self.instructions[jmp_eval_right] = ('JUMP_IF_FALSE', eval_right_pos)
                # evaluate right
                self.compile_expr(expr.right)
                end_pos = len(self.instructions)
                self.instructions[jmp_end] = ('JUMP', end_pos)
            else:
                raise CompileError(f'Unsupported binary op: {op}')
        elif isinstance(expr, UnaryOp):
            if expr.op == TokenType.NOT:
                self.compile_expr(expr.operand)
                self.emit('UNARY_NOT')
            elif expr.op == TokenType.TILDE:
                self.compile_expr(expr.operand)
                self.emit('UNARY_TILDE')
            else:
                raise CompileError(f'Unsupported unary op: {expr.op}')
        elif isinstance(expr, TernaryOp):
            # condition ? true_expr : false_expr
            # compile condition, then JUMP_IF_FALSE to false_branch
            self.compile_expr(expr.condition)
            jmp_false_pos = len(self.instructions)
            self.emit('JUMP_IF_FALSE', None)  # placeholder
            # true branch
            self.compile_expr(expr.true_expr)
            jmp_end_pos = len(self.instructions)
            self.emit('JUMP', None)  # skip false branch
            # false branch
            false_start = len(self.instructions)
            self.compile_expr(expr.false_expr)
            end_pos = len(self.instructions)
            # backpatch
            self.instructions[jmp_false_pos] = ('JUMP_IF_FALSE', false_start)
            self.instructions[jmp_end_pos] = ('JUMP', end_pos)
        elif isinstance(expr, QuaternaryOp):
            # cond1 ?^ expr1 : cond2 : expr2
            # compile cond1, then JUMP_IF_FALSE to cond2 check
            self.compile_expr(expr.cond1)
            jmp_to_cond2_pos = len(self.instructions)
            self.emit('JUMP_IF_FALSE', None)  # placeholder
            # expr1 (cond1 was true)
            self.compile_expr(expr.expr1)
            jmp_end_pos = len(self.instructions)
            self.emit('JUMP', None)  # skip rest
            # cond2 check
            cond2_start = len(self.instructions)
            self.compile_expr(expr.cond2)
            jmp_to_false_pos = len(self.instructions)
            self.emit('JUMP_IF_FALSE', None)  # placeholder
            # expr2 (cond2 was true)
            self.compile_expr(expr.expr2)
            jmp_end2_pos = len(self.instructions)
            self.emit('JUMP', None)  # skip false push
            # both false: push nullptr
            false_start = len(self.instructions)
            null_idx = self.add_const(None)
            self.emit('LOAD_CONST', null_idx)
            end_pos = len(self.instructions)
            # backpatch
            self.instructions[jmp_to_cond2_pos] = ('JUMP_IF_FALSE', cond2_start)
            self.instructions[jmp_end_pos] = ('JUMP', end_pos)
            self.instructions[jmp_to_false_pos] = ('JUMP_IF_FALSE', false_start)
            self.instructions[jmp_end2_pos] = ('JUMP', end_pos)
        elif isinstance(expr, CallExpression):
            # support calls like func(...), or obj.method(...)
            # func can be Identifier or MemberExpression
            if isinstance(expr.func, Identifier):
                # If the callee is a free variable (captured from an enclosing
                # scope), the env holds a closure cell (HList), not the raw
                # function.  Emit LOAD_DEREF + CALL_VALUE so we unwrap the cell
                # first; otherwise emit the cheap CALL_FUNCTION which does
                # env+builtin lookup by name.
                #
                # IMPORTANT: push the function (or its cell) BEFORE the args,
                # so that the VM's `callValue` (which pops the function first
                # via `removeLast`, then the args via `popArgs`) sees the
                # correct stack layout: [arg1, arg2, ..., argN, function].
                if expr.func.name in self.deref_names:
                    self.emit('LOAD_DEREF', expr.func.name)
                    for arg in expr.args:
                        self.compile_expr(arg)
                    self.emit('CALL_VALUE', len(expr.args))
                else:
                    for arg in expr.args:
                        self.compile_expr(arg)
                    self.emit('CALL_FUNCTION', (expr.func.name, len(expr.args)))
            elif isinstance(expr.func, MemberExpression):
                # for method call, compile left (instance), then args, then CALL_METHOD
                self.compile_expr(expr.func.left)
                for arg in expr.args:
                    self.compile_expr(arg)
                self.emit('CALL_METHOD', (expr.func.name, len(expr.args)))
            else:
                # general callable expression: compile the function expression
                self.compile_expr(expr.func)
                for arg in expr.args:
                    self.compile_expr(arg)
                self.emit('CALL_VALUE', len(expr.args))
        elif isinstance(expr, NewExpression):
            # compile class expression (usually Identifier)
            # emit LOAD_NAME for class then args then CALL_NEW
            if isinstance(expr.class_name, Identifier):
                self.emit('LOAD_NAME', expr.class_name.name)
            else:
                self.compile_expr(expr.class_name)
            for arg in expr.args:
                self.compile_expr(arg)
            self.emit('CALL_NEW', len(expr.args))
        elif isinstance(expr, UnionConstructExpression):
            # compile union construction: TypeName{Variant: values}
            if isinstance(expr.type_name, Identifier):
                self.emit('LOAD_NAME', expr.type_name.name)
            else:
                self.compile_expr(expr.type_name)
            self.emit('LOAD_CONST', self.add_const(expr.variant_name))
            for val in expr.values:
                self.compile_expr(val)
            self.emit('UNION_MAKE', len(expr.values))
        elif isinstance(expr, SuperExpression):
            # super.method(args) - compile as special call
            # Need special opcode for super calls
            for arg in expr.args:
                self.compile_expr(arg)
            self.emit('CALL_SUPER', (expr.method_name, len(expr.args)))
        elif isinstance(expr, InstanceOfExpression):
            # expr is TypeName
            self.compile_expr(expr.expr)
            self.emit('INSTANCEOF', expr.type_name)
        elif isinstance(expr, PointerDereference):
            self.compile_expr(expr.target)
            self.emit('DEREF')
        elif isinstance(expr, CastExpression):
            self.compile_expr(expr.expr)
            self.emit('CAST', expr.type_name)
        else:
            raise CompileError(f'Unsupported expression type: {type(expr)}')