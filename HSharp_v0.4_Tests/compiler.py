from h_ast import *
from tokens import TokenType

# Token types for operators that might not be in TokenType yet
_MODULO = getattr(TokenType, '_MOD', getattr(TokenType, 'MODULO', '%'))

def _bool_aware_eq(a, b):
    """Equality that does NOT conflate `True` with `1` and `False` with `0`.

    Python's built-in `==` treats bool as a subclass of int, so
    `True == 1` is `True`.  For H# match patterns (and the const-pool
    dedup) this is wrong: a literal-`true` arm must be a different
    const from a literal-`1` arm, and likewise for `false`/`0`.  This
    helper compares types and identity first, then falls back to
    recursive comparison with a special case for `bool`."""
    if a is b:
        return True
    if type(a) is not type(b):
        # Differ in Python type — bool and int must be distinguished.
        return False
    if isinstance(a, bool) and isinstance(b, bool):
        return a is b  # only `True is True` and `False is False`
    if isinstance(a, dict) and isinstance(b, dict):
        if len(a) != len(b):
            return False
        return all(k in b and _bool_aware_eq(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(
            _bool_aware_eq(x, y) for x, y in zip(a, b))
    return a == b

class CompileError(Exception):
    pass

# NOTE: SuperExpression and InstanceOfExpression are imported from h_ast
# via `from h_ast import *`.  Do NOT redefine them here — a local class
# would shadow the imported one and `isinstance(expr, SuperExpression)`
# would never match parser-produced nodes (class identity mismatch).

class Compiler:
    _destructure_counter = 0

    def _backpatch_breaks(self, target, old_breaks, old_continues):
        for pos in self.pending_breaks:
            self.instructions[pos] = ('JUMP', target)
        self.pending_breaks = old_breaks
        self.pending_continues = old_continues

    def add_const(self, value):
        # Dedup primitive values by identity (for bool) and equality.
        # Plain `==` would conflate `True` and `1` (Python bool is an
        # int subclass) — a serious problem for match patterns, where
        # the literal `true` must be a separate const from the literal
        # `1`.  We therefore use `_bool_aware_eq` for all value-vs-
        # const-pool comparisons so bool stays distinct from int.
        for i, v in enumerate(self.consts):
            if _bool_aware_eq(value, v):
                return i
        idx = len(self.consts)
        self.consts.append(value)
        return idx

    def _pattern_to_const(self, pat):
        """Convert a MatchPattern AST node into a dict suitable for
        placing in the const pool.  The dict shape is the contract
        the Kotlin VM uses to interpret a `MATCH_CASE` pattern:
          {"kind": "wildcard"}
          {"kind": "binding", "name": <str>}
          {"kind": "literal", "literal": <H# literal>}
          {"kind": "type", "type_name": <str>, "binding": <str|None>}
          {"kind": "variant", "variant": <str>, "names": [<str>, ...]}
          {"kind": "chan_send"}
          {"kind": "chan_recv"}
          {"kind": "chan_close"}
        """
        d = {"kind": pat.kind}
        if pat.kind == "binding":
            name = pat.bindings[0][0] if pat.bindings else "_"
            d["name"] = name
        elif pat.kind == "literal":
            d["literal"] = pat.literal
        elif pat.kind == "type":
            d["type_name"] = pat.type_name
            d["binding"] = pat.bindings[0][0] if pat.bindings else None
        elif pat.kind == "variant":
            d["variant"] = pat.variant_name
            d["names"] = [b[0] for b in (pat.bindings or [])]
        elif pat.kind in ("chan_send", "chan_recv", "chan_close"):
            # The binding name (e.g. `chan send(v)` -> name="v") is
            # carried as the first binding slot when present.
            if pat.bindings:
                d["name"] = pat.bindings[0][0]
        return d

    def emit(self, opname, arg=None):
        self.instructions.append((opname, arg))

    def _unique_destructure_temp(self):
        """Generate a fresh, collision-resistant name for the synthetic
        variable that holds the RHS of a destructuring `let`."""
        n = Compiler._destructure_counter
        Compiler._destructure_counter += 1
        return f"__destr_{n}__"

    def _emit_type_args_list(self, type_args):
        """Emit a `MAKE_LIST` of the given type-argument name strings
        followed by pushing the resulting list on the stack.  Used as a
        prelude to the *_T call opcodes so the runtime can attach the
        type arguments to the call frame / instance for introspection."""
        idx = self.add_const(list(type_args))
        # Use the same const pool encoding as ordinary H# list literals
        # (a Python list) so the JSON-side reader sees a normal list.
        # The runtime's HList constructor handles it.
        self.emit('LOAD_CONST', idx)

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
                           SuperExpression, SliceExpression, AST,
                           DestructureLet, MatchExpression)

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
            if isinstance(n, DestructureLet):
                visit(n.value, b, free)
                b = set(b)
                for nm in n.names:
                    if nm is not None:
                        b.add(nm)
                return b
            if isinstance(n, Function):
                # The function binds its name in the enclosing scope.
                # Like Lambda, we recurse into the body to find the
                # inner function's own free variables, then promote
                # the ones that aren't bound in the current scope to
                # the current function's free variables.  This is
                # essential for deep nesting: `fn a(x) { fn b(y) {
                # fn c(z) { return x + y + z; } } }` — without
                # recursing, `b` would not know it needs to capture
                # `x` for `c`, and `c` would fail to find `x`.
                # Names already bound in the current scope (params,
                # lets) are filtered by the promotion check `fv not
                # in b`, so they are NOT wrongly reported.
                local_free = set()
                inner_b = set(n.params) | {n.name}
                for s in n.body.statements:
                    inner_b = visit(s, inner_b, local_free)
                for fv in local_free:
                    if fv not in b:
                        free.add(fv)
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
            if isinstance(n, MatchExpression):
                # Walk the scrutinee with the current bound set, then
                # walk each case's guard and body with the pattern's
                # binding names added to the bound set.  Without this,
                # a binding pattern like `v if v > 0 => ...` inside a
                # lambda would wrongly treat `v` as a free variable of
                # the enclosing function, causing "Undefined name" at
                # runtime when the lambda tries to capture `v`.
                visit(n.scrutinee, b, free)
                for case in n.cases:
                    case_b = set(b)
                    if hasattr(case.pattern, 'bindings') and case.pattern.bindings:
                        for binding in case.pattern.bindings:
                            if binding and binding[0] and binding[0] != "_":
                                case_b.add(binding[0])
                    if case.guard is not None:
                        visit(case.guard, case_b, free)
                    visit(case.body, case_b, free)
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
        # Track active try-blocks for break/continue cleanup.  Each
        # entry is the loop_depth at which the try was entered; when a
        # break/continue crosses a try boundary we must emit POP_EXCEPT
        # so the exception handler stack does not leak.
        self.try_stack = []
        self.loop_depth = 0
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
        # True when compiling a function body (vs. the module top level).
        # Used to decide whether a name referenced inside a function but
        # not bound in the function should be treated as a free variable
        # (CALL_VALUE / LOAD_DEREF) or just looked up by name at call time
        # (CALL_FUNCTION).  For top-level functions, every reference other
        # than the function's own params/name is a module-level name
        # (either a user-defined let/fn at the module scope, or a runtime
        # HNative builtin) and should be looked up by name.
        self.in_function_body = False
        # True when compiling a body declared with `async fn`.  The
        # `await expr` static check requires this.  `coro fn` and plain
        # `fn` leave it False even though they share the same
        # `is_coro=True` runtime representation.
        self.in_async = False

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

    def _compile_lambda(self, expr, name=None):
        """Compile a Lambda expression into a closure (function +
        captured free vars), leaving the closure on the stack.

        If ``name`` is provided (e.g. for ``let f = fn(...){...}``),
        the name is added to the bound set and excluded from the
        lambda's freevars so the lambda can reference itself by name
        via LOAD_NAME at call time — mirroring how Function statements
        handle recursion.  Without this, ``let f = fn(n){...f(n-1)...}``
        would try to capture ``f`` as a freevar *before* ``f`` is
        stored, causing a runtime "Undefined name" error.
        """
        bound = set(expr.params)
        if name is not None:
            bound.add(name)
        freevars = self._find_free_vars_in_stmt(expr.body, bound)
        if name is not None:
            freevars = [fv for fv in freevars if fv != name]
        comp = Compiler()
        comp.bound = set(bound)
        comp.deref_names = set(freevars)
        comp.in_function_body = True
        for s in expr.body.statements:
            comp.compile_stmt(s)
        comp.emit('RETURN_VALUE')
        func_obj = {
            'args': expr.params,
            'bytecode': comp.instructions,
            'consts': comp.consts,
            'freevars': list(freevars),
        }
        # Default values for trailing parameters (literal-only),
        # mirroring the Function-statement handling.
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
                    raise CompileError(
                        f"Default argument for lambda must be a "
                        f"literal (number/string/bool/null); got "
                        f"{type(d).__name__}")
            func_obj['defaults'] = defaults_json
        if getattr(expr, 'is_variadic', False):
            func_obj['is_variadic'] = True
        idx = self.add_const(func_obj)
        for fv in freevars:
            self.emit_load_name(fv)
        self.emit('LOAD_CONST', idx)
        if freevars:
            self.emit('MAKE_CLOSURE', len(freevars))

    def compile_stmt(self, stmt):
        from h_ast import ClassDeclaration, AssignmentMember, MemberExpression, NewExpression, UnionDeclaration, UnionConstructExpression, DestructureLet, Lambda
        if isinstance(stmt, LetStatement):
            if isinstance(stmt.value, Lambda):
                # For ``let f = fn(...){...f...}``, exclude ``f`` from
                # the lambda's freevars so the lambda can reference
                # itself by name (LOAD_NAME) after it is stored —
                # mirroring how Function statements handle recursion.
                self._compile_lambda(stmt.value, stmt.name)
            else:
                self.compile_expr(stmt.value)
            self.emit_store_name(stmt.name)
            self.bound.add(stmt.name)
        elif isinstance(stmt, DestructureLet):
            # `let [a, b, c] = expr;` — evaluate RHS once into a
            # synthetic temp, then GET_ITEM for each slot.
            self.compile_expr(stmt.value)
            tmp = self._unique_destructure_temp()
            self.emit_store_name(tmp)
            self.bound.add(tmp)
            for i, name in enumerate(stmt.names):
                if name is None:
                    continue
                self.emit('LOAD_NAME', tmp)
                self.emit('LOAD_CONST', self.add_const(i))
                self.emit('GET_ITEM')
                self.emit_store_name(name)
                self.bound.add(name)
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
            #
            #    EXCEPTION: for top-level functions (the enclosing scope
            #    is the module), we skip the free-variable analysis
            #    entirely.  Module-level names (lets/functions defined
            #    in the module) and runtime HNative builtins must both
            #    be looked up by name at call time, NOT captured in
            #    closure cells.  Without this exception, every top-level
            #    function that calls a runtime builtin would falsely be
            #    treated as having that builtin as a free variable,
            #    which would force the runtime to read the wrong value
            #    out of a closure cell.
            if self.in_function_body:
                freevars = [
                    fv for fv in self._find_free_vars_in_stmt(
                        stmt.body, set(stmt.params) | {stmt.name}
                    ) if fv != stmt.name
                ]
            else:
                freevars = []
            # 2. Compile the body in a fresh compiler that knows which
            #    names are *free* in the enclosing function and must
            #    therefore go through the closure cell.
            comp = Compiler()
            comp.bound = set(stmt.params) | {stmt.name}
            comp.deref_names = set(freevars)
            comp.in_function_body = True
            # `async fn` requires the inner compiler to permit `await`.
            # `coro fn` and plain `fn` leave in_async False so any
            # accidental `await` inside them produces a static error.
            comp.in_async = bool(getattr(stmt, 'is_async', False))
            for s in stmt.body.statements:
                comp.compile_stmt(s)
            comp.emit('RETURN_VALUE')
            func_obj = {
                'args': stmt.params,
                'bytecode': comp.instructions,
                'consts': comp.consts,
                'freevars': list(freevars),
                'name': stmt.name,
            }
            # Generics: record the type-parameter list on the function
            # object so `fn<T>(x)` can be introspected at runtime.
            if stmt.type_params:
                func_obj['type_params'] = stmt.type_params
            # `async fn` is sugar over `coro fn`.  Both are represented
            # by the same `is_coro: True` runtime flag; the additional
            # `is_async: True` marker tells the HVM to wrap the call
            # result in an HFuture, so that `await` can be type-checked
            # against the Future<T> return type.
            if getattr(stmt, 'is_coro', False):
                func_obj['is_coro'] = True
            if getattr(stmt, 'is_async', False):
                func_obj['is_async'] = True
            # `parallel fn` (or `@parallel fn`) is the DZZW worker-pool
            # entry point.  It is also a coro (we run it as a separate
            # frame on a worker thread), but the additional `is_parallel:
            # True` marker tells the HVM to dispatch the call to a
            # worker via WorkerPool.submit() instead of running it
            # inline.  The result is an HFuture whose cell is left
            # PENDING until a worker completes the body.
            if getattr(stmt, 'is_parallel', False):
                func_obj['is_parallel'] = True
            if getattr(stmt, 'decorators', None):
                func_obj['decorators'] = list(stmt.decorators)
            # Default parameter values.  We currently only support
            # literal defaults (numbers, strings, bools, null) so the
            # runtime can store them as pre-evaluated HValues.  Non-
            # literal expressions are rejected with a clear error so
            # the user doesn't silently get the wrong value.
            if getattr(stmt, 'defaults', None):
                # Fold a literal default to a Python value.  Returns
                # (value, ok); ok is False for non-literal nodes.  The
                # parser lowers a leading unary minus (e.g. `x = -1`)
                # to `0 - <literal>`, so BinaryOp MINUS over numeric
                # literals is folded here to accept negative numbers.
                def _fold_default(node):
                    if isinstance(node, BooleanLiteral):
                        return bool(node.value), True
                    if isinstance(node, NumberLiteral):
                        return node.value, True
                    if isinstance(node, StringLiteral):
                        return node.value, True
                    if isinstance(node, NullLiteral):
                        return None, True
                    if isinstance(node, BinaryOp) and node.op == TokenType.MINUS:
                        l, lok = _fold_default(node.left)
                        r, rok = _fold_default(node.right)
                        if (lok and rok and isinstance(l, (int, float)) and not isinstance(l, bool)
                                and isinstance(r, (int, float)) and not isinstance(r, bool)):
                            return l - r, True
                    return None, False
                defaults_json = []
                for d in stmt.defaults:
                    # Emit raw JSON values — the HbcReader's parseValue
                    # handles primitives natively (Boolean/Number/String
                    # /null) so we don't need a tagged-union shape.
                    val, ok = _fold_default(d)
                    if not ok:
                        raise CompileError(
                            f"Default argument for '{stmt.name}' must be a "
                            f"literal (number/string/bool/null); got "
                            f"{type(d).__name__}")
                    defaults_json.append(val)
                func_obj['defaults'] = defaults_json
            if getattr(stmt, 'is_variadic', False):
                func_obj['is_variadic'] = True
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
                    # record type parameters on the method so generic
                    # methods of generic classes are still introspectable
                    if s.type_params:
                        func_obj['type_params'] = s.type_params
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
                        if isinstance(node, NullLiteral):
                            return None
                        if isinstance(node, ArrayLiteral):
                            return [eval_literal(e) for e in node.elements]
                        if isinstance(node, DictLiteral):
                            d = {}
                            for k, v in node.pairs:
                                kk = eval_literal(k)
                                vv = eval_literal(v)
                                d[kk] = vv
                            return d
                        # The parser lowers a leading unary minus (e.g.
                        # `-1`, `-3.14`) to `0 - <literal>`, so accept
                        # that BinaryOp form as a constant negative number.
                        if isinstance(node, BinaryOp) and node.op == TokenType.MINUS:
                            left = eval_literal(node.left)
                            right = eval_literal(node.right)
                            if (isinstance(left, (int, float)) and not isinstance(left, bool)
                                    and isinstance(right, (int, float)) and not isinstance(right, bool)):
                                return left - right
                            raise CompileError(
                                f"Field default must be a literal, got {type(node).__name__}")
                        raise CompileError(
                            f"Field default must be a literal, got {type(node).__name__}")
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
            # Generics: store the type-parameter list on the class object
            # so `new Foo<int>(...)` and `Foo.__type_params__[0]` work.
            if getattr(stmt, 'type_params', None):
                class_obj['type_params'] = stmt.type_params
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
            # Generics: store the interface's own type-parameter list.
            if getattr(stmt, 'type_params', None):
                iface_obj['type_params'] = stmt.type_params
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
        elif isinstance(stmt, ConcurrentBlock):
            # `concurrent { ... }` lowers to:
            #   CONCURRENT_ENTER
            #   SETUP_EXCEPT handler
            #   <body>
            #   POP_EXCEPT
            #   CONCURRENT_EXIT
            #   JUMP end
            # handler:
            #   CONCURRENT_EXIT   # always exit scope on exception
            #   RAISE             # then re-raise the original error
            # end:
            # The CONCURRENT_ENTER allocates a fresh ConcurrentScope
            # on the runtime's thread-local scope stack; every
            # @parallel call inside the body is registered as a
            # child of that scope.  CONCURRENT_EXIT joins on every
            # child (and re-throws the first failure) and pops the
            # scope off the stack.  Wrapping the body in
            # SETUP_EXCEPT/RAISE guarantees CONCURRENT_EXIT runs even
            # when the body raises, so the scope is always joined and
            # popped (no scope-stack leak / hung child tasks).  When an
            # exception is caught, dispatchException pushes the
            # exception value onto the stack; CONCURRENT_EXIT does not
            # touch the operand stack, so RAISE can pop and re-throw it.
            self.emit('CONCURRENT_ENTER')
            setup_pos = len(self.instructions)
            self.emit('SETUP_EXCEPT', None)
            for s in stmt.body.statements:
                self.compile_stmt(s)
            self.emit('POP_EXCEPT')
            self.emit('CONCURRENT_EXIT')
            self.emit('JUMP', None)
            jump_pos = len(self.instructions) - 1
            handler_start = len(self.instructions)
            self.instructions[setup_pos] = ('SETUP_EXCEPT', handler_start)
            self.emit('CONCURRENT_EXIT')
            self.emit('RAISE')
            end = len(self.instructions)
            self.instructions[jump_pos] = ('JUMP', end)
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
            if isinstance(stmt.index, SliceExpression):
                raise CompileError("slice assignment not yet supported")
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
            self.loop_depth += 1

            for s in stmt.body.statements:
                self.compile_stmt(s)
            self.emit('JUMP', for_start)
            # CLEANUP_FOR sits at the for-end position.  Two control
            # flows reach it:
            #   * `break` jumps here.  The iterator dict was pushed
            #     onto the stack by forIter and never popped, so
            #     CLEANUP_FOR pops it.
            #   * Normal end-of-iteration reaches it via FOR_ITER's
            #     jump-target field, but we point that field past
            #     CLEANUP_FOR (see for_end below) so the dict that
            #     forIter already popped is not popped again.
            self.emit('CLEANUP_FOR', None)
            for_end = len(self.instructions)         # position *after* CLEANUP_FOR
            self.instructions[for_start - 1] = ('FOR_ITER', for_end)

            self.loop_depth -= 1
            self._backpatch_breaks(for_end - 1, old_breaks, old_continues)
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
                self.emit_store_name(target.name)
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
            self.emit_load_name(expr.name)
        elif isinstance(expr, NullLiteral):
            idx = self.add_const(None)
            self.emit('LOAD_CONST', idx)
        elif isinstance(expr, Lambda):
            # Delegate to the shared helper so that `let f = fn(...){...}`
            # (which passes a name) and bare `fn(...){...}` expressions
            # share identical compilation logic.
            self._compile_lambda(expr)
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
                # short-circuit with Python semantics: falsy left -> keep
                # left's original value; truthy left -> evaluate and return
                # right.  JUMP_IF_FALSE pops the tested value, so we stash
                # left in a temp, test a copy, and reload the temp on the
                # short-circuit path (so `0 and 1` returns 0, not False).
                tmp = '__sc_tmp__'
                self.compile_expr(expr.left)
                self.emit_store_name(tmp)        # stash left
                self.emit_load_name(tmp)         # push copy to test
                self.emit('JUMP_IF_FALSE', None)
                jmp_false_pos = len(self.instructions)-1
                # left truthy: evaluate right and stash it
                self.compile_expr(expr.right)
                self.emit_store_name(tmp)
                end_pos = len(self.instructions)
                self.emit_load_name(tmp)         # result (right, or left if short-circuited)
                self.instructions[jmp_false_pos] = ('JUMP_IF_FALSE', end_pos)
            elif op == TokenType.OR:
                # short-circuit with Python semantics: truthy left -> keep
                # left's original value; falsy left -> evaluate and return
                # right (so `1 or 2` returns 1, not True).
                tmp = '__sc_tmp__'
                self.compile_expr(expr.left)
                self.emit_store_name(tmp)        # stash left
                self.emit_load_name(tmp)         # push copy to test
                self.emit('JUMP_IF_FALSE', None)
                jmp_eval_right = len(self.instructions)-1
                # left truthy: skip right, result is the stashed left
                self.emit('JUMP', None)
                jmp_end = len(self.instructions)-1
                eval_right_pos = len(self.instructions)
                self.instructions[jmp_eval_right] = ('JUMP_IF_FALSE', eval_right_pos)
                # left falsy: evaluate right and stash it
                self.compile_expr(expr.right)
                self.emit_store_name(tmp)
                end_pos = len(self.instructions)
                self.emit_load_name(tmp)         # result (left, or right if short-circuited)
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
        elif isinstance(expr, AwaitExpression):
            # `await expr` lowers to AWAIT.  The operand is compiled
            # first, so its result (expected to be an HFuture) is on
            # the top of the stack when AWAIT runs.
            #
            # Static check: `await` is only allowed
            #   (a) at the top level of a module (the entry script acts
            #       as an implicit async context — there's no enclosing
            #       function to be a non-async one), and
            #   (b) inside an `async fn` body.
            # Inside `fn` and `coro fn` bodies, `await` is rejected
            # because the surrounding function does not have the
            # `is_async` flag and therefore would not auto-wrap its
            # call result in an HFuture.
            if self.in_function_body and not self.in_async:
                raise CompileError(
                    "Static type error: `await` is only allowed inside an "
                    "`async fn` body (or at the top level of a module).  "
                    "`coro fn` and plain `fn` do not support `await`."
                )
            self.compile_expr(expr.expr)
            self.emit('AWAIT')
        elif isinstance(expr, PropagateExpression):
            # `expr?` — error-propagation postfix.  Compiles to a
            # SETUP_PROPAGATE / <expr> / POP_PROPAGATE / JUMP end /
            # <catch> triple.  The catch block pushes the unwrapped
            # exception value as the `?` expression's result and
            # jumps to the success continuation.  This makes `?`
            # behaviour equivalent to
            #   try { expr } catch (e) { e }
            # at the value level: the postfix's value is the
            # expression's normal value, or the exception payload
            # if `expr` raised.  The caller is then responsible for
            # either pattern-matching on the value or re-propagating
            # with another `?`.
            handler_pos = len(self.instructions)
            self.emit('SETUP_PROPAGATE', None)  # target back-patched
            self.compile_expr(expr.expr)
            self.emit('POP_PROPAGATE')
            jmp_end = len(self.instructions)
            self.emit('JUMP', None)             # success path
            # Catch path: SETUP_PROPAGATE dispatches the exception
            # here with the unwrapped value on the stack.  We just
            # fall through into the success continuation.
            catch_pos = len(self.instructions)
            end_pos = catch_pos                # fall through
            # Backpatch:
            self.instructions[handler_pos] = ('SETUP_PROPAGATE', catch_pos)
            self.instructions[jmp_end] = ('JUMP', end_pos)
        elif isinstance(expr, MatchExpression):
            # `match scrutinee { pat1 => body1, pat2 => body2, ... }`.
            # Compiles to:
            #   compile scrutinee
            #   for each case (in order):
            #     DUP                       ; keep scrutinee on stack
            #     LOAD_CONST <pattern_dict> ; pattern representation
            #     MATCH_CASE                ; pops scrutinee+pattern,
            #                              ; pushes bool (matched?)
            #     JUMP_IF_FALSE <next_case> ; if not, try next case
            #     compile body
            #     JUMP <end>
            #     <next_case>:
            #   RAISE "non-exhaustive match"  ; nothing matched
            #   <end>:
            self.compile_expr(expr.scrutinee)
            end_jumps = []   # JUMP positions to backpatch to end
            case_count = len(expr.cases)
            for idx, case in enumerate(expr.cases):
                is_last = (idx == case_count - 1)
                # Copy scrutinee to keep it for the next case's DUP.
                # Each case starts with the scrutinee on the stack
                # (from the previous case or from `compile_expr`
                # for the first case).  We DUP it and run MATCH_CASE
                # which pops both the dup and the pattern const, and
                # pushes a bool.
                self.emit('DUP')
                pat_idx = self.add_const(
                    self._pattern_to_const(case.pattern))
                self.emit('LOAD_CONST', pat_idx)
                self.emit('MATCH_CASE', pat_idx)
                next_case_pos = len(self.instructions)
                self.emit('JUMP_IF_FALSE', None)  # backpatch
                # Optional guard.
                if case.guard is not None:
                    self.compile_expr(case.guard)
                    guard_jmp = len(self.instructions)
                    self.emit('JUMP_IF_FALSE', None)
                    self.compile_expr(case.body)
                    end_jumps.append(len(self.instructions))
                    self.emit('JUMP', None)  # backpatch
                    guard_fail_pos = len(self.instructions)
                    self.instructions[guard_jmp] = ('JUMP_IF_FALSE', guard_fail_pos)
                    self.instructions[next_case_pos] = ('JUMP_IF_FALSE', guard_fail_pos)
                else:
                    self.compile_expr(case.body)  # Stack: [s, body]
                    end_jumps.append(len(self.instructions))
                    self.emit('JUMP', None)  # backpatch
                    fail_pos = len(self.instructions)
                    self.instructions[next_case_pos] = ('JUMP_IF_FALSE', fail_pos)
            # The leftover scrutinee from this arm stays on the
            # stack — the next case's DUP will reuse it.  If this
            # was the last case, the `RAISE` below pops it.
            # (Earlier versions emitted a POP here, but that wiped
            # the scrutinee the next iteration needed.)
            # No arm matched: push a default value of `null` and
            # raise.  This is more diagnostic than a bare RAISE with
            # an empty stack.
            none_idx = self.add_const(None)
            self.emit('LOAD_CONST', none_idx)
            err_idx = self.add_const("non-exhaustive match")
            self.emit('LOAD_CONST', err_idx)
            self.emit('RAISE')
            end_pos = len(self.instructions)
            for j in end_jumps:
                self.instructions[j] = ('JUMP', end_pos)
            # The success path leaves the body's result on top of
            # the leftover scrutinee (which MATCH_CASE never
            # consumed).  Swap them so the body's result is on
            # top and the scrutinee gets discarded, matching
            # `match` evaluation = body value, nothing else.
            self.emit('SWAP')  # Stack: [body, s]
            self.emit('POP')   # Stack: [body]
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
            has_targs = bool(getattr(expr, 'type_args', None))
            if isinstance(expr.func, Identifier):
                # If the callee is a free variable (captured from an enclosing
                # scope), the env holds a closure cell (HList), not the raw
                # function.  Emit LOAD_DEREF (to push the cell) BEFORE the
                # args, so the VM's `callValue` (which pops the function
                # first via `removeLast`, then the args via `popArgs`) sees
                # the correct stack layout: [arg1, arg2, ..., argN, function].
                if expr.func.name in self.deref_names:
                    if has_targs:
                        self._emit_type_args_list(expr.type_args)
                    for arg in expr.args:
                        self.compile_expr(arg)
                    self.emit_load_name(expr.func.name)  # push the cell LAST
                    op = 'CALL_VALUE_T' if has_targs else 'CALL_VALUE'
                    self.emit(op, len(expr.args))
                else:
                    if has_targs:
                        self._emit_type_args_list(expr.type_args)
                    for arg in expr.args:
                        self.compile_expr(arg)
                    op = 'CALL_FUNCTION_T' if has_targs else 'CALL_FUNCTION'
                    self.emit(op, (expr.func.name, len(expr.args)))
            elif isinstance(expr.func, MemberExpression):
                # for method call, compile left (instance), then args, then CALL_METHOD
                if has_targs:
                    self._emit_type_args_list(expr.type_args)
                self.compile_expr(expr.func.left)
                for arg in expr.args:
                    self.compile_expr(arg)
                op = 'CALL_METHOD_T' if has_targs else 'CALL_METHOD'
                self.emit(op, (expr.func.name, len(expr.args)))
            else:
                # General callable expression (e.g. `fns[i]`, lambdas, or
                # any other expression that yields a function value).
                # The VM's `callValue` expects the callee to be at the
                # TOP of the stack, so we push the value-args first and
                # the function/cell expression LAST.
                if has_targs:
                    self._emit_type_args_list(expr.type_args)
                for arg in expr.args:
                    self.compile_expr(arg)
                self.compile_expr(expr.func)
                op = 'CALL_VALUE_T' if has_targs else 'CALL_VALUE'
                self.emit(op, len(expr.args))
        elif isinstance(expr, NewExpression):
            # compile class expression (usually Identifier)
            # Use emit_load_name (closure-aware) so that a global class
            # name captured as a freevar by a lambda is correctly
            # dereferenced via LOAD_DEREF rather than LOAD_NAME (which
            # would find the closure cell HList instead of the class).
            has_targs = bool(getattr(expr, 'type_args', None))
            if isinstance(expr.class_name, Identifier):
                self.emit_load_name(expr.class_name.name)
            else:
                self.compile_expr(expr.class_name)
            if has_targs:
                self._emit_type_args_list(expr.type_args)
            for arg in expr.args:
                self.compile_expr(arg)
            op = 'CALL_NEW_T' if has_targs else 'CALL_NEW'
            self.emit(op, len(expr.args))
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