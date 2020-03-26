import token_def as token
import ast
import symbol_table
import evaluator # Required for access to the builtin variables
import sys # To print on stderr
import bongtypes
import typing
import os
import bong_builtins

class Parser:
    def __init__(self, lexer, symtable=None, basepath=None):
        self.lexer = lexer
        self.init_token_access()

        self.basepath = basepath if basepath != None else os.getcwd()

        if symtable == None:
            self.symbol_table = symbol_table.SymbolTable()
        else:
            self.symbol_table = symtable
        for bfuncname, bfunc in bong_builtins.functions.items():
            if not self.symbol_table.exists(bfuncname): # For re-using symbol tables in shell mode
                self.symbol_table.register(bfuncname, bongtypes.BuiltinFunction(bfunc[1]))

    def compile(self) -> ast.Program:
        statements : typing.List[ast.BaseNode] = []
        try:
            while self.peek().type != token.EOF:
                statements.append(self.top_level_stmt())
        except ParseException as e:
            statements = [] # In case of syntax error, nothing should be executed
            t = self.peek(e.offset)
            if t.lexeme != None:
                lexeme = t.lexeme
            else:
                lexeme = t.type
            print("ParseError: Token '{}' found in {}, line {}, column {}: {}".format(lexeme, t.filepath, t.line, t.col, e.msg), file=sys.stderr) # t.length unused
        return ast.Program(statements, self.symbol_table)

    def top_level_stmt(self) -> ast.BaseNode:
        if self.peek().type == token.IMPORT:
            return self.parse_import()
        if self.peek().type == token.FUNC:
            return self.parse_function_definition()
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

    def parse_import(self):
        toks = TokenList()
        if not toks.add(self.match(token.IMPORT)):
            raise Exception("Expected import statement.")
        path = self.peek()
        if not toks.add(self.match(token.STRING)):
            raise Exception("Expected module path as string.")
        name = self.peek()
        if not toks.add(self.match(token.AS)):
            raise Exception("Expected as")
        if not toks.add(self.match(token.IDENTIFIER)):
            raise Exception("Expected module alias name.")
        toks.add(self.match(token.SEMICOLON))
        if not os.path.isabs(path.lexeme):
            path = os.path.join(self.basepath, path.lexeme)
        return ast.Import(toks, name.lexeme, path)

    def parse_function_definition(self) -> ast.FunctionDefinition:
        toks = TokenList()
        # FUNC foo (bar : int) : str { ... }
        if not toks.add(self.match(token.FUNC)):
            raise Exception("Expected function definition.")
        # func FOO (bar : int) : str { ... }
        if not toks.add(self.match(token.IDENTIFIER)):
            raise ParseException("Expected function name.")
        name = self.peek(-1).lexeme
        if self.symbol_table.exists(name):
            raise ParseException("Name '{}' already exists in symbol table. Function definition impossible.".format(name))
        # Register function name before parsing parameter names (no parameter name should have the function name!)
        self.symbol_table.register(name, bongtypes.UnknownType())
        try: # Everything after registering the name has to be caught to remove the name from symtable
            # (
            if not toks.add(self.match(token.LPAREN)):
                raise ParseException("Expected ( to start the parameter list.")
            # Parameters
            parameter_names, parameter_types = self.parse_parameters()
            # )
            if not toks.add(self.match(token.RPAREN)):
                raise ParseException("Expected ) to end the parameter list.")
            # Return types
            return_types : typing.List[bongtypes.BongtypeIdentifier] = []
            if toks.add(self.match(token.COLON)):
                self.check_eof("Return type list expected.")
                return_types.append(self.parse_type())
                while toks.add(self.match(token.COMMA)):
                    return_types.append(self.parse_type())
            # {
            if not self.peek().type == token.LBRACE:
                raise ParseException("Expected function body.")
            # Push/Pop symbol tables and parse statement block
            func_symbol_table = symbol_table.SymbolTable(self.symbol_table)
            self.symbol_table = func_symbol_table
            try:
                for param,typ in zip(parameter_names,parameter_types):
                    if self.symbol_table.exists(param):
                        raise ParseException("Argument name '{}' already exists in symbol table. Function definition impossible.".format(param))
                    # TODO custom types
                    self.symbol_table.register(param, typ.get_bongtype())
                body = self.block_stmt()
            finally:
                self.symbol_table = self.symbol_table.parent # pop
        except Exception as e:
            self.symbol_table.remove(name) # Remove function name from symtable in case of error
            raise
        # Register function in symbol table
        # TODO Currently, we do not have custom types yet. In the future,
        # the parser will only write UnknownType into the symbol table
        # and a later layer will resolve those types by passing the ast
        self.symbol_table[name].typ = bongtypes.Function(bongtypes.get_bongtypes(parameter_types), bongtypes.get_bongtypes(return_types))
        return ast.FunctionDefinition(toks, name, parameter_names, parameter_types, return_types, body, func_symbol_table)

    def parse_parameters(self) -> typing.Tuple[typing.List[str],typing.List[bongtypes.BongtypeIdentifier]]:
        parameter_names : typing.List[str] = []
        parameter_types : typing.List[bongtypes.BongtypeIdentifier] = []
        self.check_eof("Parameter list expected")
        if self.peek().type != token.IDENTIFIER:
            return (parameter_names, parameter_types)
        name, typ = self.parse_parameter()
        parameter_names.append(name)
        parameter_types.append(typ)
        while self.match(token.COMMA):
            name, typ = self.parse_parameter()
            parameter_names.append(name)
            parameter_types.append(typ)
        return (parameter_names, parameter_types)
    def parse_parameter(self) -> typing.Tuple[str,bongtypes.BongtypeIdentifier]:
        self.check_eof("Another parameter expected")
        if not self.match(token.IDENTIFIER):
            raise ParseException("Expected identifier as parameter name.")
        name = self.peek(-1).lexeme
        if not self.match(token.COLON):
            raise ParseException("Expected type hint for function parameter.")
        typ = self.parse_type()
        return (name, typ)
    # Used by function definition and let statement
    def parse_type(self) -> bongtypes.BongtypeIdentifier:
        num_array_levels = 0
        while self.match(token.LBRACKET):
            if not self.match(token.RBRACKET):
                raise ParseException("Expected closing bracket ']' in type specification.")
            num_array_levels += 1
        if not self.match(token.IDENTIFIER):
            raise ParseException("Expected identifier as type.")
        typename = self.peek(-1).lexeme
        return bongtypes.BongtypeIdentifier(typename, num_array_levels)

    def return_stmt(self) -> ast.Return:
        toks = TokenList()
        if not toks.add(self.match(token.RETURN)):
            raise Exception("Expected return statement.")
        if toks.add(self.match(token.SEMICOLON)):
            return ast.Return(toks)
        expr = self.parse_commata_expressions()
        toks.add(self.match(token.SEMICOLON))
        return ast.Return(toks, expr)

    def expression_stmt(self) -> ast.BaseNode:
        expr = self.assignment()
        if tok := self.match(token.SEMICOLON):
            expr.tokens.append(tok)
        return expr

    def let_stmt(self) -> ast.Let:
        toks = TokenList()
        toks.add(self.peek()) # Add 'let' token itself for correct begin
        names : typing.List[str] = self.let_lhs()
        try:
            if not toks.add(self.match(token.ASSIGN)):
                raise ParseException("Empty let statements are not supported. Always assign a value!")
            expr : typing.Union[ast.ExpressionList, ast.AssignOp] = self.assignment()
        # TODO The following cleans up if parsing this let statement fails
        # but nevertheless, we can end up in errors when an evaluation error
        # or a typecheck error occurs. So, we need a different approach for
        # cleaning up the parser's internal state after subsequent errors.
        except Exception as e:
            for name in names:
                self.symbol_table.remove(name)
            raise
        toks.add(self.match(token.SEMICOLON))
        return ast.Let(toks, names, expr)
    # splitted so that this part can be reused for pipelines
    def let_lhs(self) -> typing.List[str]:
        if not self.match(token.LET):
            raise Exception("Expected let statement.")
        # Parse variable names and types
        variable_names, variable_types = self.parse_let_variables()
        # Register names in symbol table
        for name,typ in zip(variable_names,variable_types):
            if self.symbol_table.exists(name):
                raise ParseException("Name '{}' already exists in symbol table. Let statement impossible.".format(name))
            bongtype = typ.get_bongtype() if isinstance(typ,bongtypes.BongtypeIdentifier) else bongtypes.AutoType()
            self.symbol_table.register(name, bongtype) # TODO custom types
        return variable_names
    # TODO These functions are extremely similar to
    # parse_parameters() / parse_parameter() / parse_returntype().
    # Should we unify those functions?
    def parse_let_variables(self) -> typing.Tuple[typing.List[str],typing.List[typing.Optional[bongtypes.BongtypeIdentifier]]]:
        variable_names : typing.List[str] = []
        variable_types : typing.List[typing.Optional[bongtypes.BongtypeIdentifier]] = []
        #?? self.check_eof("Parameter list expected")
        name, typ = self.parse_let_variable()
        variable_names.append(name)
        variable_types.append(typ)
        while self.match(token.COMMA):
            name, typ = self.parse_let_variable()
            variable_names.append(name)
            variable_types.append(typ)
        return (variable_names, variable_types)
    def parse_let_variable(self) -> typing.Tuple[str, typing.Optional[bongtypes.BongtypeIdentifier]]:
        #??? self.check_eof("Another parameter expected")
        if not self.match(token.IDENTIFIER):
            raise ParseException("Expected identifier as variable name.")
        name = self.peek(-1).lexeme
        if self.match(token.COLON):
            typ : typing.Optional[bongtypes.BongtypeIdentifier] = self.parse_type()
        else:
            typ = None
        return (name, typ)

    def if_stmt(self) -> ast.IfElseStatement:
        toks = TokenList()
        if not toks.add(self.match(token.IF)):
            raise Exception("Expected if.")
        cond = self.expression()
        t = self.block_stmt()
        e : typing.Union[None, ast.Block, ast.IfElseStatement] = None
        if toks.add(self.match(token.ELSE)):
            if self.peek().type == token.IF:
                e = self.if_stmt()
            else:
                e = self.block_stmt()
        return ast.IfElseStatement(toks, cond, t, e)

    def while_stmt(self) -> ast.WhileStatement:
        if not (tok := self.match(token.WHILE)):
            raise Exception("Expected while.")
        cond = self.expression()
        t = self.block_stmt()
        return ast.WhileStatement([tok], cond, t)

    def print_stmt(self) -> ast.Print:
        toks = TokenList()
        if not toks.add(self.match(token.PRINT)):
            raise Exception("Expected print statement.")
        expr = self.expression()
        toks.add(self.match(token.SEMICOLON))
        return ast.Print(toks, expr)

    def block_stmt(self) -> ast.Block:
        self.check_eof("Expected { for block statement.")
        toks = TokenList()
        if not toks.add(self.match(token.LBRACE)):
            raise ParseException("Expected { for block statement.")
        block_symbol_table = symbol_table.SymbolTable(self.symbol_table)
        self.symbol_table = block_symbol_table
        try:
            statements : typing.List[ast.BaseNode] = []
            while self.peek().type != token.RBRACE:
                self.check_eof("Expected statement for block body.")
                statements.append(self.stmt())
            self.check_eof("missing } for block statement")
            if not toks.add(self.match(token.RBRACE)):
                raise ParseException("Missing } for block statement.")
        finally:
            self.symbol_table = self.symbol_table.parent
        return ast.Block(toks, statements, block_symbol_table)

    def assignment(self) -> typing.Union[ast.ExpressionList, ast.AssignOp]:
        lhs : typing.Union[ast.ExpressionList, ast.AssignOp] = self.parse_commata_expressions()
        while tok := self.match(token.ASSIGN):
            rhs : ast.BaseNode = self.assignment()
            lhs = ast.AssignOp([tok], lhs, rhs)
        return lhs

    def expression(self) -> ast.BaseNode:
        return self.parse_or()

    def parse_or(self) -> ast.BaseNode:
        lhs = self.parse_and()
        while tok := self.match(token.OP_OR):
            lhs = ast.BinOp([tok], lhs, "||", self.parse_and())
        return lhs

    def parse_and(self) -> ast.BaseNode:
        lhs = self.parse_not()
        while tok := self.match(token.OP_AND):
            lhs = ast.BinOp([tok], lhs, "&&", self.parse_not())
        return lhs

    def parse_not(self) -> ast.BaseNode:
        if tok := self.match(token.OP_NEG):
            return ast.UnaryOp([tok], "!", self.parse_not())
        return self.compare()

    def compare(self) -> ast.BaseNode:
        lhs = self.parse_pipeline()
        while tok := self.match([token.OP_EQ, token.OP_NEQ, token.OP_GT, token.OP_GE, token.OP_LT, token.OP_LE]):
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
            lhs = ast.BinOp([tok], lhs, op, rhs)
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
        toks = TokenList()
        while toks.add(self.match(token.BONG)):
            if self.peek().type == token.LET:
                toks.add(self.peek())
                names = self.let_lhs()
                elements.append(ast.PipelineLet(toks, names))
            elif (self.peek().type == token.IDENTIFIER and
                    self.peek(1).type == token.COMMA):
                # Like this, we can not have more "complicated" variables
                # (index-access or whatever) that we want to assign to.
                elements.append(self.parse_commata_expressions())
            else:
                elements.append(self.addition())
        nonblocking = True if toks.add(self.match(token.AMPERSAND)) else False
        pipeline = ast.Pipeline(toks, elements, nonblocking)
        #if not self.match(token.SEMICOLON):
            #raise ParseException("A pipeline should end a line!")
        return pipeline

    def addition(self) -> ast.BaseNode:
        lhs = self.multiplication()
        while tok := self.match([token.OP_ADD, token.OP_SUB]):
            prev = self.peek(-1)
            rhs = self.multiplication()
            if prev.type == token.OP_ADD:
                op = "+"
            elif prev.type == token.OP_SUB:
                op = "-"
            else:
                raise Exception("Assertion failed: \"+-\".")
            lhs = ast.BinOp([tok], lhs, op, rhs)
        return lhs

    def multiplication(self):
        lhs = self.signed()
        while tok := self.match([token.OP_MULT, token.OP_DIV, token.OP_MOD]):
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
            lhs = ast.BinOp([tok], lhs, op, rhs)
        return lhs

    def signed(self):
        if tok := self.match(token.OP_SUB):
            return ast.UnaryOp([tok], "-", self.exponentiation())
        if self.match(token.OP_ADD):
            pass # return self.exponentiation()
        return self.exponentiation()

    def exponentiation(self):
        lhs = self.index_access()
        if tok := self.match(token.OP_POW):
            rhs = self.exponentiation()
            lhs = ast.BinOp([tok], lhs, "^", rhs)
        return lhs

    def index_access(self):
        lhs = self.primary()
        toks = TokenList()
        while toks.add(self.match(token.LBRACKET)):
            self.check_eof("Missing expression for indexing.")
            rhs = self.expression()
            if not toks.add(self.match(token.RBRACKET)):
                raise ParseException("Missing ] for indexing.")
            lhs = ast.IndexAccess(toks, lhs, rhs)
        return lhs

    def primary(self):
        if tok := self.match(token.INT_VALUE):
            return ast.Integer([tok], int(tok.lexeme))
        if tok := self.match(token.FLOAT_VALUE):
            return ast.Float([tok], float(tok.lexeme))
        if tok := self.match(token.STRING):
            return ast.String([tok], str(tok.lexeme))
        if tok := self.match(token.BOOL_VALUE):
            return ast.Bool([tok], True if self.peek(-1).lexeme=="true" else False)
        toks = TokenList()
        if toks.add(self.match(token.LPAREN)):
            exp = self.expression()
            if not toks.add(self.match(token.RPAREN)):
                raise ParseException("Missing closing parenthesis ).")
            exp.tokens.extend(toks)
            return exp
        if toks.add(self.match(token.LBRACKET)):
            if toks.add(self.match(token.RBRACKET)):
                return ast.Array(toks, ast.ExpressionList([], []))
            elements = self.parse_commata_expressions()
            if not toks.add(self.match(token.RBRACKET)):
                raise ParseException("Expected ].")
            return ast.Array(toks, elements)
        if tok := self.match(token.IDENTIFIER):
            toks.add(tok)
            if toks.add(self.match(token.LPAREN)):
                func_name = tok.lexeme
                arguments = self.parse_arguments()
                if not toks.add(self.match(token.RPAREN)):
                    raise ParseException("Missing ) on function call.")
                return ast.FunctionCall(toks, func_name, arguments)
            if self.symbol_table.exists(self.peek(-1).lexeme):
                return ast.Variable(toks, self.peek(-1).lexeme)
            name = self.peek(-1).lexeme
            args = self.syscall_arguments(name)
            # Add the last token we have used until now so that
            # the ast node's location (especially length) is right
            toks.add(self.peek(-1))
            return ast.SysCall(toks, args)
        # Special case: Syscall with './foo'
        if self.peek(0).type==token.DOT and self.peek(1).type==token.OP_DIV:
            # The DOT token could be preceded by whitespace which would cause
            # syscall_arguments() to have "" as the first argument of the
            # syscall if called without the following line and with
            # syscall_arguments("") instead.
            dot = self.next()
            args = self.syscall_arguments(".")
            toks.add(self.peek(-1)) # see above
            return ast.SysCall(toks, args)
        # Special case: Syscall with '../foo'
        if self.peek(0).type==token.DOT and self.peek(1).type==token.DOT and self.peek(2).type==token.OP_DIV:
            firstdot = self.next()
            args = self.syscall_arguments(".")
            toks.add(self.peek(-1)) # see above
            return ast.SysCall(toks, args)
        # Special case: Syscall with absolute path like '/foo/bar'
        if self.peek(0).type==token.OP_DIV and self.peek(1).type==token.IDENTIFIER:
            slash = self.next()
            args = self.syscall_arguments("/")
            toks.add(self.peek(-1)) # see above
            return ast.SysCall(toks, args)
        raise ParseException("Value, program call, '()' or array expected.")

    def parse_arguments(self) -> ast.ExpressionList:
        if self.peek().type == token.RPAREN:
            return ast.ExpressionList([],[])
        return self.parse_commata_expressions()

    def parse_commata_expressions(self) -> ast.ExpressionList:
        elements = ast.ExpressionList([], [])
        elements.append(self.expression())
        # no tokens required because all commas are encapsulated by
        # expressions so the location is correct anyways
        while self.match(token.COMMA):
            elements.append(self.expression())
        return elements

    def syscall_arguments(self, name) -> typing.List[str]:
        #valid = [token.OP_SUB, token.OP_DIV, token.OP_MULT, token.OP
        # TODO complete list of invalid tokens (which finish syscall args)
        invalid = [token.BONG, token.AMPERSAND, token.SEMICOLON, token.LBRACE, token.OP_EQ, token.RPAREN, token.EOF]
        arguments : typing.List[str] = []
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

    # Return current token
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

    # Return current token and advance to the next one
    def next(self):
        t = self.peek()
        self.past_tokens = [self.next_tokens[0]] + self.past_tokens[:-1]
        self.next_tokens = self.next_tokens[1:] + [self.lexer.get_token()]
        return t

    # Match current token against the type (or list of types) given in compare.
    # If found, return the current token and advance, otherwise return None.
    def match(self, compare):
        typ = self.peek().type
        if not isinstance(compare, list):
            compare = [compare]
        for c in compare:
            if c == typ:
                return self.next()
        return False

class TokenList(list):
    def __init__(self):
        nothing : typing.List[token.Token] = []
        super().__init__(nothing)
    def add(self, tok : typing.Optional[token.Token]):
        if isinstance(tok, token.Token):
            self.append(tok)
        return tok

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
