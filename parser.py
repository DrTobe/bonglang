import token_def as token
import ast

class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.init_token_access()

    def compile(self):
        if self.peek().type == token.PRINT:
            return self.print_stmt()
        if self.peek().type == token.LET:
            return self.let_stmt()
        if self.peek().type == token.IDENTIFIER: # here, everything can happen
            if self.peek(1).type == token.ASSIGN:
                self.assignment() # TODO
        if self.peek().type == token.IDENTIFIER or self.peek().type == token.INT_VALUE or self.peek().type == token.BOOL_VALUE or self.peek().type == token.LPAREN or self.peek().type == token.OP_SUB or self.peek().type == token.OP_NEG:
            return self.expression()
        if not self.match(token.EOF):
            raise(Exception("unparsed tokens left: " + str(self.peek())))

    def let_stmt(self):
        if not self.match(token.LET):
            raise Exception("expected print statement")
        if not self.match(token.IDENTIFIER):
            raise Exception("FUCK")
        name = self.peek(-1).lexeme
        if not self.match(token.ASSIGN):
            raise Exception("FUCK2")
        expr = self.expression()
        return ast.Let(name, expr)

    def print_stmt(self):
        if not self.match(token.PRINT):
            raise(Exception("expected print statement"))
        res = ast.Print(self.expression())
        return res

    def assignment(self):
        raise(Exception("assignments not implemented yet"))

    def expression(self):
        return self.parse_or()

    def parse_or(self):
        lhs = self.parse_and()
        while self.match(token.OP_OR):
            lhs = ast.BinOp(lhs, "||", self.parse_and())
        return lhs

    def parse_and(self):
        lhs = self.parse_not()
        while self.match(token.OP_AND):
            lhs = ast.BinOp(lhs, "&&", self.parse_not())
        return lhs
    
    def parse_not(self):
        if self.match(token.OP_NEG):
            return ast.UnaryOp("!", self.parse_not())
        return self.compare()

    def compare(self):
        lhs = self.addition()
        while self.match([token.OP_EQ, token.OP_NEQ, token.OP_GT, token.OP_GE, token.OP_LT, token.OP_LE]):
            prev = self.peek(-1)
            rhs = self.addition()
            if prev.type == token.OP_EQ:
                op = "=="
            elif prev.type == token.OP_NEQ:
                op = "!="
            elif prev.type == token.OP_GT:
                op = ">"
            elif prev.type == token.OP_GE:
                op = ">="
            elif prev.type == token.OP_LT:
                op = "<"
            elif prev.type == token.OP_LE:
                op = "<="
            else:
                raise Exception("assertion failed == > < !=")
            lhs = ast.BinOp(lhs, op, rhs)
        return lhs

    def addition(self):
        lhs = self.multiplication()
        while self.match([token.OP_ADD, token.OP_SUB]):
            prev = self.peek(-1)
            rhs = self.multiplication()
            if prev.type == token.OP_ADD:
                op = "+"
            elif prev.type == token.OP_SUB:
                op = "-"
            else:
                raise Exception("assertion failed: +-")
            lhs = ast.BinOp(lhs, op, rhs)
        return lhs

    def multiplication(self):
        lhs = self.signed()
        while self.match([token.OP_MULT, token.OP_DIV, token.OP_MOD]):
            prev = self.peek(-1)
            rhs = self.signed()
            if prev.type == token.OP_MULT:
                op = "*"
            elif prev.type == token.OP_DIV:
                op = "/"
            elif prev.type == token.OP_MOD:
                op = "%"
            else:
                raise Exception("assertion failed: */%")
            lhs = ast.BinOp(lhs, op, rhs)
        return lhs

    def signed(self):
        if self.match(token.OP_SUB):
            return ast.UnaryOp("-", self.exponentiation())
        if self.match(token.OP_ADD):
            pass # return self.exponentiation()
        return self.exponentiation()

    def exponentiation(self):
        lhs = self.primary()
        if self.match(token.OP_POW):
            rhs = self.exponentiation()
            lhs = ast.BinOp(lhs, "^", rhs)
        return lhs

    def primary(self):
        if self.match(token.INT_VALUE):
            return ast.Integer(int(self.peek(-1).lexeme))
        if self.match(token.BOOL_VALUE):
            return ast.Bool(True if self.peek(-1).lexeme=="true" else False)
        if self.match(token.IDENTIFIER):
            return ast.Variable(self.peek(-1).lexeme)
        if self.match(token.LPAREN):
            exp = self.expression()
            if not self.match(token.RPAREN):
                raise Exception("missing closing parenthesis )")
            return exp
        raise Exception("integer or () expected")

    # 
    # Token access methods
    # This is implemented with a list of tokens for the future / look ahead
    # and a list for the past / looking back
    #
    BACK = 3
    AHEAD = 5

    def init_token_access(self):
        self.past_tokens = [token.EOF] * Parser.BACK
        self.next_tokens = []
        for i in range(Parser.AHEAD):
            self.next_tokens.append(self.lexer.get_token())

    def peek(self, steps=0):
        if steps >= 0:
            if steps >= Parser.AHEAD:
                raise(Exception("Looking ahead too far!"))
            return self.next_tokens[steps]
        else:
            steps = -1*steps - 1
            if steps >= Parser.BACK:
                raise(Exception("Looking back too far!"))
            return self.past_tokens[steps]

    def next(self):
        t = self.peek()
        self.past_tokens = [self.next_tokens[0]] + self.past_tokens[:-1]
        self.next_tokens = self.next_tokens[1:] + [self.lexer.get_token()]
        return t

    def match(self, compare):
        typ = self.peek().type
        if not isinstance(compare, list):
            compare = [compare]
        for c in compare:
            if c == typ:
                self.next()
                return True
        return False

