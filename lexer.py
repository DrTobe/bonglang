import token_def as token
from token_def import Token

class Lexer:
    def __init__(self, code):
        self.code = code
        self.current_pos = 0
        self.last_token = None
        self.had_whitespace = False

    def create_token(self, typ, lexeme=None):
        self.last_token = Token(typ, self.had_whitespace, lexeme)
        self.had_whitespace = False
        return self.last_token

    def get_token(self):
        c = self.next()
        while c!="" and is_whitespace(c):
            # implicit semicolons
            if is_newline(c) and self.last_token != None and self.last_token.type in [
                    token.IDENTIFIER, token.INT_VALUE, token.BOOL_VALUE,
                    token.RPAREN, token.RBRACKET, token.STRING, token.RETURN
                    ]:
                return self.create_token(token.SEMICOLON)
            # squeeze multiple whitespaces together
            self.had_whitespace = True
            c = self.next()
        if c == "": # EOF
            return self.create_token(token.EOF)
        if c == "/": # comments
            if self.match("/"): # single-line comment starts
                while self.peek()!="" and not is_newline(self.peek()):
                    self.next() # remove everything until newline is found
                while self.peek()!="" and is_newline(self.peek()):
                    self.next() # for \r\n and \n\r, remove all newline chars
                return self.get_token()
            if self.match("*"): # multi-line comment
                commentlevel = 1
                while commentlevel > 0 and self.peek()!="":
                    c = self.next()
                    if c == "/" and self.match("*"):
                        commentlevel += 1
                    elif c == "*" and self.match("/"):
                        commentlevel -= 1
                return self.get_token()
        if c == ";":
            return self.create_token(token.SEMICOLON)
        if c == ",":
            return self.create_token(token.COMMA)
        if c == ".":
            return self.create_token(token.DOT)
        if c == "+":
            return self.create_token(token.OP_ADD)
        if c == "-":
            return self.create_token(token.OP_SUB)
        if c == "*":
            return self.create_token(token.OP_MULT)
        if c == "/":
            return self.create_token(token.OP_DIV)
        if c == "%":
            return self.create_token(token.OP_MOD)
        if c == "^":
            return self.create_token(token.OP_POW)
        if c == "(":
            return self.create_token(token.LPAREN)
        if c == ")":
            return self.create_token(token.RPAREN)
        if c == "{":
            return self.create_token(token.LBRACE)
        if c == "}":
            return self.create_token(token.RBRACE)
        if c == "[":
            return self.create_token(token.LBRACKET)
        if c == "]":
            return self.create_token(token.RBRACKET)
        if c == "=":
            if self.match("="):
                return self.create_token(token.OP_EQ)
            return self.create_token(token.ASSIGN)
        if c == "!":
            if self.match("="):
                return self.create_token(token.OP_NEQ)
            return self.create_token(token.OP_NEG)
        if c == "<":
            if self.match("="):
                return self.create_token(token.OP_LE)
            return self.create_token(token.OP_LT)
        if c == ">":
            if self.match("="):
                return self.create_token(token.OP_GE)
            return self.create_token(token.OP_GT)
        if c == "&":
            if self.match("&"):
                return self.create_token(token.OP_AND)
            raise Exception("single & not supported (yet?)")
        if c == "|":
            if self.match("|"):
                return self.create_token(token.OP_OR)
            return self.create_token(token.BONG)
        if is_number(c):
            lex = c
            while is_number(self.peek()):
                lex += self.next()
            return self.create_token(token.INT_VALUE, lex)
        if is_alpha(c):
            lex = c
            while is_alpha(self.peek()) or self.peek()=="_":
                lex += self.next()
            if lex == "print":
                return self.create_token(token.PRINT)
            if lex == "true" or lex == "false":
                return self.create_token(token.BOOL_VALUE, lex)
            if lex == "let":
                return self.create_token(token.LET)
            if lex == "if":
                return self.create_token(token.IF)
            if lex == "else":
                return self.create_token(token.ELSE)
            if lex == "while":
                return self.create_token(token.WHILE)
            if lex == "func":
                return self.create_token(token.FUNC)
            if lex == "return":
                return self.create_token(token.RETURN)
            return self.create_token(token.IDENTIFIER, lex)
        if "\"" == c: # begin of a string
            lex = ""
            while not self.match("\""):
                lex += self.next()
            return self.create_token(token.STRING, lex)
        else:
            return self.create_token(token.ERR, "unrecognized character ("+c+")")

    def peek(self):
        return self.code[self.current_pos] if self.current_pos < len(self.code) else ""

    def next(self):
        c = self.peek()
        self.current_pos += 1
        return c

    def match(self, compare):
        c = self.peek()
        if c == compare:
            self.next()
            return True
        return False

def is_number(arg):
    return arg >= "0" and arg <= "9"

def is_alpha(arg):
    return (arg >= "a" and arg <= "z") or (arg >= "A" and arg <= "Z")

def is_whitespace(arg):
    return arg == " " or arg == "\t" or arg == "\n" or arg == "\r"

def is_newline(arg):
    return arg == "\r" or arg == "\n"
