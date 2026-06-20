from enum import Enum

class TokenType(Enum):
    LET = 'LET'
    FN = 'FN'
    RETURN = 'RETURN'
    WHILE = 'WHILE'
    IF = 'IF'
    ELSE = 'ELSE'
    FOR = 'FOR'
    IN = 'IN'
    PRINT = 'PRINT'
    IMPORT = 'IMPORT'
    CLASS = 'CLASS'
    NEW = 'NEW'
    INTERFACE = 'INTERFACE'
    IMPLEMENTS = 'IMPLEMENTS'
    EXTENDS = 'EXTENDS'
    UNION = 'UNION'
    PRIVATE = 'PRIVATE'
    STATIC = 'STATIC'
    SUPER = 'SUPER'
    IS = 'IS'
    AS = 'AS'
    MODULE = 'MODULE'
    CONCEPT = 'CONCEPT'
    CORO = 'CORO'
    ASYNC = 'ASYNC'
    AWAIT = 'AWAIT'
    PARALLEL = 'PARALLEL'  # `parallel fn foo()` — same as `@parallel`
    CONCURRENT = 'CONCURRENT'  # `concurrent { ... }` block
    CHAN = 'CHAN'  # `chan T` channel type
    AT = 'AT'  # `@` decorator prefix
    ASM = 'ASM'
    PTR = 'PTR'
    TRY = 'TRY'
    CATCH = 'CATCH'
    THROW = 'THROW'
    DEL = 'DEL'

    IDENTIFIER = 'IDENTIFIER'
    NUMBER = 'NUMBER'
    STRING = 'STRING'
    BOOL = 'BOOL'

    PLUS = 'PLUS'
    MINUS = 'MINUS'
    STAR = 'STAR'
    SLASH = 'SLASH'
    LSHIFT = 'LSHIFT'
    RSHIFT = 'RSHIFT'
    BITAND = 'BITAND'
    BITOR = 'BITOR'
    BITXOR = 'BITXOR'
    TILDE = 'TILDE'

    EQ = 'EQ'          # =
    EQEQ = 'EQEQ'      # ==
    BANGEQ = 'BANGEQ'  # !=
    GT = 'GT'
    LT = 'LT'
    GTE = 'GTE'
    LTE = 'LTE'
    MOD = 'MOD'        # %
    BAND = 'BAND'      # &

    LPAREN = 'LPAREN'
    RPAREN = 'RPAREN'
    LBRACE = 'LBRACE'
    RBRACE = 'RBRACE'
    LBRACKET = 'LBRACKET'
    RBRACKET = 'RBRACKET'

    COLON = 'COLON'    # :
    COMMA = 'COMMA'
    SEMI = 'SEMI'
    DOT = 'DOT'
    QMARK = 'QMARK'        # ?
    QMARK_CARET = 'QMARK_CARET'  # ?^
    AND = 'AND'
    OR = 'OR'
    NOT = 'NOT'
    CONTINUE = 'CONTINUE'
    BREAK = 'BREAK'
    AUTO = 'AUTO'
    NULL = 'NULL'
    EOF = 'EOF'

    D3SIZEPOWER = 'D3SIZEPOWER'
    EM3D = 'EM3D'
    REGION = 'REGION'
    REGION_INTERFACE = 'REGION_INTERFACE'
    PUBLIC = 'PUBLIC'