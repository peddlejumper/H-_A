class AST:
    pass

class Program(AST):
    def __init__(self, statements):
        self.statements = statements

class LetStatement(AST):
    def __init__(self, name, value):
        self.name = name
        self.value = value

class PrintStatement(AST):
    def __init__(self, expr):
        self.expr = expr

class ImportStatement(AST):
    def __init__(self, path):
        self.path = path

class Function(AST):
    def __init__(self, name, params, body, is_static=False, type_params=None,
                 is_async=False, is_parallel=False, decorators=None):
        self.name = name
        self.params = params
        self.body = body
        self.is_static = is_static
        self.type_params = type_params or []
        # `async fn foo() { ... }` lowers to `coro fn foo() { ... }`
        # with an extra `is_async` marker on the func object so that the
        # Kotlin VM can recognise async calls and wrap their result in
        # a HFuture.
        self.is_async = is_async
        # `@parallel foo() { ... }` (or `parallel fn foo() { ... }`)
        # marks the function as a multi-threaded DZZW worker-pool
        # task.  The call site submits the body to a worker thread
        # and returns an HFuture whose cell is left PENDING until a
        # worker completes the body.  This is the *user-facing* way
        # to get true parallelism; `async fn` is single-threaded.
        self.is_parallel = is_parallel
        # Raw decorator list, e.g. ['@parallel'].  Kept for future
        # user-defined decorators; the compiler currently only acts
        # on the well-known ones (`@parallel`).
        self.decorators = decorators or []

class AwaitExpression(AST):
    """`await expr` — must appear inside an `async fn` body.  The
    operand `expr` is expected to be an HFuture (or any HValue
    recognised as awaitable by the static check).  At runtime this
    lowers to a single AWAIT opcode that synchronously pulls the
    future's value; since H# has no real concurrency, async/await is
    a static-analysis-friendly sugar over the underlying `coro fn` /
    HFuture machinery."""
    def __init__(self, expr):
        self.expr = expr

class CallExpression(AST):
    def __init__(self, func, args, type_args=None):
        self.func = func
        self.args = args
        self.type_args = type_args or []

class ReturnStatement(AST):
    def __init__(self, expr):
        self.expr = expr

class WhileStatement(AST):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

class IfStatement(AST):
    def __init__(self, condition, consequence, alternative=None):
        self.condition = condition
        self.consequence = consequence
        self.alternative = alternative

class TryStatement(AST):
    def __init__(self, body, exception_name, handler):
        self.body = body
        self.exception_name = exception_name
        self.handler = handler

class ThrowStatement(AST):
    def __init__(self, expr):
        self.expr = expr

class ForStatement(AST):
    def __init__(self, var1, var2, iterable, body):
        self.var1 = var1
        self.var2 = var2
        self.iterable = iterable
        self.body = body

class BlockStatement(AST):
    def __init__(self, statements):
        self.statements = statements

class ConcurrentBlock(AST):
    """`concurrent { stmt1; stmt2; ... }` — a structured-concurrency
    block.  All `@parallel` coroutines spawned inside the body are
    registered as children of an implicit scope; the block's exit
    joins on every child and re-throws the first failure.

    Note: at the AST level a ConcurrentBlock is just a BlockStatement
    with extra context; the compiler emits CONCURRENT_ENTER before
    the body and CONCURRENT_EXIT after.  We model it as its own node
    so the parser can be explicit about it (rather than overload the
    `block` rule with a heuristic)."""
    def __init__(self, body):
        self.body = body

class Identifier(AST):
    def __init__(self, name):
        self.name = name

class NumberLiteral(AST):
    def __init__(self, value):
        self.value = value

class StringLiteral(AST):
    def __init__(self, value):
        self.value = value

class BooleanLiteral(AST):
    def __init__(self, value):
        self.value = value

class NullLiteral(AST):
    def __init__(self):
        pass

class Lambda(AST):
    def __init__(self, params, body):
        self.params = params
        self.body = body

class UnaryOp(AST):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

class ArrayLiteral(AST):
    def __init__(self, elements):
        self.elements = elements

class DictLiteral(AST):
    def __init__(self, pairs):
        self.pairs = pairs

class IndexExpression(AST):
    def __init__(self, left, index):
        self.left = left
        self.index = index

class SliceExpression(AST):
    """`a:b` or `a:b:c` slice — a separate AST node so it can be
    compiled to a single `SLICE` opcode rather than two GET_ITEMs."""
    def __init__(self, start, end, step=None):
        self.start = start   # expression or None
        self.end = end       # expression or None
        self.step = step     # expression or None

class BinaryOp(AST):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class TernaryOp(AST):
    def __init__(self, condition, true_expr, false_expr):
        self.condition = condition
        self.true_expr = true_expr
        self.false_expr = false_expr

class QuaternaryOp(AST):
    def __init__(self, cond1, expr1, cond2, expr2):
        self.cond1 = cond1
        self.expr1 = expr1
        self.cond2 = cond2
        self.expr2 = expr2

class MatchPattern(AST):
    """A single pattern inside a `match` arm.

    `kind` is one of:
      - "wildcard"  : the `_` pattern — matches anything, no binding
      - "binding"   : a bare identifier — matches anything, binds to name
      - "literal"   : number / string / bool / null literal equality
      - "type"      : `is T` — matches a value of type T, optional binding
      - "variant"   : `Variant(x, y, ...)` — matches a union variant
      - "chan_send": `chan send(v)` — channel can-send pattern
      - "chan_recv": `chan recv(v)` — channel can-recv pattern
      - "chan_close": `chan close` — channel is closed pattern

    `bindings` is a list of (name, optional_subpattern) tuples.  For
    `wildcard` / `literal` / `type` without a binding name it is empty.
    For `variant("Some", x)` it is `[("x", None)]`.  For
    `chan_send(v)` it is `[("v", None)]`.
    """
    def __init__(self, kind, bindings=None, literal=None, type_name=None,
                 variant_name=None):
        self.kind = kind
        self.bindings = bindings or []
        self.literal = literal          # for kind == "literal"
        self.type_name = type_name      # for kind == "type"
        self.variant_name = variant_name  # for kind == "variant"

class MatchCase(AST):
    """A single arm of a `match` expression: a pattern, an optional
    guard, and a body expression (or block)."""
    def __init__(self, pattern, body, guard=None):
        self.pattern = pattern
        self.body = body
        self.guard = guard  # optional Boolean expression; None means no guard

class MatchExpression(AST):
    """`match scrutinee { pat1 => body1, pat2 => body2, ... }`.

    The body of each arm is an expression.  The whole `match` form
    evaluates to the value of the chosen arm's body.  If no arm
    matches, a runtime `HSharpException` is raised with message
    "non-exhaustive match" (this is a deliberate failure mode; users
    are expected to include a `_ => ...` wildcard arm).
    """
    def __init__(self, scrutinee, cases):
        self.scrutinee = scrutinee
        self.cases = cases  # list of MatchCase

class PropagateExpression(AST):
    """`expr?` — the error-propagation postfix operator.

    At runtime:
      1. evaluate `expr`
      2. if it raises, the current function returns immediately
         with the raised value (the exception payload is returned
         as-is — the caller sees a "Result"-like result)
      3. if it succeeds, the value is unwrapped and execution
         continues normally

    In H#'s single-frame-per-function design, `?` lowers to a
    `TRY_PUSH` followed by the expr's code, then `TRY_POP` on
    the success path.  On failure the VM marks the current frame
    as halted-with-return-value = raised-payload and unwinds to
    the call site.
    """
    def __init__(self, expr):
        self.expr = expr

class AssignmentIndex(AST):
    def __init__(self, array, index, value):
        self.array = array
        self.index = index
        self.value = value

class DeleteStatement(AST):
    def __init__(self, target):
        self.target = target

class AssignmentIdentifier(AST):
    def __init__(self, name, value):
        self.name = name
        self.value = value

class MemberExpression(AST):
    def __init__(self, left, name):
        self.left = left
        self.name = name

class AssignmentMember(AST):
    def __init__(self, left, name, value):
        self.left = left
        self.name = name
        self.value = value

class ClassDeclaration(AST):
    def __init__(self, name, body, base=None, implements=None, type_params=None):
        self.name = name
        self.body = body
        self.base = base
        self.implements = implements or []
        self.type_params = type_params or []

class InterfaceDeclaration(AST):
    def __init__(self, name, body, bases=None, type_params=None):
        self.name = name
        self.body = body
        self.bases = bases or []
        self.type_params = type_params or []

class UnionVariant(AST):
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields  # list of field names (strings)

class UnionDeclaration(AST):
    def __init__(self, name, variants):
        self.name = name
        self.variants = variants  # list of UnionVariant

class UnionConstructExpression(AST):
    def __init__(self, type_name, variant_name, values):
        self.type_name = type_name  # Identifier or string
        self.variant_name = variant_name  # string
        self.values = values  # list of expressions

class FieldDeclaration(AST):
    def __init__(self, name, value, is_private=False):
        self.name = name
        self.value = value
        self.is_private = is_private

class NewExpression(AST):
    def __init__(self, class_name, args, type_args=None):
        self.class_name = class_name
        self.args = args
        self.type_args = type_args or []

class SuperExpression(AST):
    def __init__(self, method_name, args):
        self.method_name = method_name
        self.args = args

class InstanceOfExpression(AST):
    def __init__(self, expr, type_name):
        self.expr = expr
        self.type_name = type_name

class CastExpression(AST):
    def __init__(self, expr, type_name):
        self.expr = expr
        self.type_name = type_name

class ModuleDeclaration(AST):
    def __init__(self, name, body):
        self.name = name
        self.body = body

class ConceptDeclaration(AST):
    def __init__(self, name, body=None):
        self.name = name
        self.body = body

class AsmBlock(AST):
    def __init__(self, code):
        self.code = code

class PointerDereference(AST):
    def __init__(self, target):
        self.target = target

class ContinueStatement(AST):
    def __init__(self):
        pass

class BreakStatement(AST):
    def __init__(self):
        pass

class CoroFunction(AST):
    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.body = body

class D3SizePowerDeclaration(AST):
    def __init__(self, name, properties, body):
        self.name = name
        self.properties = properties
        self.body = body

class D3Property(AST):
    def __init__(self, name, params, is_public=False):
        self.name = name
        self.params = params
        self.is_public = is_public

class D3RegionDeclaration(AST):
    def __init__(self, name, coords, body, implements=None):
        self.name = name
        self.coords = coords
        self.body = body
        self.implements = implements or []

class D3RegionInterfaceDeclaration(AST):
    def __init__(self, name, methods, bases=None):
        self.name = name
        self.methods = methods
        self.bases = bases or []

class D3Em3dDeclaration(AST):
    def __init__(self, name, parent_d3, properties, body):
        self.name = name
        self.parent_d3 = parent_d3
        self.properties = properties
        self.body = body

class D3CoordinateExpr(AST):
    def __init__(self, params):
        self.params = params