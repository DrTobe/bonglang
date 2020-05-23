import token_def as token
from token_def import Token
import eof_exception

class Lexer:
    def __init__(self, code, filepath):
        self.code = code
        self.current_pos = 0
        self.last_token = None
        self.had_whitespace = False
        # Fields for reporting (error) positions
        # For line and col we use an ever-growing list that lets us look
        # back in time
        self.filepath = filepath
        self.line = [1]
        self.col = [1]

    def create_token(self, typ, length=1, lexeme=None):
        # The ever-growing lits in the past is [current, previous, ...]
        # The last character that was part of the token we currently generate
        # was just "matched-away" or removed with next(). Thus, for length==1,
        # we do not need index 0 but index 1 instead.
        line = self.line[length]
        col = self.col[length]
        # DEBUG: Print what kinds of tokens are generated
        #print(typ, self.filepath, line, col, length, lexeme)
        self.last_token = Token(typ, self.filepath, line, col, length, self.had_whitespace, lexeme)
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
        if c == ":":
            return self.create_token(token.COLON)
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
                return self.create_token(token.OP_EQ, 2)
            return self.create_token(token.ASSIGN)
        if c == "!":
            if self.match("="):
                return self.create_token(token.OP_NEQ, 2)
            return self.create_token(token.OP_NEG)
        if c == "<":
            if self.match("="):
                return self.create_token(token.OP_LE, 2)
            return self.create_token(token.OP_LT)
        if c == ">":
            if self.match("="):
                return self.create_token(token.OP_GE, 2)
            return self.create_token(token.OP_GT)
        if c == "&":
            if self.match("&"):
                return self.create_token(token.OP_AND, 2)
            return self.create_token(token.AMPERSAND)
        if c == "|":
            if self.match("|"):
                return self.create_token(token.OP_OR, 2)
            return self.create_token(token.BONG)
        if is_number(c):
            lex = c
            while is_number(self.peek()):
                lex += self.next()
            if self.peek()=="." and is_number(self.peek(1)):
                lex += self.next() # == "."
                while is_number(self.peek()):
                    lex += self.next()
                return self.create_token(token.FLOAT_VALUE, len(lex), lex)
            return self.create_token(token.INT_VALUE, len(lex), lex)
        if is_alpha(c):
            lex = c
            while is_alpha(self.peek()) or self.peek()=="_":
                lex += self.next()
            if lex == "print":
                return self.create_token(token.PRINT, len(lex), lex)
            if lex == "true" or lex == "false":
                return self.create_token(token.BOOL_VALUE, len(lex), lex)
            if lex == "let":
                return self.create_token(token.LET, len(lex), lex)
            if lex == "if":
                return self.create_token(token.IF, len(lex), lex)
            if lex == "else":
                return self.create_token(token.ELSE, len(lex), lex)
            if lex == "while":
                return self.create_token(token.WHILE, len(lex), lex)
            if lex == "func":
                return self.create_token(token.FUNC, len(lex), lex)
            if lex == "return":
                return self.create_token(token.RETURN, len(lex), lex)
            if lex == "import":
                return self.create_token(token.IMPORT, len(lex), lex)
            if lex == "as":
                return self.create_token(token.AS, len(lex), lex)
            if lex == "struct":
                return self.create_token(token.STRUCT, len(lex), lex)
            return self.create_token(token.IDENTIFIER, len(lex), lex)
        if "\"" == c: # begin of a string
            lex = ""
            token_len = 0
            while not self.match("\""):
                def nextChar():
                    char = self.next()
                    nonlocal token_len # https://stackoverflow.com/a/11987499
                    token_len += 1
                    if char == "":
                        raise eof_exception.UnexpectedEof("Unfinished String.")
                    return char
                char = nextChar()
                if char == "\\": # begin escape sequence
                    char = nextChar()
                    if char == "\\":
                        lex += "\\"
                    elif char == "\"":
                        lex += "\""
                    elif char == "0":
                        lex += chr(0)
                    elif char == "n":
                        lex += "\n"
                    elif char == "r":
                        lex += "\r"
                    elif char == "t":
                        lex += "\t"
                    elif char == "x":
                        high = nextChar()
                        low = nextChar()
                        try:
                            val = int(high+low, 16)
                        except ValueError as e:
                            self.raise_token_exception("Escape sequence \\x"
                                    " requires exactly two digits between"
                                    f" 0 and F/f, '{high+low}' found instead.", 4)
                        if val < 0 or val > 127:
                            self.raise_token_exception("Escape sequence \\x"
                                    " must evaluate to a value between 0 and"
                                    f" 127, {val} was calculated instead.", 4)
                        lex += chr(val)
                    elif char == "u":
                        char = nextChar()
                        if char != "{":
                            self.raise_token_exception("Escape sequence"
                                    " \\u{...} expects an opening brace,"
                                    f" '{char}' found instead", 3)
                        unic = ""
                        char = nextChar()
                        while char != "}":
                            unic += char
                            if len(unic) > 6:
                                self.raise_token_exception("Escape sequence"
                                        " \\u{...} expects at most 6 digits.",
                                        10) # len = \u{ + 7
                            char = nextChar()
                        try:
                            val = int(unic, 16)
                        except ValueError as e:
                            self.raise_token_exception("Escape sequence \\u{...}"
                                    " requires only digits between"
                                    f" 0 and F/f, '{unic}' found instead.", 4+len(unic))
                        if val < 0 or val > 0x10FFFF:
                            self.raise_token_exception("Escape sequence \\u{...}"
                                    " must evaluate to a value between 0 and"
                                    f" 0x10FFFF, {hex(val)} was calculated instead.", 4+len(unic))
                        lex += chr(val)
                else:
                    lex += char
            return self.create_token(token.STRING, token_len+2, lex)
        else:
            return self.create_token(token.OTHER, 1, c)

    def peek(self, steps=0):
        pos = self.current_pos + steps
        return self.code[pos] if pos < len(self.code) else ""

    def next(self):
        c = self.peek()
        self.current_pos += 1
        if is_newline(c):
            newline = self.line[0]+1
            newcol = 1
        else:
            newline = self.line[0]
            newcol = self.col[0]+1
        self.line = [newline] + self.line
        self.col = [newcol] + self.col
        return c

    def match(self, compare):
        c = self.peek()
        if c == compare:
            self.next()
            return True
        return False

    def raise_token_exception(self, msg, length):
        line = self.line[length]
        col = self.col[length]
        raise TokenizeException(msg, self.filepath, line, col, length)

def is_number(arg):
    return arg >= "0" and arg <= "9"

def is_alpha(arg):
    return (arg >= "a" and arg <= "z") or (arg >= "A" and arg <= "Z")

def is_whitespace(arg):
    return arg == " " or arg == "\t" or arg == "\n" or arg == "\r"

def is_newline(arg):
    return arg == "\r" or arg == "\n"

# Custom exception for lexer errors.
# The (negative) offset is used to specify which token (in the past) describes
# the error position best.
class TokenizeException(Exception):
    def __init__(self, msg, filepath, line, col, length):
        super().__init__(self, msg)
        self.msg = msg
        self.filepath = filepath
        self.line = line
        self.col = col
        self.length = length
    def __str__(self):
        return super().__str__()
