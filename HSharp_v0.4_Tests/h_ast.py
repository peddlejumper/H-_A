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
    def __init__(self, name, params, body, is_static=False):
        self.name = name
        self.params = params
        self.body = body
        self.is_static = is_static

class CallExpression(AST):
    def __init__(self, func, args):
        self.func = func
        self.args = args

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
    def __init__(self, name, body, base=None, implements=None):
        self.name = name
        self.body = body
        self.base = base
        self.implements = implements or []

class InterfaceDeclaration(AST):
    def __init__(self, name, body, bases=None):
        self.name = name
        self.body = body
        self.bases = bases or []

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
    def __init__(self, class_name, args):
        self.class_name = class_name
        self.args = args

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