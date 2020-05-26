import token_def as token
import lexer
import ast
from symbol_tree import SymbolTree, SymbolTreeNode # the latter for snapshots
import evaluator # Required for access to the builtin variables
import sys # To print on stderr
import bongtypes
import typing
import os
import bong_builtins
import collections
from eof_exception import UnexpectedEof

class Parser:
    def __init__(self, lexer, snapshot=None, basepath=None):
        self.lexer = lexer

        self.basepath = basepath if basepath != None else os.getcwd()

        self.symbols_global : typing.Dict[str, bongtypes.BaseNode] = {}
        self.symbol_tree = SymbolTree()
        if snapshot != None:
            # When restoring the global dictionary, we need to copy the dict.
            # Otherwise, we change the snapshot that the caller (the repl)
            # will (most probably) reuse.
            self.symbols_global = snapshot[0].copy() # overwrite
            self.symbol_tree.restore_snapshot(snapshot[1]) # restore
        else:
            # Only when initializing symbol tables for the first time, register
            # builtin stuff
            for bfuncname, bfunc in bong_builtins.functions.items():
                self.symbols_global[bfuncname] = bongtypes.BuiltinFunction(bfunc[1])
            for btypename, btype in bongtypes.basic_types.items():
                self.symbols_global[btypename] = bongtypes.Typedef(btype())

    # TODO Somehow, the Parser is re-initialized each input round, the
    # evaluator is not. This is somehow the reason why snapshots have to be
    # taken and restored on the parser.
    # I guess this design can be revised, too.
    def take_snapshot(self) -> typing.Tuple[typing.Dict[str, bongtypes.BaseType], SymbolTreeNode]:
        return self.symbols_global, self.symbol_tree.take_snapshot()

    def compile(self) -> typing.Optional[ast.TranslationUnit]:
        try:
            return self.compile_uncaught()
        except lexer.TokenizeException as e:
            print(f"LexerError in {e.filepath}, line {e.line},"
                    f" column {e.col}: {e.msg}", file=sys.stderr)
        except ParseException as e:
            t = self.peek(e.offset)
            if t.lexeme != None:
                lexeme = t.lexeme
            else:
                lexeme = t.type
            print("ParseError: Token '{}' found in {}, line {}, column {}: {}".format(lexeme, t.filepath, t.line, t.col, e.msg), file=sys.stderr) # t.length unused
        return None
    def compile_uncaught(self) -> ast.TranslationUnit:
        # init_token_access() can throw EofException so it should not
        # be done in the constructor.
        self.init_token_access()
        imp_stmts : typing.List[ast.Import] = []
        struct_stmts : collections.OrderedDict[str, ast.StructDefinition] = collections.OrderedDict()
        func_stmts : collections.OrderedDict[str, ast.FunctionDefinition] = collections.OrderedDict()
        statements : typing.List[ast.BaseNode] = []
        while self.peek().type != token.EOF:
            stmt = self.top_level_stmt()
            if isinstance(stmt, ast.Import):
                imp_stmts.append(stmt)
            elif isinstance(stmt, ast.StructDefinition):
                if stmt.name in struct_stmts:
                    raise Exception("Struct Definition with same name generated twice.")
                struct_stmts[stmt.name] = stmt
            elif isinstance(stmt, ast.FunctionDefinition):
                func_stmts[stmt.name] = stmt
            else:
                statements.append(stmt)
        return ast.TranslationUnit(imp_stmts, struct_stmts, func_stmts,
                statements, self.symbols_global)

    def top_level_stmt(self) -> ast.BaseNode:
        if self.peek().type == token.IMPORT:
            return self.parse_import()
        if self.peek().type == token.STRUCT:
            return self.parse_struct_definition()
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
        if not toks.add(self.match(token.STRING)):
            raise ParseException("Expected module path as string.")
        path = self.peek(-1).lexeme
        if not toks.add(self.match(token.AS)):
            raise ParseException("Expected as")
        if not toks.add(self.match(token.IDENTIFIER)):
            raise ParseException("Expected module alias name.")
        name = self.peek(-1).lexeme
        toks.add(self.match(token.SEMICOLON))
        if not os.path.isabs(path):
            path = os.path.join(self.basepath, path)
        if name in self.symbols_global:
            raise ParseException(f"Name '{name}' already exists in global symbol table. Import impossible.")
        self.symbols_global[name] = bongtypes.UnknownType()
        return ast.Import(toks, name, path)

    def parse_function_definition(self) -> ast.FunctionDefinition:
        toks = TokenList()
        # FUNC foo (bar : int) : str { ... }
        if not toks.add(self.match(token.FUNC)):
            raise Exception("Expected function definition.")
        # func FOO (bar : int) : str { ... }
        if not toks.add(self.match(token.IDENTIFIER)):
            raise ParseException("Expected function name.")
        name = self.peek(-1).lexeme
        if name in self.symbols_global:
            raise ParseException(f"Name '{name}' already exists in symbol table. Function definition impossible.")
        # Register function name before parsing parameter names (no parameter name should have the function name!)
        self.symbols_global[name] = bongtypes.UnknownType()
        # (
        if not toks.add(self.match(token.LPAREN)):
            raise ParseException("Expected ( to start the parameter list.")
        # Parameters
        parameter_names, parameter_types = self.parse_parameters()
        # )
        if not toks.add(self.match(token.RPAREN)):
            raise ParseException("Expected ) to end the parameter list.")
        # Return types
        return_types : typing.List[ast.BongtypeIdentifier] = []
        if toks.add(self.match(token.COLON)):
            self.check_eof("Return type list expected.")
            return_types.append(self.parse_type())
            while toks.add(self.match(token.COMMA)):
                return_types.append(self.parse_type())
        # {
        if not self.peek().type == token.LBRACE:
            raise ParseException("Expected function body.")
        # New local symbol table (tree) for statement block
        # We could just store the global symbol table in the object because
        # it will always be the same. But remembering the previous symbol
        # table here theoretically allows to parse function definitions inside
        # other functions (the local symbol table would be properly restored
        # then).
        global_symbol_tree = self.symbol_tree
        self.symbol_tree = SymbolTree()
        # Parameters
        for param,typ in zip(parameter_names,parameter_types):
            if param in self.symbol_tree:
                raise ParseException(f"Argument name '{param}' appears twice in function definition")
            self.symbol_tree.register(param, bongtypes.UnknownType())
        # Snapshot before block is parsed (this changes the state of the tree)
        func_symbol_tree_snapshot = self.symbol_tree.take_snapshot()
        # Function body
        body = self.block_stmt()
        # Restore symbol table/tree
        self.symbol_tree = global_symbol_tree
        return ast.FunctionDefinition(toks, name, parameter_names, parameter_types, return_types, body, func_symbol_tree_snapshot)

    def parse_struct_definition(self) -> ast.StructDefinition:
        toks = TokenList()
        # STRUCT foo {bar : int, ...}
        if not toks.add(self.match(token.STRUCT)):
            raise Exception("Expected struct definition.")
        # func FOO {bar : int, ...}
        if not toks.add(self.match(token.IDENTIFIER)):
            raise ParseException("Expected struct name.")
        name = self.peek(-1).lexeme
        if name in self.symbols_global:
            raise ParseException(f"Name '{name}' already exists in global symbol table. Struct definition impossible.")
        # {
        if not toks.add(self.match(token.LBRACE)):
            raise ParseException("Expected { to start the field list.")
        # Fields
        field_names, field_types = self.parse_parameters()
        if len(field_names) == 0:
            raise ParseException(f"Struct {name} is empty.")
        fields : typing.Dict[str, ast.BongtypeIdentifier] = {}
        for field_name, field_type in zip(field_names, field_types):
            if field_name in fields:
                raise ParseException(f"Field '{field_name}' found multiple times"
                        " in struct '{name}'.")
            fields[field_name] = field_type
        # }
        if not toks.add(self.match(token.RBRACE)):
            raise ParseException("Expected } to end the field list.")
        # If everything went fine, register the struct name
        self.symbols_global[name] = bongtypes.UnknownType()
        return ast.StructDefinition(toks, name, fields)

    # Used by parse_function_definition() and parse_struct_definition()
    def parse_parameters(self) -> typing.Tuple[typing.List[str],typing.List[ast.BongtypeIdentifier]]:
        parameter_names : typing.List[str] = []
        parameter_types : typing.List[ast.BongtypeIdentifier] = []
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
    def parse_parameter(self) -> typing.Tuple[str,ast.BongtypeIdentifier]:
        self.check_eof("Another parameter expected")
        if not self.match(token.IDENTIFIER):
            raise ParseException("Expected identifier as parameter name.")
        name = self.peek(-1).lexeme
        if not self.match(token.COLON):
            raise ParseException("Expected type hint for function parameter.")
        typ = self.parse_type()
        return (name, typ)
    # Used by function definition and let statement
    def parse_type(self) -> ast.BongtypeIdentifier:
        num_array_levels = 0
        while self.match(token.LBRACKET):
            if not self.match(token.RBRACKET):
                raise ParseException("Expected closing bracket ']' in type specification.")
            num_array_levels += 1
        if not self.match(token.IDENTIFIER):
            raise ParseException("Expected identifier as module or type.")
        typename = [self.peek(-1).lexeme]
        while self.match(token.DOT):
            if not self.match(token.IDENTIFIER):
                raise ParseException("Expected identifier as module or type.")
            typename.append(self.peek(-1).lexeme)
        return ast.BongtypeIdentifier(typename, num_array_levels)

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
        var_names, var_types = self.let_lhs() # Writes variable names to symbol table
        if not toks.add(self.match(token.ASSIGN)):
            raise ParseException("Empty let statements are not supported. Always assign a value!")
        expr : typing.Union[ast.ExpressionList, ast.AssignOp] = self.assignment()
        toks.add(self.match(token.SEMICOLON))
        return ast.Let(toks, var_names, var_types, expr, self.symbol_tree.take_snapshot())
    # splitted so that this part can be reused for pipelines
    def let_lhs(self) -> typing.Tuple[typing.List[str],typing.List[typing.Optional[ast.BongtypeIdentifier]]]:
        if not self.match(token.LET):
            raise Exception("Expected let statement.")
        # Parse variable names and types
        variable_names, variable_types = self.parse_let_variables()
        # Check for duplicate names
        names = set()
        for name in variable_names:
            if name in names:
                raise ParseException(f"Name '{name}' found twice in let statement")
            names.add(name)
        # Batch register w/o failing
        for name in variable_names:
            self.symbol_tree.register(name, bongtypes.UnknownType())
        return variable_names, variable_types
    # TODO These functions are extremely similar to
    # parse_parameters() / parse_parameter() / parse_returntype().
    # Should we unify those functions?
    def parse_let_variables(self) -> typing.Tuple[typing.List[str],typing.List[typing.Optional[ast.BongtypeIdentifier]]]:
        variable_names : typing.List[str] = []
        variable_types : typing.List[typing.Optional[ast.BongtypeIdentifier]] = []
        name, typ = self.parse_let_variable()
        variable_names.append(name)
        variable_types.append(typ)
        while self.match(token.COMMA):
            name, typ = self.parse_let_variable()
            variable_names.append(name)
            variable_types.append(typ)
        return (variable_names, variable_types)
    def parse_let_variable(self) -> typing.Tuple[str, typing.Optional[ast.BongtypeIdentifier]]:
        self.check_eof("Another variable expected")
        if not self.match(token.IDENTIFIER):
            raise ParseException("Expected identifier as variable name.")
        name = self.peek(-1).lexeme
        if self.match(token.COLON):
            typ : typing.Optional[ast.BongtypeIdentifier] = self.parse_type()
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
        # Snapshot the current scope (before block)
        previous_scope = self.symbol_tree.take_snapshot()
        # Parse all block statments
        statements : typing.List[ast.BaseNode] = []
        while self.peek().type != token.RBRACE:
            self.check_eof("Expected statement for block body.")
            statements.append(self.stmt())
        self.check_eof("missing } for block statement")
        if not toks.add(self.match(token.RBRACE)):
            raise ParseException("Missing } for block statement.")
        # Store block scope and ...
        # leave block scope == restore scope snapshot
        block_scope = self.symbol_tree.take_snapshot()
        self.symbol_tree.restore_snapshot(previous_scope)
        return ast.Block(toks, statements)

    def assignment(self) -> typing.Union[ast.ExpressionList, ast.AssignOp]:
        lhs = self.parse_commata_expressions()
        # Parse only one '=', the others are consumed by the inner self.assignment()
        if tok := self.match(token.ASSIGN):
            rhs = self.assignment()
            return ast.AssignOp([tok], lhs, rhs)
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
                names, types = self.let_lhs()
                elements.append(ast.PipelineLet(toks, names, types, self.symbol_tree.take_snapshot()))
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
        lhs = self.access()
        if tok := self.match(token.OP_POW):
            rhs = self.exponentiation()
            lhs = ast.BinOp([tok], lhs, "^", rhs)
        return lhs

    def access(self):
        lhs = self.primary()
        toks = TokenList()
        """
        # For struct values, we have to check until 'T { field :' so that
        # it can be distinguished from 'if t {'
        # IndexAccess and FunctionCall are easier.
        while (self.peek(0).type == token.LBRACKET          # IndexAccess
                or self.peek(0).type == token.LPAREN        # FunctionCall
                or (self.peek(0).type == token.LBRACE       # StructValue
                    and self.peek(1).type == token.IDENTIFIER
                    and self.peek(2).type == token.COLON)
                ):
                """
        while self.following_access():
            if toks.add(self.match(token.LBRACKET)):
                self.check_eof("Missing expression for indexing.")
                rhs = self.expression()
                if not toks.add(self.match(token.RBRACKET)):
                    raise ParseException("Missing ] for indexing.")
                lhs = ast.IndexAccess(toks, lhs, rhs)
            elif toks.add(self.match(token.LPAREN)):
                arguments = self.parse_arguments()
                if not toks.add(self.match(token.RPAREN)):
                    raise ParseException("Missing ) on function call.")
                lhs = ast.FunctionCall(toks, lhs, arguments)
            elif toks.add(self.match(token.DOT)):
                if not toks.add(self.match(token.IDENTIFIER)):
                    raise ParseException("Missing identifier for DotIndex.")
                rhs = self.peek(-1).lexeme
                lhs = ast.DotAccess(toks, lhs, rhs)
            else:
                if not toks.add(self.match(token.LBRACE)):
                    raise Exception("Missing { for struct value.")
                fields = self.parse_struct_fields()
                if not toks.add(self.match(token.RBRACE)):
                    raise ParseException("Missing } on struct value.")
                # The statement/access is finished after instantiating a struct
                #return ast.StructValue(toks, lhs, fields)
                # A newly instantiated struct can be accessed directly
                lhs = ast.StructValue(toks, lhs, fields)
        return lhs

    # Currently, we generate program calls in primary as a fallback if an identifier
    # is not found. This causes us to parse program calls whenever a
    # function or struct type is defined after it is used. To mitigate,
    # we already have to check in primary() if a function call or struct
    # value will follow. Since this is the condition that is required
    # in access(), we transfer it to its own method and call it from
    # access() and primary().
    def following_access(self):
        if self.peek(0).type == token.LBRACKET:
            return True
        if self.peek(0).type == token.LPAREN:
            return True
        # TODO Currently, we enforce the dot to follow immediately after
        # the previous identifier so that things like 'cd ..' or 'ls .'
        # will still be parsed as program calls. This should be changed
        # later when program call generation is fixed.
        if self.peek(0).type == token.DOT and not self.peek(0).prec_by_space:
            return True
        if (self.peek(0).type == token.LBRACE
                and self.peek(1).type == token.IDENTIFIER
                and self.peek(2).type == token.COLON):
            return True

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
        # parentheses ( ... )
        if toks.add(self.match(token.LPAREN)):
            exp = self.expression()
            if not toks.add(self.match(token.RPAREN)):
                raise ParseException("Missing closing parenthesis ).")
            exp.tokens.extend(toks)
            return exp
        # array values [ ... ]
        if toks.add(self.match(token.LBRACKET)):
            if toks.add(self.match(token.RBRACKET)):
                return ast.Array(toks, ast.ExpressionList([], []))
            elements = self.parse_commata_expressions()
            if not toks.add(self.match(token.RBRACKET)):
                raise ParseException("Expected ].")
            return ast.Array(toks, elements)
        # variable name, function call, struct value, ... here, we only
        # parse the corresponding identifier or ... program call fallback
        if toks.add(self.match(token.IDENTIFIER)):
            identifier = self.peek(-1).lexeme
            if (identifier in self.symbol_tree 
                    or identifier in self.symbols_global
                    or self.following_access()):
                return ast.Identifier(toks, identifier)
            # Program Call fallback!
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

    def parse_struct_fields(self) -> typing.Dict[str, ast.BaseNode]:
        fields : typing.Dict[str, ast.BaseNode] = {}
        name, value = self.parse_struct_field()
        fields[name] = value
        while self.match(token.COMMA):
            name, value = self.parse_struct_field()
            if name in fields:
                raise ParseException(f"Field '{name}' found multiple times")
            fields[name] = value
        return fields
    def parse_struct_field(self) -> typing.Tuple[str, ast.BaseNode]:
        if not self.match(token.IDENTIFIER):
            raise ParseException("Struct value requires at least one field.")
        name = self.peek(-1).lexeme
        if not self.match(token.COLON):
            raise ParseException("':' missing for assigning a value to struct field.")
        value = self.expression()
        return name, value

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
