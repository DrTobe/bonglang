import token_def as token
import ast
import symbol_table
import environment
import evaluator # Required for access to the builtin variables
import sys # To print on stderr
import bongtypes
import typing

class Parser:
    def __init__(self, lexer, symtable=None, functions=None):
        self.lexer = lexer
        self.init_token_access()
        if symtable == None:
            self.symbol_table = symbol_table.SymbolTable()
        else:
            self.symbol_table = symtable
        for key in evaluator.Eval.BUILTIN_ENVIRONMENT:
            if key not in self.symbol_table.names:
                self.symbol_table.register(key)
        if functions == None:
            self.functions : environment.Environment= environment.Environment()
        else:
            self.functions = functions

    def compile(self) -> ast.Program:
        statements = []
        try:
            while self.peek().type != token.EOF:
                stmt = self.top_level_stmt()
                if stmt != None:
                    statements.append(stmt)
        except ParseException as e:
            statements = [] # In case of syntax error, nothing should be executed
            t = self.peek(e.offset)
            if t.lexeme != None:
                lexeme = t.lexeme
            else:
                lexeme = t.type
            print("ParseError: Token '{}' found in {}, line {}, column {}: {}".format(lexeme, t.filepath, t.line, t.col, e.msg), file=sys.stderr) # t.length unused
        return ast.Program(statements, self.functions)

    def top_level_stmt(self) -> typing.Optional[ast.BaseNode]:
        if self.peek().type == token.FUNC:
            self.parse_function_definition()
            return None
        return self.stmt()

    def stmt(self) -> ast.BaseNode:
        if self.peek().type == token.PRINT:
            return self.print_stmt()
        if self.peek().type == token.LET:
            return self.let_stmt()
        if self.peek().type == token.IF:
            return self.if_stmt()
        if self.peek().type == token.RETURN:
            return self.return_stmt()
        if self.peek().type == token.WHILE:
            return self.while_stmt()
        if self.peek().type == token.LBRACE:
            return self.block_stmt()
        if (self.peek().type == token.IDENTIFIER or
                self.peek().type == token.INT_VALUE or
                self.peek().type == token.FLOAT_VALUE or
                self.peek().type == token.BOOL_VALUE or
                self.peek().type == token.LPAREN or
                self.peek().type == token.OP_SUB or
                self.peek().type == token.OP_NEG or
                self.peek().type == token.LBRACKET or
                self.peek().type == token.STRING):
            return self.expression_stmt()
        # Special cases: Syscalls in current directory like './foo' or with
        # absolute path like '/foo/bar'
        if (self.peek(0).type==token.OP_DIV and
                self.peek(1).type==token.IDENTIFIER or
                self.peek(0).type==token.DOT and
                self.peek(1).type==token.OP_DIV or
                self.peek(0).type==token.DOT and
                self.peek(1).type==token.DOT and
                self.peek(2).type==token.OP_DIV):
            return self.expression_stmt()
        raise ParseException("Unknown statement found.")

    def parse_function_definition(self) -> None:
        if not self.match(token.FUNC):
            raise Exception("Expected function definition.")

        if not self.match(token.IDENTIFIER):
            raise ParseException("Expected function name.")

        name = self.peek(-1).lexeme
        if self.symbol_table.exists(name):
            raise ParseException("Name '{}' already exists in symbol table. Function definition impossible.".format(name))
        if not self.match(token.LPAREN):
            raise ParseException("Expected ( to start the parameter list.")

        parameters = self.parse_parameters()

        if not self.match(token.RPAREN):
            raise ParseException("Expected ) to end the parameter list.")

        if not self.peek().type == token.LBRACE:
            raise ParseException("Expected function body.")

        original_symbol_table = self.symbol_table
        func_symbol_table = symbol_table.SymbolTable()
        self.symbol_table = func_symbol_table
        for param in parameters:
            self.symbol_table.register(param)
        body = self.block_stmt()
        self.symbol_table = original_symbol_table
        func = ast.FunctionDefinition(name, parameters, body, func_symbol_table)
        self.functions.register(name)
        self.functions.set(name, func)
        original_symbol_table.register(name)
        original_symbol_table[name].typ = bongtypes.Function()
        return None # function definition is in the symbol table, so we don't need to return it

    def parse_parameters(self) -> typing.List[str]:
        params : typing.List[str]= []
        self.check_eof("Parameter list expected")
        p = self.peek()
        if not self.match(token.IDENTIFIER):
            return params
        params.append(p.lexeme)
        while self.match(token.COMMA):
            self.check_eof("Another parameter expected")
            p = self.peek()
            if not self.match(token.IDENTIFIER):
                raise ParseException("Expected identifier as parameter.")
            params.append(p.lexeme)
        return params

    def return_stmt(self) -> ast.Return:
        if not self.match(token.RETURN):
            raise Exception("Expected return statement.")
        if self.match(token.SEMICOLON):
            return ast.Return()
        expr = self.expression()
        self.match(token.SEMICOLON)
        return ast.Return(expr)

    def expression_stmt(self) -> ast.BaseNode:
        expr = self.assignment()
        self.match(token.SEMICOLON)
        return expr

    def let_stmt(self) -> ast.Let:
        names : typing.List[str] = self.let_lhs()
        try:
            if not self.match(token.ASSIGN):
                raise ParseException("Empty let statements are not supported. Always assign a value!")
            expr : ast.BaseNode = self.assignment()
        # TODO The following cleans up if parsing this let statement fails
        # but nevertheless, we can end up in errors when an evaluation error
        # or a typecheck error occurs. So, we need a different approach for
        # cleaning up the parser's internal state after subsequent errors.
        except ParseException as e:
            for name in names:
                self.symbol_table.remove(name)
            raise
        self.match(token.SEMICOLON)
        return ast.Let(names, expr)
    # splitted so that this part can be reused for pipelines
    def let_lhs(self) -> typing.List[str]:
        if not self.match(token.LET):
            raise Exception("Expected let statement.")
        if not self.match(token.IDENTIFIER):
            raise ParseException("At least one identifier must be specified.")
        names = [self.peek(-1).lexeme]
        while self.match(token.COMMA):
            self.check_eof("Another identifier expected.")
            if not self.match(token.IDENTIFIER):
                raise ParseException("Another identifier expected.")
            names.append(self.peek(-1).lexeme)
        for name in names:
            if self.symbol_table.exists(name):
                raise ParseException("Name '{}' already exists in symbol table. Let statement impossible.".format(name))
            self.symbol_table.register(name)
        return names

    def if_stmt(self) -> ast.IfElseStatement:
        if not self.match(token.IF):
            raise Exception("Expected if.")
        cond = self.expression()
        t = self.block_stmt()
        e : typing.Union[None, ast.Block, ast.IfElseStatement] = None
        if self.match(token.ELSE):
            if self.peek().type == token.IF:
                e = self.if_stmt()
            else:
                e = self.block_stmt()
        return ast.IfElseStatement(cond, t, e)

    def while_stmt(self) -> ast.WhileStatement:
        if not self.match(token.WHILE):
            raise Exception("Expected while.")
        cond = self.expression()
        t = self.block_stmt()
        return ast.WhileStatement(cond, t)

    def print_stmt(self) -> ast.Print:
        if not self.match(token.PRINT):
            raise Exception("Expected print statement.")
        res = ast.Print(self.expression())
        self.match(token.SEMICOLON)
        return res

    def block_stmt(self) -> ast.Block:
        self.check_eof("Expected { for block statement.")
        if not self.match(token.LBRACE):
            raise ParseException("Expected { for block statement.")
        block_symbol_table = symbol_table.SymbolTable(self.symbol_table)
        self.symbol_table = block_symbol_table
        statements = []
        while self.peek().type != token.RBRACE:
            self.check_eof("Expected statement for block body.")
            statements.append(self.stmt())
        self.check_eof("missing } for block statement")
        if not self.match(token.RBRACE):
            raise ParseException("Missing } for block statement.")
        self.symbol_table = self.symbol_table.parent
        return ast.Block(statements, block_symbol_table)

    def assignment(self) -> ast.BaseNode:
        lhs : ast.BaseNode = ast.ExpressionList(self.parse_commata_expressions())
        if self.match(token.ASSIGN):
            rhs = self.assignment()
            lhs = ast.BinOp(lhs, "=", rhs)
        return lhs

    def expression(self) -> ast.BaseNode:
        return self.parse_or()

    def parse_or(self) -> ast.BaseNode:
        lhs = self.parse_and()
        while self.match(token.OP_OR):
            lhs = ast.BinOp(lhs, "||", self.parse_and())
        return lhs

    def parse_and(self) -> ast.BaseNode:
        lhs = self.parse_not()
        while self.match(token.OP_AND):
            lhs = ast.BinOp(lhs, "&&", self.parse_not())
        return lhs

    def parse_not(self) -> ast.BaseNode:
        if self.match(token.OP_NEG):
            return ast.UnaryOp("!", self.parse_not())
        return self.compare()

    def compare(self) -> ast.BaseNode:
        lhs = self.parse_pipeline()
        while self.match([token.OP_EQ, token.OP_NEQ, token.OP_GT, token.OP_GE, token.OP_LT, token.OP_LE]):
            prev = self.peek(-1)
            rhs = self.parse_pipeline()
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
                raise Exception("Assertion failed \"== > < !=\".")
            lhs = ast.BinOp(lhs, op, rhs)
        return lhs

    def parse_pipeline(self) -> ast.BaseNode:
        leftmost = self.addition()
        if not self.peek().type==token.BONG:
            return leftmost
        # Pipelines consist of:
        # a) stdin for the first syscall (string or string-variable)
        # b) syscalls
        # c) stdout[,stderr] for the last syscall (pipelinelet, expressionlist)
        #PipelinePart = typing.Union[ast.String, ast.Variable, ast.SysCall, ast.PipelineLet, ast.ExpressionList]
        # Unfortunately, this can not be guaranteed here because leftmost is
        # ast.BaseNode :( should we do type-checking here?
        #elements : typing.List[PipelinePart] = [leftmost]
        elements : typing.List[ast.BaseNode] = [leftmost]
        while self.match(token.BONG):
            if self.peek().type == token.LET:
                names = self.let_lhs()
                elements.append(ast.PipelineLet(names))
            elif (self.peek().type == token.IDENTIFIER and
                    self.peek(1).type == token.COMMA):
                # Like this, we can not have more "complicated" variables
                # (index-access or whatever) that we want to assign to.
                elements.append(ast.ExpressionList(self.parse_commata_expressions()))
            else:
                elements.append(self.addition())
        pipeline = ast.Pipeline(elements, False)
        if self.match(token.AMPERSAND):
            pipeline.nonblocking = True
        #if not self.match(token.SEMICOLON):
            #raise ParseException("A pipeline should end a line!")
        return pipeline

    def addition(self) -> ast.BaseNode:
        lhs = self.multiplication()
        while self.match([token.OP_ADD, token.OP_SUB]):
            prev = self.peek(-1)
            rhs = self.multiplication()
            if prev.type == token.OP_ADD:
                op = "+"
            elif prev.type == token.OP_SUB:
                op = "-"
            else:
                raise Exception("Assertion failed: \"+-\".")
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
                raise Exception("Assertion failed: */%")
            lhs = ast.BinOp(lhs, op, rhs)
        return lhs

    def signed(self):
        if self.match(token.OP_SUB):
            return ast.UnaryOp("-", self.exponentiation())
        if self.match(token.OP_ADD):
            pass # return self.exponentiation()
        return self.exponentiation()

    def exponentiation(self):
        lhs = self.index_access()
        if self.match(token.OP_POW):
            rhs = self.exponentiation()
            lhs = ast.BinOp(lhs, "^", rhs)
        return lhs

    def index_access(self):
        lhs = self.primary()
        if self.match(token.LBRACKET):
            self.check_eof("Missing expression for indexing.")
            rhs = self.expression()
            if not self.match(token.RBRACKET):
                raise ParseException("Missing ] for indexing.")
            lhs = ast.IndexAccess(lhs, rhs)
        return lhs

    def primary(self):
        if self.match(token.INT_VALUE):
            return ast.Integer(int(self.peek(-1).lexeme))
        if self.match(token.FLOAT_VALUE):
            return ast.Float(float(self.peek(-1).lexeme))
        if self.match(token.STRING):
            return ast.String(str(self.peek(-1).lexeme))
        if self.match(token.BOOL_VALUE):
            return ast.Bool(True if self.peek(-1).lexeme=="true" else False)
        if self.match(token.IDENTIFIER):
            if self.match(token.LPAREN):
                func_name = self.peek(-2).lexeme
                arguments = self.parse_arguments()
                if not self.match(token.RPAREN):
                    raise ParseException("Missing ) on function call.")
                return ast.FunctionCall(func_name, arguments)
            if self.symbol_table.exists(self.peek(-1).lexeme):
                return ast.Variable(self.peek(-1).lexeme)
            name = self.peek(-1).lexeme
            args = self.syscall_arguments(name)
            return ast.SysCall(args)
        # Special case: Syscall with './foo'
        if self.peek(0).type==token.DOT and self.peek(1).type==token.OP_DIV:
            # The DOT token could be preceded by whitespace which would cause
            # syscall_arguments() to have "" as the first argument of the
            # syscall if called without the following line and with
            # syscall_arguments("") instead.
            dot = self.next()
            args = self.syscall_arguments(".")
            return ast.SysCall(args)
        # Special case: Syscall with '../foo'
        if self.peek(0).type==token.DOT and self.peek(1).type==token.DOT and self.peek(2).type==token.OP_DIV:
            firstdot = self.next()
            args = self.syscall_arguments(".")
            return ast.SysCall(args)
        # Special case: Syscall with absolute path like '/foo/bar'
        if self.peek(0).type==token.OP_DIV and self.peek(1).type==token.IDENTIFIER:
            slash = self.next()
            args = self.syscall_arguments("/")
            return ast.SysCall(args)
        if self.match(token.LPAREN):
            exp = self.expression()
            if not self.match(token.RPAREN):
                raise ParseException("Missing closing parenthesis ).")
            return exp
        if self.match(token.LBRACKET):
            if self.match(token.RBRACKET):
                return ast.Array([])
            elements = self.parse_commata_expressions()
            if not self.match(token.RBRACKET):
                raise ParseException("Expected ].")
            return ast.Array(elements)
        raise ParseException("Integer or () expected.")

    def parse_arguments(self):
        if self.peek().type == token.RPAREN:
            return []
        return self.parse_commata_expressions()

    def parse_commata_expressions(self) -> typing.List[ast.BaseNode]:
        elements = []
        elements.append(self.expression())
        while self.match(token.COMMA):
            elements.append(self.expression())
        return elements

    def syscall_arguments(self, name):
        #valid = [token.OP_SUB, token.OP_DIV, token.OP_MULT, token.OP
        # TODO complete list of invalid tokens (which finish syscall args)
        invalid = [token.BONG, token.AMPERSAND, token.SEMICOLON, token.LBRACE, token.OP_EQ, token.RPAREN, token.EOF]
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
            if c.type in [token.IDENTIFIER, token.INT_VALUE, token.FLOAT_VALUE, token.BOOL_VALUE, token.STRING, token.OTHER]:
                arg += c.lexeme
            else:
                arg += c.type
        arguments.append(arg)
        self.match(token.SEMICOLON) # match away a possible semicolon
        return arguments

    # The check_eof() method is used whenever we could expect the (current)
    # input to end before (complete) parsing was successful which happens
    # in the REPL with multiline input. Then, an UnexpectedEof Exception is
    # raised which can be caught by the REPL to retry with more input.
    def check_eof(self, msg):
        if self.peek().type == token.EOF:
            raise UnexpectedEof(msg)

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
                raise Exception("Looking ahead too far!")
            return self.next_tokens[steps]
        else:
            steps = -1*steps - 1
            if steps >= Parser.BACK:
                raise Exception("Looking back too far!")
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

# Custom exception for parser errors.
# The (negative) offset is used to specify which token (in the past) describes
# the error position best.
class ParseException(Exception):
    def __init__(self, msg, offset=0):
        super().__init__(self, msg)
        self.msg = msg
        self.offset = offset
    def __str__(self):
        return super().__str__()

# Exception that tells us that EOF was found in a situation where we did
# not expect it. This is used advantageous for multi-line statements
# in the REPL.
class UnexpectedEof(Exception):
    pass
