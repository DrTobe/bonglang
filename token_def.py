class Token:
    def __init__(self, typ, lexeme = None):
        self.type = typ
        self.lexeme = lexeme
    def __str__(self):
        if self.lexeme != None:
            return self.type + "(" + str(self.lexeme) + ")"
        return self.type

BONG = "|"
ERR = "ERROR"
EOF = "EOF"
ASSIGN = "="
SEMICOLON = ";"
LBRACE = "{"
RBRACE = "}"
LBRACKET = "["
RBRACKET = "]"
LPAREN = "("
RPAREN = ")"
INT_VALUE = "INT_VALUE"
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
PRINT = "PRINT"
LET = "let"
IF = "if"
ELSE = "else"
WHILE = "while"
