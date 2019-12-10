import token_def as token
from token_def import Token

class Lexer:
    def __init__(self, code):
        self.code = code
        self.current_pos = 0

    def get_token(self):
        c = self.next()
        while c!="" and is_whitespace(c):
            c = self.next()
        if c == "": # EOF
            return Token(token.EOF)
        """
        if is_newline(c): # newlines
            while self.peek()!="" and is_newline(self.peek()):
                self.next()
            return Token(token.EOL)
        """
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
        if c == "+":
            return Token(token.OP_ADD)
        if c == "-":
            return Token(token.OP_SUB)
        if c == "*":
            return Token(token.OP_MULT)
        if c == "/":
            return Token(token.OP_DIV)
        if c == "%":
            return Token(token.OP_MOD)
        if c == "^":
            return Token(token.OP_POW)
        if c == "(":
            return Token(token.LPAREN)
        if c == ")":
            return Token(token.RPAREN)
        if c == "=":
            if self.match("="):
                return Token(token.OP_EQ)
            return Token(token.ASSIGN)
        if c == "!":
            if self.match("="):
                return Token(token.OP_NEQ)
            return Token(token.OP_NEG)
        if c == "<":
            if self.match("="):
                return Token(token.OP_LE)
            return Token(token.OP_LT)
        if c == ">":
            if self.match("="):
                return Token(token.OP_GE)
            return Token(token.OP_GT)
        if c == "&":
            if self.match("&"):
                return Token(token.OP_AND)
            raise Exception("single & not supported (yet?)")
        if c == "|":
            if self.match("|"):
                return Token(token.OP_OR)
            return Token(token.BONG)
        if is_number(c):
            lex = c
            while is_number(self.peek()):
                lex += self.next()
            return Token(token.INT_VALUE, lex)
        if is_alpha(c):
            lex = c
            while is_alpha(self.peek()):
                lex += self.next()
            if lex == "print":
                return Token(token.PRINT)
            if lex == "true" or lex == "false":
                return Token(token.BOOL_VALUE, lex)
            if lex == "let":
                return Token(token.LET)
            """
            replaced by dictionary in the future
            if lex == "if":
                return Token(token.IF)
            """
            return Token(token.IDENTIFIER, lex)
        else:
            return Token(token.ERR, "unrecognized character ("+c+")")

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
