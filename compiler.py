from h_ast import *
from tokens import TokenType

# Token types for operators that might not be in TokenType yet
_MODULO = getattr(TokenType, '_MOD', getattr(TokenType, 'MODULO', '%'))

class CompileError(Exception):
    pass

# NOTE: SuperExpression and InstanceOfExpression are imported from h_ast
# via `from h_ast import *`.  Do NOT redefine them here — a local class
# would shadow the imported one and `isinstance(expr, SuperExpression)`
# would never match parser-produced nodes (class identity mismatch).

class Compiler:
    _destructure_counter = 0

    def __init__(self, use_hcompiler=False):
        self.use_hcompiler = use_hcompiler
        self.consts = []
        self.instructions = []
        self._labels = []
        self.interfaces = {}
        self.pending_breaks = []
        self.pending_continues = []
        # Track active try-blocks for break/continue cleanup.  Each
        # entry is the loop_depth at which the try was entered; when a
        # break/continue crosses a try boundary we must emit POP_EXCEPT
        # so the exception handler stack does not leak.
        self.try_stack = []
        self.loop_depth = 0

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

    def _unique_destructure_temp(self):
        """Generate a fresh, collision-resistant name for the synthetic
        variable that holds the RHS of a destructuring `let`."""
        # Use a module-level counter so two destructures in the same
        # scope don't share the same temp.
        n = Compiler._destructure_counter
        Compiler._destructure_counter += 1
        return f"__destr_{n}__"

    def compile(self, program):
        # program: Program AST
        for stmt in program.statements:
            self.compile_stmt(stmt)
        self.emit('HALT')
        return {'instructions': self.instructions, 'consts': self.consts}

    def _find_free_vars_in_stmt(self, node, bound):
        free = set()
        from h_ast import Identifier, LetStatement, Function, Lambda, BlockStatement, CallExpression, MemberExpression, DestructureLet
        def visit(n, local_bound):
            if isinstance(n, Identifier):
                if n.name not in local_bound:
                    free.add(n.name)
            elif isinstance(n, LetStatement):
                visit(n.value, local_bound)
                local_bound = set(local_bound)
                local_bound.add(n.name)
            elif isinstance(n, DestructureLet):
                visit(n.value, local_bound)
                local_bound = set(local_bound)
                for nm in n.names:
                    if nm is not None:
                        local_bound.add(nm)
            elif isinstance(n, Function):
                # Recurse into the function body so free variables used
                # directly inside it (but defined in an enclosing scope)
                # are captured.  Nested Function/Lambda nodes are NOT
                # recursed into (their own free vars belong to them).
                b = set(local_bound) | set(n.params)
                for s in n.body.statements:
                    visit(s, b)
            elif isinstance(n, Lambda):
                b = set(local_bound)|set(n.params)
                for s in n.body.statements:
                    visit(s, b)
            elif isinstance(n, BlockStatement):
                for s in n.statements:
                    visit(s, local_bound)
            elif isinstance(n, CallExpression):
                visit(n.func, local_bound)
                for a in n.args:
                    visit(a, local_bound)
            elif isinstance(n, MemberExpression):
                visit(n.left, local_bound)
            elif isinstance(n, AST):
                for attr, v in vars(n).items():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, AST):
                                visit(item, local_bound)
                    elif isinstance(v, AST):
                        visit(v, local_bound)
        visit(node, set(bound))
        return list(free)

    def compile_stmt(self, stmt):
        from h_ast import ClassDeclaration, AssignmentMember, MemberExpression, NewExpression, UnionDeclaration, UnionConstructExpression, DestructureLet
        if isinstance(stmt, LetStatement):
            self.compile_expr(stmt.value)
            self.emit('STORE_NAME', stmt.name)
        elif isinstance(stmt, DestructureLet):
            # `let [a, b, c] = expr;`
            # Evaluate RHS once into a synthetic temp, then index it
            # for each slot.  Using a temp (rather than DUP_TOP) keeps
            # us independent of stack-manipulation opcodes.
            self.compile_expr(stmt.value)
            tmp = self._unique_destructure_temp()
            self.emit('STORE_NAME', tmp)
            for i, name in enumerate(stmt.names):
                if name is None:
                    continue
                self.emit('LOAD_NAME', tmp)
                self.emit('LOAD_CONST', self.add_const(i))
                self.emit('GET_ITEM')
                self.emit('STORE_NAME', name)
            # Drop the temp so it doesn't leak into the user's namespace
            # visibly (it remains in `bound` but that's fine — the name
            # is mangled enough not to collide with user code).
        elif isinstance(stmt, PrintStatement):
            self.compile_expr(stmt.expr)
            self.emit('PRINT')
        elif isinstance(stmt, Function):
            # compile function body into its own bytecode object
            comp = Compiler()
            for s in stmt.body.statements:
                comp.compile_stmt(s)
            comp.emit('RETURN_VALUE')
            func_obj = {'args': stmt.params, 'bytecode': comp.instructions, 'consts': comp.consts}
            # Default values for trailing parameters (literal-only).
            if getattr(stmt, 'defaults', None):
                defaults_json = []
                for d in stmt.defaults:
                    if isinstance(d, BooleanLiteral):
                        defaults_json.append(bool(d.value))
                    elif isinstance(d, NumberLiteral):
                        defaults_json.append(d.value)
                    elif isinstance(d, StringLiteral):
                        defaults_json.append(d.value)
                    elif isinstance(d, NullLiteral):
                        defaults_json.append(None)
                    else:
                        raise Exception(
                            f"Default argument for '{stmt.name}' must be a "
                            f"literal (number/string/bool/null); got "
                            f"{type(d).__name__}")
                func_obj['defaults'] = defaults_json
            if getattr(stmt, 'is_variadic', False):
                func_obj['is_variadic'] = True
            # Capture free variables so nested functions close over the
            # lexical environment in which they are *defined* (not called).
            freevars = self._find_free_vars_in_stmt(stmt, stmt.params)
            if freevars:
                func_obj['freevars'] = freevars
            idx = self.add_const(func_obj)
            self.emit('MAKE_CLOSURE', idx)
            self.emit('STORE_NAME', stmt.name)
        elif isinstance(stmt, ReturnStatement):
            self.compile_expr(stmt.expr)
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
            self.loop_depth += 1

            for s in stmt.body.statements:
                self.compile_stmt(s)
            self.emit('JUMP', start)
            end = len(self.instructions)
            self.instructions[jmp_false_pos] = ('JUMP_IF_FALSE', end)

            self.loop_depth -= 1
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
                    func_obj = {'args': s.params, 'bytecode': comp.instructions, 'consts': comp.consts, 'name': s.name}
                    # Default values for trailing parameters (literal-only).
                    if getattr(s, 'defaults', None):
                        defaults_json = []
                        for d in s.defaults:
                            if isinstance(d, BooleanLiteral):
                                defaults_json.append(bool(d.value))
                            elif isinstance(d, NumberLiteral):
                                defaults_json.append(d.value)
                            elif isinstance(d, StringLiteral):
                                defaults_json.append(d.value)
                            elif isinstance(d, NullLiteral):
                                defaults_json.append(None)
                            else:
                                raise Exception(
                                    f"Default argument for '{s.name}' must be a "
                                    f"literal (number/string/bool/null); got "
                                    f"{type(d).__name__}")
                        func_obj['defaults'] = defaults_json
                    if getattr(s, 'is_variadic', False):
                        func_obj['is_variadic'] = True
                    if getattr(s, 'is_static', False):
                        # store static methods as top-level attributes on the class object
                        # they will be callable via ClassName.method(...)
                        methods.setdefault('__static__', {})[s.name] = func_obj
                    else:
                        # Store methods under their declared name.  The VM's
                        # CALL_NEW looks up the constructor under both
                        # `__init__` and `init` (see HVM.callNew and
                        # bytecode.py CALL_NEW), so both `fn init(...)`
                        # and `fn __init__(...)` work as constructors, and
                        # explicit `p.init(3, 4)` calls still resolve.
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
            # Record the loop depth at which this try was entered so
            # that break/continue emitted inside the body can decide
            # whether they cross the try boundary and need a POP_EXCEPT.
            self.try_stack.append(self.loop_depth)
            for s in stmt.body.statements:
                self.compile_stmt(s)
            self.emit('POP_EXCEPT')
            self.try_stack.pop()
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
            self.emit('STORE_NAME', stmt.name)
        elif isinstance(stmt, ForStatement):
            iter_idx = self.add_const(('__ITER__', stmt.var1, stmt.var2))
            self.compile_expr(stmt.iterable)
            self.emit('LOAD_CONST', iter_idx)
            self.emit('FOR_ITER', None)
            # for_start points AT the FOR_ITER instruction so that the
            # loop-back JUMP and `continue` re-enter through FOR_ITER
            # (which advances the iterator / tests for exhaustion).
            # Previously this pointed one past FOR_ITER, skipping the
            # advance and producing an infinite loop on the first
            # element; the Kotlin HbcReader worked around this with
            # fixForLoopJumps, but the Python VM had no such fix.
            for_start = len(self.instructions) - 1

            old_breaks = self.pending_breaks
            old_continues = self.pending_continues
            self.pending_breaks = []
            self.pending_continues = [for_start]
            self.loop_depth += 1

            for s in stmt.body.statements:
                self.compile_stmt(s)
            self.emit('JUMP', for_start)
            for_end = len(self.instructions)
            self.instructions[for_start] = ('FOR_ITER', for_end)

            self.loop_depth -= 1
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
            # If we're inside a try block that was entered within the
            # current loop, jumping back to the loop header crosses the
            # try boundary — emit POP_EXCEPT for each such active try so
            # the runtime exception-handler stack does not leak.
            for d in self.try_stack:
                if d == self.loop_depth:
                    self.emit('POP_EXCEPT')
            if self.pending_continues:
                target = self.pending_continues[-1]
                self.emit('JUMP', target)
            else:
                self.emit('CONTINUE', None)
        elif isinstance(stmt, BreakStatement):
            for d in self.try_stack:
                if d == self.loop_depth:
                    self.emit('POP_EXCEPT')
            self.pending_breaks.append(len(self.instructions))
            self.emit('BREAK', None)
        elif isinstance(stmt, DeleteStatement):
            # `del x` / `del obj.attr` / `del arr[i]` — the VM has no
            # dedicated DELETE opcode, so lower `del` to a null store:
            #   del x     ->  x = null
            #   del o.a   ->  o.a = null
            #   del a[i]  ->  a[i] = null
            target = stmt.target
            if isinstance(target, Identifier):
                self.emit('LOAD_CONST', self.add_const(None))
                self.emit('STORE_NAME', target.name)
            elif isinstance(target, MemberExpression):
                self.compile_expr(target.left)
                self.emit('LOAD_CONST', self.add_const(None))
                self.emit('STORE_ATTR', target.name)
            elif isinstance(target, IndexExpression):
                # `del a[i]` — emit DELETE_ITEM, which the Kotlin HVM
                # dispatches by runtime type: for lists it removes by
                # INDEX (with negative-index support, out-of-range
                # raises); for dicts it removes by KEY.  Stack layout
                # is [..., target, idx], which is exactly what the two
                # compile_expr calls below produce.  This replaces the
                # old `a.remove(i)` lowering which was wrong for lists
                # (remove(x) deletes the first element with VALUE x,
                # not at INDEX x).
                # NOTE: the Python VM in bytecode.py does not yet
                # implement DELETE_ITEM; `del a[i]` run there will
                # raise "Unknown opcode: DELETE_ITEM".  Add DELETE_ITEM
                # support to bytecode.py separately if Python-VM
                # testing of `del` is needed.
                self.compile_expr(target.left)
                self.compile_expr(target.index)
                self.emit('DELETE_ITEM', None)
            else:
                raise CompileError(
                    f"del target must be identifier, member, or index; "
                    f"got {type(target).__name__}")
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
            self.emit('LOAD_NAME', expr.name)
        elif isinstance(expr, NullLiteral):
            idx = self.add_const(None)
            self.emit('LOAD_CONST', idx)
        elif isinstance(expr, Lambda):
            # compile lambda into a function constant (no capture support in this MVP)
            comp = Compiler()
            for s in expr.body.statements:
                comp.compile_stmt(s)
            comp.emit('RETURN_VALUE')
            # capture free vars from current compilation scope
            freevars = self._find_free_vars_in_stmt(expr, expr.params)
            func_obj = {'args': expr.params, 'bytecode': comp.instructions, 'consts': comp.consts, 'freevars': freevars}
            # Default values for trailing parameters (literal-only),
            # mirroring the Function-statement handling above.
            if getattr(expr, 'defaults', None):
                defaults_json = []
                for d in expr.defaults:
                    if isinstance(d, BooleanLiteral):
                        defaults_json.append(bool(d.value))
                    elif isinstance(d, NumberLiteral):
                        defaults_json.append(d.value)
                    elif isinstance(d, StringLiteral):
                        defaults_json.append(d.value)
                    elif isinstance(d, NullLiteral):
                        defaults_json.append(None)
                    else:
                        raise Exception(
                            f"Default argument for lambda must be a "
                            f"literal (number/string/bool/null); got "
                            f"{type(d).__name__}")
                func_obj['defaults'] = defaults_json
            if getattr(expr, 'is_variadic', False):
                func_obj['is_variadic'] = True
            idx = self.add_const(func_obj)
            self.emit('MAKE_CLOSURE', idx)
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
                      TokenType.BITAND, TokenType.BITOR, TokenType.BITXOR, TokenType.LSHIFT, TokenType.RSHIFT,
                      TokenType.IN):
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