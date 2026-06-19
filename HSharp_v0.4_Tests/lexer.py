from tokens import TokenType

class Lexer:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.current_char = self.text[self.pos] if self.text else None
        self.line = 1
        self.col = 1

    def advance(self):
        if self.current_char == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        self.pos += 1
        if self.pos >= len(self.text):
            self.current_char = None
        else:
            self.current_char = self.text[self.pos]

    def skip_whitespace(self):
        while self.current_char and (self.current_char.isspace() or self.current_char == '#'):
            if self.current_char == '#':
                # skip comment until end of line
                while self.current_char and self.current_char != '\n':
                    self.advance()
                continue
            self.advance()

    def number(self):
        result = ''
        while self.current_char and self.current_char.isdigit():
            result += self.current_char
            self.advance()
        # handle fractional part
        if self.current_char == '.':
            result += '.'
            self.advance()
            frac = ''
            while self.current_char and self.current_char.isdigit():
                frac += self.current_char
                self.advance()
            if frac == '':
                raise SyntaxError('Invalid number literal')
            return float(result + frac)
        return int(result)

    def identifier(self):
        result = ''
        while self.current_char and (self.current_char.isalnum() or self.current_char == '_'):
            result += self.current_char
            self.advance()
        keywords = {
            'let': TokenType.LET,
            'fn': TokenType.FN,
            'return': TokenType.RETURN,
            'while': TokenType.WHILE,
            'if': TokenType.IF,
            'else': TokenType.ELSE,
            'for': TokenType.FOR,
            'in': TokenType.IN,
            'print': TokenType.PRINT,
            'import': TokenType.IMPORT,
            'class': TokenType.CLASS,
            'new': TokenType.NEW,
            'extends': TokenType.EXTENDS,
            'private': TokenType.PRIVATE,
            'static': TokenType.STATIC,
            'interface': TokenType.INTERFACE,
            'implements': TokenType.IMPLEMENTS,
            'union': TokenType.UNION,
            'super': TokenType.SUPER,
            'is': TokenType.IS,
            'as': TokenType.AS,
            'module': TokenType.MODULE,
            'concept': TokenType.CONCEPT,
            'coro': TokenType.CORO,
            'asm': TokenType.ASM,
            'ptr': TokenType.PTR,
            'true': ('BOOL', True),
            'false': ('BOOL', False),
            'and': TokenType.AND,
            'or': TokenType.OR,
            'not': TokenType.NOT,
            'continue': TokenType.CONTINUE,
            'break': TokenType.BREAK,
            'nullptr': (TokenType.NULL, None),
            'null': (TokenType.NULL, None),
            'auto': TokenType.AUTO,
            'try': TokenType.TRY,
            'catch': TokenType.CATCH,
            'throw': TokenType.THROW,
            'del': TokenType.DEL,
            '3dsizepower': TokenType.D3SIZEPOWER,
            'em3d': TokenType.EM3D,
            'region': TokenType.REGION,
            'region_interface': TokenType.REGION_INTERFACE,
            'public': TokenType.PUBLIC,
        }
        if result in keywords:
            val = keywords[result]
            if isinstance(val, tuple):
                # e.g. ('BOOL', True)
                if val[0] == 'BOOL':
                    return (TokenType.BOOL, val[1])
                return val
            else:
                return (val, None)
        return (TokenType.IDENTIFIER, result)

    def string(self):
        self.advance()
        result = ''
        while self.current_char is not None and self.current_char != '"':
            if self.current_char is None:
                raise SyntaxError("Unterminated string")
            if self.current_char == '\\':
                self.advance()
                if self.current_char == 'n':
                    result += '\n'
                    self.advance()
                elif self.current_char == '"':
                    result += '"'
                    self.advance()
                else:
                    result += '\\' + (self.current_char or '')
                    self.advance()
            else:
                result += self.current_char
                self.advance()
        self.advance()
        return (TokenType.STRING, result)
    def peek_token(self):
        saved_pos = self.pos
        saved_line = self.line
        saved_col = self.col
        saved_char = self.current_char
        token = self.get_next_token()
        self.pos = saved_pos
        self.line = saved_line
        self.col = saved_col
        self.current_char = saved_char
        return token

    def get_next_token(self):
        while self.current_char is not None:
            if self.current_char.isspace() or self.current_char == '#':
                self.skip_whitespace()
                continue

            if self.current_char.isdigit():
                start_pos = self.pos
                num_result = self.number()
                after_num = ''
                temp_pos = self.pos
                while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] == '_'):
                    after_num += self.text[self.pos]
                    self.pos += 1
                combined = str(num_result) + after_num
                if combined == '3dsizepower':
                    if self.pos < len(self.text):
                        self.current_char = self.text[self.pos]
                    else:
                        self.current_char = None
                    return (TokenType.D3SIZEPOWER, '3dsizepower')
                self.pos = temp_pos
                if self.pos < len(self.text):
                    self.current_char = self.text[self.pos]
                else:
                    self.current_char = None
                return (TokenType.NUMBER, num_result)

            if self.current_char.isalpha() or self.current_char == '_':
                return self.identifier()

            if self.current_char == '"':
                return self.string()

            # 多字符 operators
            if self.current_char == '=':
                self.advance()
                if self.current_char == '=':
                    self.advance()
                    return (TokenType.EQEQ, '==')
                return (TokenType.EQ, '=')
            if self.current_char == '!':
                self.advance()
                if self.current_char == '=':
                    self.advance()
                    return (TokenType.BANGEQ, '!=')
                # bare `!` is a logical-not prefix, like in C / Kotlin
                return (TokenType.NOT, '!')
            if self.current_char == '>':
                self.advance()
                if self.current_char == '=':
                    self.advance()
                    return (TokenType.GTE, '>=')
                if self.current_char == '>':
                    self.advance()
                    return (TokenType.RSHIFT, '>>')
                return (TokenType.GT, '>')
            if self.current_char == '<':
                self.advance()
                if self.current_char == '=':
                    self.advance()
                    return (TokenType.LTE, '<=')
                if self.current_char == '<':
                    self.advance()
                    return (TokenType.LSHIFT, '<<')
                return (TokenType.LT, '<')
            if self.current_char == '?':
                self.advance()
                if self.current_char == '^':
                    self.advance()
                    return (TokenType.QMARK_CARET, '?^')
                return (TokenType.QMARK, '?')

            # 单字符
            if self.current_char == '+':
                self.advance()
                return (TokenType.PLUS, '+')
            if self.current_char == '-':
                self.advance()
                return (TokenType.MINUS, '-')
            if self.current_char == '*':
                self.advance()
                return (TokenType.STAR, '*')
            if self.current_char == '/':
                self.advance()
                return (TokenType.SLASH, '/')
            if self.current_char == '&':
                self.advance()
                if self.current_char == '&':
                    self.advance()
                    return (TokenType.AND, '&&')
                return (TokenType.BITAND, '&')
            if self.current_char == '|':
                self.advance()
                if self.current_char == '|':
                    self.advance()
                    return (TokenType.OR, '||')
                return (TokenType.BITOR, '|')
            if self.current_char == '^':
                self.advance()
                return (TokenType.BITXOR, '^')
            if self.current_char == '~':
                self.advance()
                return (TokenType.TILDE, '~')
            if self.current_char == ';':
                self.advance()
                return (TokenType.SEMI, ';')
            if self.current_char == '(':
                self.advance()
                return (TokenType.LPAREN, '(')
            if self.current_char == ')':
                self.advance()
                return (TokenType.RPAREN, ')')
            if self.current_char == '{':
                self.advance()
                return (TokenType.LBRACE, '{')
            if self.current_char == '}':
                self.advance()
                return (TokenType.RBRACE, '}')
            if self.current_char == '[':
                self.advance()
                return (TokenType.LBRACKET, '[')
            if self.current_char == ']':
                self.advance()
                return (TokenType.RBRACKET, ']')
            if self.current_char == ':':
                self.advance()
                return (TokenType.COLON, ':')
            if self.current_char == ',':
                self.advance()
                return (TokenType.COMMA, ',')
            if self.current_char == '.':
                self.advance()
                return (TokenType.DOT, '.')
            if self.current_char == '%':
                self.advance()
                return (TokenType.MOD, '%')

            raise SyntaxError(f"Invalid character: '{self.current_char}'")

        return (TokenType.EOF, None)