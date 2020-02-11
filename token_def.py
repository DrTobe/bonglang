class Token:
    def __init__(self, typ, filepath, line, col, length, prec_by_space = False, lexeme = None):
        self.type = typ
        self.prec_by_space = prec_by_space
        self.lexeme = lexeme
        self.filepath = filepath
        self.line = line
        self.col = col
        self.length = length
    def __str__(self):
        if self.lexeme != None:
            return self.type + "(" + str(self.lexeme) + ")"
        return self.type

BONG = "|"
AMPERSAND = "&"
OTHER = "OTHER"
EOF = "EOF"
ASSIGN = "="
DOT = "."
SEMICOLON = ";"
COMMA = ","
LBRACE = "{"
RBRACE = "}"
LBRACKET = "["
RBRACKET = "]"
LPAREN = "("
RPAREN = ")"
INT_VALUE = "INT_VALUE"
FLOAT_VALUE = "FLOAT_VALUE"
BOOL_VALUE = "BOOL_VALUE"
IDENTIFIER = "IDENTIFIER"
OP_ADD = "+"
OP_SUB = "-"
OP_MULT = "*"
OP_DIV = "/"
OP_MOD = "%"
OP_POW = "^"
OP_EQ = "=="
OP_NEQ = "!="
OP_GT = ">"
OP_GE = ">="
OP_LT = "<"
OP_LE = "<="
OP_AND = "&&"
OP_OR = "||"
OP_NEG = "!"
PRINT = "print"
LET = "let"
IF = "if"
ELSE = "else"
WHILE = "while"
FUNC = "func"
RETURN = "return"
STRING = "STRING_VALUE"
