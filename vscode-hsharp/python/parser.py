from tokens import TokenType
from h_ast import *

class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()

    def eat(self, token_type):
        if self.current_token[0] == token_type:
            self.current_token = self.lexer.get_next_token()
        else:
            raise SyntaxError(f"Expected {token_type}, got {self.current_token}")

    def parse(self):
        statements = []
        while self.current_token[0] != TokenType.EOF:
            stmt = self.statement()
            statements.append(stmt)
        return Program(statements)

    def statement(self):
        # module / concept / asm / coro support
        if self.current_token[0] == TokenType.MODULE:
            return self.module_declaration()
        if self.current_token[0] == TokenType.CONCEPT:
            return self.concept_declaration()
        if self.current_token[0] == TokenType.ASM:
            return self.asm_statement()
        if self.current_token[0] == TokenType.CORO:
            # coro fn ...
            self.eat(TokenType.CORO)
            fn = self.function_declaration(is_coro=True)
            return fn
        if self.current_token[0] == TokenType.ASYNC:
            # `async fn foo() { ... }` is sugar over `coro fn foo() { ... }`.
            # We require `async` to be followed by `fn` on the same logical
            # line so that `async` is still usable as an identifier inside
            # expression contexts.
            saved_lexer = self.lexer.save_state()
            saved_token = self.current_token
            try:
                self.eat(TokenType.ASYNC)
                if self.current_token[0] == TokenType.FN:
                    fn = self.function_declaration(is_async=True)
                    return fn
                # Not `async fn`; treat `async` as a plain identifier.
                self.lexer.restore_state(saved_lexer)
                self.current_token = saved_token
            except SyntaxError:
                self.lexer.restore_state(saved_lexer)
                self.current_token = saved_token
        if self.current_token[0] == TokenType.D3SIZEPOWER:
            return self.d3sizepower_declaration()
        if self.current_token[0] == TokenType.EM3D:
            return self.em3d_declaration()
        if self.current_token[0] == TokenType.LET:
            return self.let_statement()
        elif self.current_token[0] == TokenType.PRINT:
            return self.print_statement()
        elif self.current_token[0] == TokenType.FN:
            return self.function_declaration()
        elif self.current_token[0] == TokenType.CLASS:
            return self.class_declaration()
        elif self.current_token[0] == TokenType.INTERFACE:
            return self.interface_declaration()
        elif self.current_token[0] == TokenType.UNION:
            return self.union_declaration()
        elif self.current_token[0] == TokenType.WHILE:
            return self.while_statement()
        elif self.current_token[0] == TokenType.IF:
            return self.if_statement()
        elif self.current_token[0] == TokenType.TRY:
            return self.try_statement()
        elif self.current_token[0] == TokenType.THROW:
            return self.throw_statement()
        elif self.current_token[0] == TokenType.CONTINUE:
            self.eat(TokenType.CONTINUE)
            self.eat(TokenType.SEMI)
            return ContinueStatement()
        elif self.current_token[0] == TokenType.BREAK:
            self.eat(TokenType.BREAK)
            self.eat(TokenType.SEMI)
            return BreakStatement()
        elif self.current_token[0] == TokenType.FOR:
            return self.for_statement()
        elif self.current_token[0] == TokenType.IMPORT:
            return self.import_statement()
        elif self.current_token[0] == TokenType.RETURN:
            return self.return_statement()
        elif self.current_token[0] == TokenType.DEL:
            return self.del_statement()
        else:
            expr = self.expression()
            if isinstance(expr, IndexExpression) and self.current_token[0] == TokenType.EQ:
                self.eat(TokenType.EQ)
                value = self.expression()
                self.eat(TokenType.SEMI)
                return AssignmentIndex(expr.left, expr.index, value)
            if isinstance(expr, Identifier) and self.current_token[0] == TokenType.EQ:
                self.eat(TokenType.EQ)
                value = self.expression()
                self.eat(TokenType.SEMI)
                return AssignmentIdentifier(expr.name, value)
            if isinstance(expr, MemberExpression) and self.current_token[0] == TokenType.EQ:
                self.eat(TokenType.EQ)
                value = self.expression()
                self.eat(TokenType.SEMI)
                return AssignmentMember(expr.left, expr.name, value)
            else:
                self.eat(TokenType.SEMI)
                return expr

    def let_statement(self):
        # allow 'let' or 'auto' as variable declaration
        if self.current_token[0] == TokenType.LET:
            self.eat(TokenType.LET)
        else:
            self.eat(TokenType.AUTO)
        var_name = self.current_token[1]
        self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.EQ)
        value = self.expression()
        self.eat(TokenType.SEMI)
        return LetStatement(var_name, value)

    def print_statement(self):
        self.eat(TokenType.PRINT)
        expr = self.expression()
        self.eat(TokenType.SEMI)
        return PrintStatement(expr)

    def import_statement(self):
        self.eat(TokenType.IMPORT)
        if self.current_token[0] == TokenType.STRING:
            path = self.current_token[1]
            self.eat(TokenType.STRING)
        elif self.current_token[0] == TokenType.IDENTIFIER:
            name = self.current_token[1]
            self.eat(TokenType.IDENTIFIER)
            path = Identifier(name)
        else:
            raise SyntaxError('import requires a string path or identifier')
        self.eat(TokenType.SEMI)
        return ImportStatement(path)

    def function_declaration(self, is_coro=False, is_async=False):
        self.eat(TokenType.FN)
        func_name = self.current_token[1]
        self.eat(TokenType.IDENTIFIER)
        # Optional type parameter list: fn foo<T, U>(...)
        type_params = self._parse_type_params()
        self.eat(TokenType.LPAREN)
        params = []
        if self.current_token[0] != TokenType.RPAREN:
            params.append(self.current_token[1])
            self.eat(TokenType.IDENTIFIER)
            while self.current_token[0] == TokenType.COMMA:
                self.eat(TokenType.COMMA)
                params.append(self.current_token[1])
                self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.RPAREN)
        body = self.block()
        fn = Function(func_name, params, body, type_params=type_params)
        if is_coro:
            fn.is_coro = True
        if is_async:
            # `async fn` is sugar over the lower-level `coro fn`.  The
            # HVM recognises the resulting function object by the
            # `is_async` flag and wraps its return value in an
            # HFuture, so `await` can be statically checked against
            # the Future<T> return type.
            fn.is_coro = True
            fn.is_async = True
        return fn

    def _parse_type_params(self):
        """If current token is '<', parse a comma-separated list of
        identifiers and consume the closing '>'.  Returns the list
        (possibly empty).  Used by class/fn/interface declarations
        and by `new` / call expressions for type-argument lists."""
        if self.current_token[0] != TokenType.LT:
            return []
        self.eat(TokenType.LT)
        out = [self.current_token[1]]
        self.eat(TokenType.IDENTIFIER)
        while self.current_token[0] == TokenType.COMMA:
            self.eat(TokenType.COMMA)
            out.append(self.current_token[1])
            self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.GT)
        return out

    def module_declaration(self):
        self.eat(TokenType.MODULE)
        name = self.current_token[1]
        self.eat(TokenType.IDENTIFIER)
        body = self.block()
        return ModuleDeclaration(name, body)

    def concept_declaration(self):
        self.eat(TokenType.CONCEPT)
        name = self.current_token[1]
        self.eat(TokenType.IDENTIFIER)
        body = None
        if self.current_token[0] == TokenType.LBRACE:
            body = self.block()
        return ConceptDeclaration(name, body)

    def asm_statement(self):
        self.eat(TokenType.ASM)
        if self.current_token[0] == TokenType.STRING:
            code = self.current_token[1]
            self.eat(TokenType.STRING)
        else:
            # allow block for inline asm
            body = self.block()
            code = body
        self.eat(TokenType.SEMI)
        return AsmBlock(code)

    def class_declaration(self):
        self.eat(TokenType.CLASS)
        class_name = self.current_token[1]
        self.eat(TokenType.IDENTIFIER)
        # Optional type parameter list: class Foo<T, U>
        type_params = self._parse_type_params()
        base = None
        implements = []
        if self.current_token[0] == TokenType.EXTENDS:
            self.eat(TokenType.EXTENDS)
            base = self.current_token[1]
            self.eat(TokenType.IDENTIFIER)
        if self.current_token[0] == TokenType.IMPLEMENTS:
            self.eat(TokenType.IMPLEMENTS)
            implements.append(self.current_token[1])
            self.eat(TokenType.IDENTIFIER)
            while self.current_token[0] == TokenType.COMMA:
                self.eat(TokenType.COMMA)
                implements.append(self.current_token[1])
                self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.LBRACE)
        members = []
        while self.current_token[0] != TokenType.RBRACE:
            if self.current_token[0] == TokenType.PRIVATE:
                self.eat(TokenType.PRIVATE)
                self.eat(TokenType.LET)
                var_name = self.current_token[1]
                self.eat(TokenType.IDENTIFIER)
                self.eat(TokenType.EQ)
                value = self.expression()
                self.eat(TokenType.SEMI)
                members.append(FieldDeclaration(var_name, value, is_private=True))
            elif self.current_token[0] == TokenType.LET:
                self.eat(TokenType.LET)
                var_name = self.current_token[1]
                self.eat(TokenType.IDENTIFIER)
                self.eat(TokenType.EQ)
                value = self.expression()
                self.eat(TokenType.SEMI)
                members.append(FieldDeclaration(var_name, value, is_private=False))
            elif self.current_token[0] == TokenType.FN:
                members.append(self.function_declaration())
            elif self.current_token[0] == TokenType.STATIC:
                # static method
                self.eat(TokenType.STATIC)
                if self.current_token[0] != TokenType.FN:
                    raise SyntaxError('static must be followed by fn')
                fn = self.function_declaration()
                # mark function as static
                fn.is_static = True
                members.append(fn)
            else:
                members.append(self.statement())
        self.eat(TokenType.RBRACE)
        return ClassDeclaration(class_name, BlockStatement(members), base, implements, type_params=type_params)

    def interface_declaration(self):
        self.eat(TokenType.INTERFACE)
        name = self.current_token[1]
        self.eat(TokenType.IDENTIFIER)
        # Optional type parameter list: interface Foo<T, U>
        type_params = self._parse_type_params()
        bases = []
        if self.current_token[0] == TokenType.EXTENDS:
            self.eat(TokenType.EXTENDS)
            bases.append(self.current_token[1])
            self.eat(TokenType.IDENTIFIER)
            while self.current_token[0] == TokenType.COMMA:
                self.eat(TokenType.COMMA)
                bases.append(self.current_token[1])
                self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.LBRACE)
        methods = []
        while self.current_token[0] != TokenType.RBRACE:
            if self.current_token[0] == TokenType.FN:
                self.eat(TokenType.FN)
                mname = self.current_token[1]
                self.eat(TokenType.IDENTIFIER)
                # Interface method type params (rarely used, but supported)
                mtype_params = self._parse_type_params()
                self.eat(TokenType.LPAREN)
                params = []
                if self.current_token[0] != TokenType.RPAREN:
                    params.append(self.current_token[1])
                    self.eat(TokenType.IDENTIFIER)
                    while self.current_token[0] == TokenType.COMMA:
                        self.eat(TokenType.COMMA)
                        params.append(self.current_token[1])
                        self.eat(TokenType.IDENTIFIER)
                self.eat(TokenType.RPAREN)
                if self.current_token[0] == TokenType.SEMI:
                    self.eat(TokenType.SEMI)
                    methods.append(Function(mname, params, None, type_params=mtype_params))
                else:
                    body = self.block()
                    methods.append(Function(mname, params, body, type_params=mtype_params))
            else:
                raise SyntaxError('Only method declarations allowed in interface')
        self.eat(TokenType.RBRACE)
        return InterfaceDeclaration(name, BlockStatement(methods), bases, type_params=type_params)

    def union_declaration(self):
        self.eat(TokenType.UNION)
        name = self.current_token[1]
        self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.LBRACE)
        variants = []
        while self.current_token[0] != TokenType.RBRACE:
            var_name = self.current_token[1]
            self.eat(TokenType.IDENTIFIER)
            fields = []
            if self.current_token[0] == TokenType.COLON:
                self.eat(TokenType.COLON)
                fields.append(self.current_token[1])
                self.eat(TokenType.IDENTIFIER)
                while self.current_token[0] == TokenType.COMMA:
                    self.eat(TokenType.COMMA)
                    fields.append(self.current_token[1])
                    self.eat(TokenType.IDENTIFIER)
            self.eat(TokenType.SEMI)
            variants.append(UnionVariant(var_name, fields))
        self.eat(TokenType.RBRACE)
        return UnionDeclaration(name, variants)

    def d3sizepower_declaration(self):
        self.eat(TokenType.D3SIZEPOWER)
        name = self.current_token[1]
        self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.LBRACE)
        properties = []
        while self.current_token[0] not in (TokenType.REGION, TokenType.REGION_INTERFACE, TokenType.RBRACE):
            is_public = False
            if self.current_token[0] == TokenType.PUBLIC:
                is_public = True
                self.eat(TokenType.PUBLIC)
            prop_name = self.current_token[1]
            self.eat(TokenType.IDENTIFIER)
            if self.current_token[0] == TokenType.LBRACE:
                self.eat(TokenType.LBRACE)
                params = []
                if self.current_token[0] != TokenType.RBRACE:
                    if self.current_token[0] == TokenType.IDENTIFIER:
                        params.append(self.current_token[1])
                        self.eat(TokenType.IDENTIFIER)
                    elif self.current_token[0] == TokenType.NUMBER:
                        params.append(self.current_token[1])
                        self.eat(TokenType.NUMBER)
                    while self.current_token[0] == TokenType.COMMA:
                        self.eat(TokenType.COMMA)
                        if self.current_token[0] == TokenType.IDENTIFIER:
                            params.append(self.current_token[1])
                            self.eat(TokenType.IDENTIFIER)
                        elif self.current_token[0] == TokenType.NUMBER:
                            params.append(self.current_token[1])
                            self.eat(TokenType.NUMBER)
                self.eat(TokenType.RBRACE)
                properties.append(D3Property(prop_name, params, is_public))
            elif self.current_token[0] == TokenType.LBRACKET:
                self.eat(TokenType.LBRACKET)
                inner_params = self.d3_param_expr()
                self.eat(TokenType.RBRACKET)
                properties.append(D3Property(prop_name, inner_params, is_public))
            elif self.current_token[0] == TokenType.EQ:
                self.eat(TokenType.EQ)
                val = self.expression()
                properties.append(D3Property(prop_name, [val], is_public))
        regions = []
        region_interfaces = []
        while self.current_token[0] != TokenType.RBRACE:
            if self.current_token[0] == TokenType.REGION_INTERFACE:
                region_interfaces.append(self.d3_region_interface())
            elif self.current_token[0] == TokenType.REGION:
                regions.append(self.d3_region_declaration())
            else:
                raise SyntaxError(f"Expected region or region_interface, got {self.current_token}")
        self.eat(TokenType.RBRACE)
        body = BlockStatement(regions + region_interfaces)
        return D3SizePowerDeclaration(name, properties, body)

    def em3d_declaration(self):
        self.eat(TokenType.EM3D)
        name = self.current_token[1]
        self.eat(TokenType.IDENTIFIER)
        parent_d3 = None
        if self.current_token[0] == TokenType.EXTENDS:
            self.eat(TokenType.EXTENDS)
            parent_d3 = self.current_token[1]
            self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.LBRACE)
        properties = []
        while self.current_token[0] not in (TokenType.REGION, TokenType.REGION_INTERFACE, TokenType.RBRACE):
            is_public = False
            if self.current_token[0] == TokenType.PUBLIC:
                is_public = True
                self.eat(TokenType.PUBLIC)
            prop_name = self.current_token[1]
            self.eat(TokenType.IDENTIFIER)
            if self.current_token[0] == TokenType.LBRACE:
                self.eat(TokenType.LBRACE)
                params = []
                if self.current_token[0] != TokenType.RBRACE:
                    if self.current_token[0] == TokenType.IDENTIFIER:
                        params.append(self.current_token[1])
                        self.eat(TokenType.IDENTIFIER)
                    elif self.current_token[0] == TokenType.NUMBER:
                        params.append(self.current_token[1])
                        self.eat(TokenType.NUMBER)
                    while self.current_token[0] == TokenType.COMMA:
                        self.eat(TokenType.COMMA)
                        if self.current_token[0] == TokenType.IDENTIFIER:
                            params.append(self.current_token[1])
                            self.eat(TokenType.IDENTIFIER)
                        elif self.current_token[0] == TokenType.NUMBER:
                            params.append(self.current_token[1])
                            self.eat(TokenType.NUMBER)
                self.eat(TokenType.RBRACE)
                properties.append(D3Property(prop_name, params, is_public))
            elif self.current_token[0] == TokenType.LBRACKET:
                self.eat(TokenType.LBRACKET)
                inner_params = self.d3_param_expr()
                self.eat(TokenType.RBRACKET)
                properties.append(D3Property(prop_name, inner_params, is_public))
            elif self.current_token[0] == TokenType.EQ:
                self.eat(TokenType.EQ)
                val = self.expression()
                properties.append(D3Property(prop_name, [val], is_public))
        regions = []
        region_interfaces = []
        while self.current_token[0] != TokenType.RBRACE:
            if self.current_token[0] == TokenType.REGION_INTERFACE:
                region_interfaces.append(self.d3_region_interface())
            elif self.current_token[0] == TokenType.REGION:
                regions.append(self.d3_region_declaration())
            else:
                raise SyntaxError(f"Expected region or region_interface, got {self.current_token}")
        self.eat(TokenType.RBRACE)
        body = BlockStatement(regions + region_interfaces)
        return D3Em3dDeclaration(name, parent_d3, properties, body)

    def d3_param_expr(self):
        params = {}
        while self.current_token[0] == TokenType.IDENTIFIER or self.current_token[0] == TokenType.AUTO:
            if self.current_token[0] == TokenType.AUTO:
                    self.eat(TokenType.AUTO)
                    self.eat(TokenType.LBRACE)
                    inner_key = self.current_token[1]
                    self.eat(TokenType.IDENTIFIER)
                    self.eat(TokenType.EQ)
                    if self.current_token[0] == TokenType.AUTO:
                        self.eat(TokenType.AUTO)
                        self.eat(TokenType.BITXOR)
                        inner_val = None
                        if self.current_token[0] == TokenType.NUMBER:
                            inner_val = self.current_token[1]
                            self.eat(TokenType.NUMBER)
                            if self.current_token[0] == TokenType.IDENTIFIER:
                                inner_val = str(inner_val) + self.current_token[1]
                                self.eat(TokenType.IDENTIFIER)
                        else:
                            inner_val = self.current_token[1]
                            self.eat(TokenType.IDENTIFIER)
                        params[inner_key] = ['auto_pow', inner_val]
                    elif self.current_token[0] == TokenType.NUMBER:
                        inner_val = self.current_token[1]
                        self.eat(TokenType.NUMBER)
                        if self.current_token[0] == TokenType.IDENTIFIER:
                            inner_val = str(inner_val) + self.current_token[1]
                            self.eat(TokenType.IDENTIFIER)
                        params[inner_key] = ['auto', inner_val]
                    elif self.current_token[0] == TokenType.IDENTIFIER:
                        inner_val = self.current_token[1]
                        self.eat(TokenType.IDENTIFIER)
                        params[inner_key] = ['auto', inner_val]
                    elif self.current_token[0] == TokenType.STRING:
                        inner_val = self.current_token[1]
                        self.eat(TokenType.STRING)
                        params[inner_key] = ['auto', inner_val]
                    self.eat(TokenType.RBRACE)
            else:
                key = self.current_token[1]
                self.eat(TokenType.IDENTIFIER)
                self.eat(TokenType.EQ)
                if self.current_token[0] == TokenType.NUMBER:
                    params[key] = self.current_token[1]
                    self.eat(TokenType.NUMBER)
                elif self.current_token[0] == TokenType.IDENTIFIER:
                    params[key] = self.current_token[1]
                    self.eat(TokenType.IDENTIFIER)
                elif self.current_token[0] == TokenType.STRING:
                    params[key] = self.current_token[1]
                    self.eat(TokenType.STRING)
        return D3CoordinateExpr(params)

    def d3_region_interface(self):
        self.eat(TokenType.REGION_INTERFACE)
        name = self.current_token[1]
        self.eat(TokenType.IDENTIFIER)
        bases = []
        if self.current_token[0] == TokenType.EXTENDS:
            self.eat(TokenType.EXTENDS)
            bases.append(self.current_token[1])
            self.eat(TokenType.IDENTIFIER)
            while self.current_token[0] == TokenType.COMMA:
                self.eat(TokenType.COMMA)
                bases.append(self.current_token[1])
                self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.LBRACE)
        methods = []
        while self.current_token[0] != TokenType.RBRACE:
            if self.current_token[0] == TokenType.FN:
                self.eat(TokenType.FN)
                mname = self.current_token[1]
                self.eat(TokenType.IDENTIFIER)
                self.eat(TokenType.LPAREN)
                params = []
                if self.current_token[0] != TokenType.RPAREN:
                    params.append(self.current_token[1])
                    self.eat(TokenType.IDENTIFIER)
                    while self.current_token[0] == TokenType.COMMA:
                        self.eat(TokenType.COMMA)
                        params.append(self.current_token[1])
                        self.eat(TokenType.IDENTIFIER)
                self.eat(TokenType.RPAREN)
                self.eat(TokenType.SEMI)
                methods.append(Function(mname, params, None))
            else:
                raise SyntaxError('Only method declarations allowed in region_interface')
        self.eat(TokenType.RBRACE)
        return D3RegionInterfaceDeclaration(name, methods, bases)

    def d3_region_declaration(self):
        self.eat(TokenType.REGION)
        name = self.current_token[1]
        self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.LPAREN)
        coords = []
        coords.append(self.current_token[1])
        self.eat(TokenType.NUMBER)
        while self.current_token[0] == TokenType.COMMA:
            self.eat(TokenType.COMMA)
            if self.current_token[0] == TokenType.NUMBER:
                coords.append(self.current_token[1])
                self.eat(TokenType.NUMBER)
            elif self.current_token[0] == TokenType.IDENTIFIER:
                coords.append(self.current_token[1])
                self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.RPAREN)
        implements = []
        if self.current_token[0] == TokenType.IMPLEMENTS:
            self.eat(TokenType.IMPLEMENTS)
            implements.append(self.current_token[1])
            self.eat(TokenType.IDENTIFIER)
            while self.current_token[0] == TokenType.COMMA:
                self.eat(TokenType.COMMA)
                implements.append(self.current_token[1])
                self.eat(TokenType.IDENTIFIER)
        body = self.block()
        return D3RegionDeclaration(name, coords, body, implements)

    def block(self):
        self.eat(TokenType.LBRACE)
        statements = []
        while self.current_token[0] != TokenType.RBRACE:
            statements.append(self.statement())
        self.eat(TokenType.RBRACE)
        return BlockStatement(statements)

    def while_statement(self):
        self.eat(TokenType.WHILE)
        self.eat(TokenType.LPAREN)
        condition = self.expression()
        self.eat(TokenType.RPAREN)
        body = self.block()
        return WhileStatement(condition, body)

    def if_statement(self):
        self.eat(TokenType.IF)
        self.eat(TokenType.LPAREN)
        condition = self.expression()
        self.eat(TokenType.RPAREN)
        consequence = self.block()
        alternative = None
        if self.current_token[0] == TokenType.ELSE:
            self.eat(TokenType.ELSE)
            if self.current_token[0] == TokenType.IF:
                alternative = self.if_statement()
            else:
                alternative = self.block()
        return IfStatement(condition, consequence, alternative)

    def for_statement(self):
        self.eat(TokenType.FOR)
        var1 = self.current_token[1]
        self.eat(TokenType.IDENTIFIER)
        var2 = None
        if self.current_token[0] == TokenType.COMMA:
            self.eat(TokenType.COMMA)
            var2 = self.current_token[1]
            self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.IN)
        iterable = self.expression()
        body = self.block()
        return ForStatement(var1, var2, iterable, body)

    def return_statement(self):
        self.eat(TokenType.RETURN)
        # support both `return;` and `return expr;`
        if self.current_token[0] == TokenType.SEMI:
            self.current_token = self.lexer.get_next_token()
            return ReturnStatement(None)
        expr = self.expression()
        self.eat(TokenType.SEMI)
        return ReturnStatement(expr)

    def del_statement(self):
        self.eat(TokenType.DEL)
        target = self.expression()
        self.eat(TokenType.SEMI)
        return DeleteStatement(target)

    def try_statement(self):
        self.eat(TokenType.TRY)
        body = self.block()
        self.eat(TokenType.CATCH)
        self.eat(TokenType.LPAREN)
        exception_name = self.current_token[1]
        self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.RPAREN)
        handler = self.block()
        return TryStatement(body, exception_name, handler)

    def throw_statement(self):
        self.eat(TokenType.THROW)
        expr = self.expression()
        self.eat(TokenType.SEMI)
        return ThrowStatement(expr)

    def expression(self):
        return self.ternary()

    def ternary(self):
        node = self.logical_or()
        # Check for ternary ? or quaternary ?^
        if self.current_token[0] == TokenType.QMARK:
            self.eat(TokenType.QMARK)
            true_expr = self.expression()
            self.eat(TokenType.COLON)
            false_expr = self.expression()
            return TernaryOp(node, true_expr, false_expr)
        if self.current_token[0] == TokenType.QMARK_CARET:
            self.eat(TokenType.QMARK_CARET)
            expr1 = self.expression()
            self.eat(TokenType.COLON)
            cond2 = self.logical_or()  # no ternary inside cond2 to avoid ambiguity
            self.eat(TokenType.COLON)
            expr2 = self.expression()
            return QuaternaryOp(node, expr1, cond2, expr2)
        return node

    def logical_or(self):
        node = self.logical_and()
        while self.current_token[0] == TokenType.OR:
            token = self.current_token
            self.eat(TokenType.OR)
            node = BinaryOp(left=node, op=token[0], right=self.logical_and())
        return node

    def logical_and(self):
        node = self.equality()
        while self.current_token[0] == TokenType.AND:
            token = self.current_token
            self.eat(TokenType.AND)
            node = BinaryOp(left=node, op=token[0], right=self.equality())
        return node

    def equality(self):
        node = self.bitwise_or()
        while self.current_token[0] in (TokenType.EQEQ, TokenType.BANGEQ):
            token = self.current_token
            self.eat(token[0])
            node = BinaryOp(left=node, op=token[0], right=self.comparison())
        return node

    def bitwise_or(self):
        node = self.comparison()
        while self.current_token[0] in (TokenType.BITOR, TokenType.BITXOR, TokenType.BITAND, TokenType.LSHIFT, TokenType.RSHIFT):
            token = self.current_token
            self.eat(token[0])
            node = BinaryOp(left=node, op=token[0], right=self.comparison())
        return node

    def comparison(self):
        node = self.term()
        while self.current_token[0] in (TokenType.GT, TokenType.LT, TokenType.GTE, TokenType.LTE, TokenType.IN):
            token = self.current_token
            self.eat(token[0])
            node = BinaryOp(left=node, op=token[0], right=self.term())
        return node

    def term(self):
        node = self.factor()
        while self.current_token[0] in (TokenType.PLUS, TokenType.MINUS):
            token = self.current_token
            self.eat(token[0])
            node = BinaryOp(left=node, op=token[0], right=self.factor())
        return node

    def factor(self):
        node = self.unary()
        while self.current_token[0] in (TokenType.STAR, TokenType.SLASH, TokenType.MOD):
            token = self.current_token
            self.eat(token[0])
            node = BinaryOp(left=node, op=token[0], right=self.unary())
        return node

    def unary(self):
        if self.current_token[0] == TokenType.MINUS:
            token = self.current_token
            self.eat(TokenType.MINUS)
            return BinaryOp(NumberLiteral(0), TokenType.MINUS, self.unary())
        if self.current_token[0] == TokenType.NOT:
            self.eat(TokenType.NOT)
            return UnaryOp(TokenType.NOT, self.unary())
        if self.current_token[0] == TokenType.STAR:
            # pointer dereference (syntactic support)
            self.eat(TokenType.STAR)
            return PointerDereference(self.unary())
        if self.current_token[0] == TokenType.TILDE:
            self.eat(TokenType.TILDE)
            return UnaryOp(TokenType.TILDE, self.unary())
        if self.current_token[0] == TokenType.AWAIT:
            # `await expr` lowers to a single AWAIT opcode.  The
            # static check that `await` only appears inside an
            # `async fn` body is performed by the compiler.
            self.eat(TokenType.AWAIT)
            return AwaitExpression(self.unary())
        return self.primary()

    def primary(self):
        token = self.current_token
        if token[0] == TokenType.FN:
            # lambda expression: fn(params) { body }
            self.eat(TokenType.FN)
            self.eat(TokenType.LPAREN)
            params = []
            if self.current_token[0] != TokenType.RPAREN:
                params.append(self.current_token[1])
                self.eat(TokenType.IDENTIFIER)
                while self.current_token[0] == TokenType.COMMA:
                    self.eat(TokenType.COMMA)
                    params.append(self.current_token[1])
                    self.eat(TokenType.IDENTIFIER)
            self.eat(TokenType.RPAREN)
            body = self.block()
            return Lambda(params, body)
        if token[0] == TokenType.NULL:
            self.eat(TokenType.NULL)
            return NullLiteral()
        if token[0] == TokenType.NEW:
            self.eat(TokenType.NEW)
            cls_name = self.current_token[1]
            self.eat(TokenType.IDENTIFIER)
            # Optional type-arg list: new Foo<T, U>(...)
            type_args = self._parse_type_params()
            self.eat(TokenType.LPAREN)
            args = []
            if self.current_token[0] != TokenType.RPAREN:
                args.append(self.expression())
                while self.current_token[0] == TokenType.COMMA:
                    self.eat(TokenType.COMMA)
                    args.append(self.expression())
            self.eat(TokenType.RPAREN)
            return NewExpression(Identifier(cls_name), args, type_args=type_args)
        if token[0] == TokenType.SUPER:
            self.eat(TokenType.SUPER)
            self.eat(TokenType.DOT)
            method_name = self.current_token[1]
            self.eat(TokenType.IDENTIFIER)
            self.eat(TokenType.LPAREN)
            args = []
            if self.current_token[0] != TokenType.RPAREN:
                args.append(self.expression())
                while self.current_token[0] == TokenType.COMMA:
                    self.eat(TokenType.COMMA)
                    args.append(self.expression())
            self.eat(TokenType.RPAREN)
            return SuperExpression(method_name, args)
        if token[0] == TokenType.NUMBER:
            self.eat(TokenType.NUMBER)
            return self._parse_postfix(NumberLiteral(token[1]))
        elif token[0] == TokenType.STRING:
            self.eat(TokenType.STRING)
            return self._parse_postfix(StringLiteral(token[1]))
        elif token[0] == TokenType.BOOL:
            self.eat(TokenType.BOOL)
            return self._parse_postfix(BooleanLiteral(token[1]))
        elif token[0] == TokenType.LBRACKET:
            return self.array_literal()
        elif token[0] == TokenType.LBRACE:
            return self.dict_literal()
        elif token[0] == TokenType.IDENTIFIER:
            name = token[1]
            self.eat(TokenType.IDENTIFIER)
            return self._parse_postfix(Identifier(name))
        elif token[0] == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            node = self.expression()
            self.eat(TokenType.RPAREN)
            return self._parse_postfix(node)
        else:
            line = self.current_token[2] if len(self.current_token) > 2 else '?'
            col = self.current_token[3] if len(self.current_token) > 3 else '?'
            raise SyntaxError(f"Unexpected token: {token} at line {line}, col {col}")

    def _parse_subscript(self):
        """Parse one subscript inside `[ … ]` — an expression or a slice
        expression of the form `[start? : end? (: step?)?]`."""
        start = None
        if self.current_token[0] != TokenType.COLON:
            start = self.expression()
        if self.current_token[0] == TokenType.COLON:
            self.eat(TokenType.COLON)
            end = None
            if self.current_token[0] not in (TokenType.COLON, TokenType.RBRACKET, TokenType.COMMA):
                end = self.expression()
            step = None
            if self.current_token[0] == TokenType.COLON:
                self.eat(TokenType.COLON)
                if self.current_token[0] not in (TokenType.RBRACKET, TokenType.COMMA):
                    step = self.expression()
            return SliceExpression(start, end, step)
        return start

    def _parse_postfix(self, node):
        """Apply zero or more postfix operators (`(args)`, `[idx]`, `.name`,
        `{Variant:…}`) to an already-parsed primary.  Used uniformly for
        identifiers, literals, and parenthesised expressions so that things
        like `"hello".length()` and `(a + b).method(1)` parse correctly.

        A leading `name<T, U>(args)` (call with explicit type arguments) is
        allowed when `node` is an `Identifier`.  Because the `<` operator
        also appears in binary comparisons, we use a try/restore approach:
        peek ahead to confirm the shape `<ident[, ident]*>(` and only then
        consume the tokens as type arguments.  If the shape does not match
        (e.g. `a < b` in a comparison), the `<` is left untouched and the
        surrounding expression layer handles it as a comparison operator."""
        if (isinstance(node, Identifier) and
                self.current_token[0] == TokenType.LT):
            saved_lexer = self.lexer.save_state()
            saved_token = self.current_token
            try:
                type_args = self._parse_type_params()
                if self.current_token[0] == TokenType.LPAREN:
                    # Real type-arg list; keep the consumption and stash
                    # the names so the next loop iteration can attach them
                    # to the call expression.
                    node._pending_type_args = type_args
                else:
                    # Wasn't a type-arg list (e.g. `a < b`).  Undo.
                    self.lexer.restore_state(saved_lexer)
                    self.current_token = saved_token
            except SyntaxError:
                self.lexer.restore_state(saved_lexer)
                self.current_token = saved_token
        while True:
            if (hasattr(node, '_pending_type_args') and
                    self.current_token[0] == TokenType.LPAREN):
                pending = node._pending_type_args
                self.eat(TokenType.LPAREN)
                args = []
                if self.current_token[0] != TokenType.RPAREN:
                    args.append(self.expression())
                    while self.current_token[0] == TokenType.COMMA:
                        self.eat(TokenType.COMMA)
                        args.append(self.expression())
                self.eat(TokenType.RPAREN)
                call = CallExpression(node, args, type_args=pending)
                node = call
                continue
            if self.current_token[0] == TokenType.LPAREN:
                self.eat(TokenType.LPAREN)
                args = []
                if self.current_token[0] != TokenType.RPAREN:
                    args.append(self.expression())
                    while self.current_token[0] == TokenType.COMMA:
                        self.eat(TokenType.COMMA)
                        args.append(self.expression())
                self.eat(TokenType.RPAREN)
                node = CallExpression(node, args)
                continue
            if self.current_token[0] == TokenType.LBRACKET:
                self.eat(TokenType.LBRACKET)
                subscripts = [self._parse_subscript()]
                while self.current_token[0] == TokenType.COMMA:
                    self.eat(TokenType.COMMA)
                    subscripts.append(self._parse_subscript())
                self.eat(TokenType.RBRACKET)
                for sub in subscripts:
                    node = IndexExpression(node, sub)
                continue
            if self.current_token[0] == TokenType.DOT:
                self.eat(TokenType.DOT)
                attr = self.current_token[1]
                self.eat(TokenType.IDENTIFIER)
                node = MemberExpression(node, attr)
                continue
            if self.current_token[0] == TokenType.LBRACE:
                # Union construction: TypeName{VariantName: expr1, ...} or TypeName{VariantName}
                # Check for {Identifier: or {Identifier} pattern; if not, let parent handle the {
                saved_token = self.current_token
                saved_pos = self.lexer.pos
                saved_line = self.lexer.line
                saved_col = self.lexer.col
                saved_char = self.lexer.current_char
                self.eat(TokenType.LBRACE)  # consume {
                tok1 = self.current_token
                has_pattern = (tok1[0] == TokenType.IDENTIFIER)
                if has_pattern:
                    self.eat(TokenType.IDENTIFIER)  # consume variant name
                    has_pattern = (self.current_token[0] == TokenType.COLON or self.current_token[0] == TokenType.RBRACE)
                # Restore lexer state and current token
                self.lexer.pos = saved_pos
                self.lexer.line = saved_line
                self.lexer.col = saved_col
                self.lexer.current_char = saved_char
                self.current_token = saved_token
                if not has_pattern:
                    break
                # Now parse union construction for real
                self.eat(TokenType.LBRACE)
                var_name = self.current_token[1]
                self.eat(TokenType.IDENTIFIER)
                values = []
                if self.current_token[0] == TokenType.COLON:
                    self.eat(TokenType.COLON)
                    values.append(self.expression())
                    while self.current_token[0] == TokenType.COMMA:
                        self.eat(TokenType.COMMA)
                        values.append(self.expression())
                self.eat(TokenType.RBRACE)
                node = UnionConstructExpression(node, var_name, values)
                continue
            break
        return node

    def array_literal(self):
        self.eat(TokenType.LBRACKET)
        elements = []
        if self.current_token[0] != TokenType.RBRACKET:
            elements.append(self.expression())
            while self.current_token[0] == TokenType.COMMA:
                self.eat(TokenType.COMMA)
                elements.append(self.expression())
        self.eat(TokenType.RBRACKET)
        return ArrayLiteral(elements)

    def dict_literal(self):
        self.eat(TokenType.LBRACE)
        pairs = []
        if self.current_token[0] != TokenType.RBRACE:
            key = self.expression()
            self.eat(TokenType.COLON)
            value = self.expression()
            pairs.append((key, value))
            while self.current_token[0] == TokenType.COMMA:
                self.eat(TokenType.COMMA)
                key = self.expression()
                self.eat(TokenType.COLON)
                value = self.expression()
                pairs.append((key, value))
        self.eat(TokenType.RBRACE)
        return DictLiteral(pairs)