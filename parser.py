import token_def as token
import ast
import symbol_table

class Parser:
    def __init__(self, lexer, symtable=None):
        self.lexer = lexer
        self.init_token_access()
        self.symbol_table = symtable
        if symtable == None:
            self.symbol_table = symbol_table.SymbolTable()

    def compile(self):
        statements = []
        while self.peek().type != token.EOF:
            statements.append(self.stmt())
        return ast.Block(statements, self.symbol_table)

    def stmt(self):
        if self.peek().type == token.PRINT:
            return self.print_stmt()
        if self.peek().type == token.LET:
            return self.let_stmt()
        if self.peek().type == token.IF:
            return self.if_stmt()
        if self.peek().type == token.WHILE:
            return self.while_stmt()
        if self.peek().type == token.LBRACE:
            return self.block_stmt()
        if self.peek().type == token.IDENTIFIER or self.peek().type == token.INT_VALUE or self.peek().type == token.BOOL_VALUE or self.peek().type == token.LPAREN or self.peek().type == token.OP_SUB or self.peek().type == token.OP_NEG:
            return self.expression_stmt()
        raise(Exception("unknown statement found: {}".format(str(self.peek()))))

    def expression_stmt(self):
        expr = self.expression()
        self.match(token.SEMICOLON)
        return expr

    def let_stmt(self):
        if not self.match(token.LET):
            raise Exception("expected print statement")
        if not self.match(token.IDENTIFIER):
            raise Exception("FUCK")
        name = self.peek(-1).lexeme
        # TODO optional: check if already registered
        self.symbol_table.register(name)
        if not self.match(token.ASSIGN):
            raise Exception("FUCK2")
        expr = self.expression()
        self.match(token.SEMICOLON)
        return ast.Let(name, expr)

    def if_stmt(self):
        if not self.match(token.IF):
            raise Exception("expected if")
        cond = self.expression()
        t = self.block_stmt()
        e = None
        if self.match(token.ELSE):
            if self.peek().type == token.IF:
                e = self.if_stmt()
            else:
                e = self.block_stmt()
        return ast.IfElseStatement(cond, t, e)

    def while_stmt(self):
        if not self.match(token.WHILE):
            raise(Exception("expected while"))
        cond = self.expression()
        t = self.block_stmt()
        return ast.WhileStatement(cond, t)

    def print_stmt(self):
        if not self.match(token.PRINT):
            raise(Exception("expected print statement"))
        res = ast.Print(self.expression())
        self.match(token.SEMICOLON)
        return res

    def block_stmt(self):
        if not self.match(token.LBRACE):
            raise(Exception("expected { for block statement"))
        block_symbol_table = symbol_table.SymbolTable(self.symbol_table)
        self.symbol_table = block_symbol_table
        statements = []
        while self.peek().type != token.RBRACE:
            statements.append(self.stmt())
        if not self.match(token.RBRACE):
            raise(Exception("missing } for block statement"))
        self.symbol_table = self.symbol_table.parent
        return ast.Block(statements, block_symbol_table)

    def expression(self):
        return self.assignment()

    def assignment(self):
        lhs = self.parse_or()
        if self.match(token.ASSIGN):
            rhs = self.assignment()
            lhs = ast.BinOp(lhs, "=", rhs)
        return lhs

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
            if self.symbol_table.exists(self.peek(-1).lexeme):
                return ast.Variable(self.peek(-1).lexeme)
            name = self.peek(-1).lexeme
            args = self.syscall_arguments(name)
            return ast.SysCall(args)
        if self.match(token.LPAREN):
            exp = self.expression()
            if not self.match(token.RPAREN):
                raise Exception("missing closing parenthesis )")
            return exp
        raise Exception("integer or () expected")

    def syscall_arguments(self, name):
        #valid = [token.OP_SUB, token.OP_DIV, token.OP_MULT, token.OP
        # TODO complete list of invalid tokens (which finish syscall args)
        invalid = [token.BONG, token.SEMICOLON, token.EOF, token.ERR]
        arguments = []
        arg = name
        while self.peek().type not in invalid:
            c = self.next()
            # if whitespace is found, this goes to the next arg
            if c.prec_by_space:
                arguments.append(arg)
                arg = ""
            # for valid tokens, translate 
            # only for int_value, bool_value, identifier, we have to use the lexeme
            # otherwise, the type is equivalent to what was matched before (which is what we want to restore here)
            if c.type in [token.IDENTIFIER, token.INT_VALUE, token.BOOL_VALUE]:
                arg += c.lexeme
            else:
                arg += c.type
        arguments.append(arg)
        self.match(token.SEMICOLON) # match away a possible semicolon
        return arguments

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

    # TODO Lexer generates whitespace tokens; here, implement a method that
    # allows for checking if the next token is whitespace, skip whitespace
    # tokens in peek; next and match rely on peek
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

