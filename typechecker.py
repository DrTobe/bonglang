import ast
import symbol_table
import bongtypes

import typing

# Comply with typing constraints, unpack BaseType value from optional
def some(typ : typing.Optional[bongtypes.BaseType]) -> bongtypes.BaseType:
    assert isinstance(typ, bongtypes.BaseType)
    return typ
def somenode(node : typing.Optional[ast.BaseNode]) -> ast.BaseNode:
    assert isinstance(node, ast.BaseNode)
    return node

class TypeChecker:
    def __init__(self):
        pass

    def checkprogram(self, program : ast.Program):
        print(program.symbol_table)
        print(program)
        self.symbol_table = program.symbol_table
        for stmt in program.statements:
            res = self.check(stmt)
            if isinstance(res, bongtypes.ReturnType):
                # TODO check that expression evaluates to INT
                pass
        return True # TODO is there any return type?

    def check(self, node : ast.BaseNode) -> typing.Optional[bongtypes.BaseType]:
        if isinstance(node, ast.Block):
            self.push_symtable(node.symbol_table)
            try:
                # All return statements in a whole block must match so that the
                # whole block is consistent. Store return types in block_result.
                block_result = None
                for stmt in node.stmts:
                    result = self.check(stmt)
                    if isinstance(result, bongtypes.ReturnType):
                        if block_result == None: # initialize
                            block_result = result
                        elif not some(block_result).sametype(result): # ensure that all returns are the same
                                raise bongtypes.BongtypeException("Return type does not match previous return type in block.")
            finally:
                self.pop_symtable()
            return block_result
        if isinstance(node, ast.Return):
            if node.result == None:
                return bongtypes.ReturnType(None)
            result = self.check(node.result)
            return bongtypes.ReturnType(result)
        if isinstance(node, ast.IfElseStatement):
            if type(self.check(node.cond))!=bongtypes.Boolean:
                raise bongtypes.BongtypeException("If statement requires boolean condition.")
            a = self.check(node.thn)
            b = None # so that b is not undefined
            if node.els != None:
                b = self.check(somenode(node.els))
            # 1. if { } else { } -> OK
            # 2. if { return } else { } -> OK
            # 3. if { } else { return } -> OK
            # 4. if { return } else { } -> returns should match!
            # (Also see type checking for Block that ensures return-type equality)
            if a!=None and b!=None: # 4
                if some(a).sametype(b):
                    return a
                else:
                    raise bongtypes.BongtypeException("'If' and 'Else' branch's return type do not match.")
            if b!=None:             # 3
                return b
            return a                # 1 & 2
        if isinstance(node, ast.WhileStatement):
            if type(self.check(node.cond))!=bongtypes.Boolean:
                raise bongtypes.BongtypeException("While statement requires boolean condition.")
            return self.check(node.t)
        if isinstance(node, ast.BinOp):
            op = node.op
            if op == "=":
                assert isinstance(node.lhs, ast.ExpressionList)
                assert isinstance(node.rhs, ast.ExpressionList)
                return self.assign(node.lhs, node.rhs)
            # For BinOps, most bongtypes' operators are overloaded
            # Not overloaded: 'and' and 'or'
            lhs = some(self.check(node.lhs))
            rhs = some(self.check(node.rhs))
            if op == "+":
                return lhs + rhs
            if op == "-":
                return lhs - rhs
            if op == "*":
                return lhs * rhs
            if op == "/":
                return lhs // rhs
            if op == "%":
                return lhs % rhs
            if op == "^":
                return lhs ** rhs
            if op == "&&":
                if type(lhs)!=bongtypes.Boolean:
                    raise bongtypes.BongtypeException("Logical 'and' expects boolean operands. Left operand is not boolean.")
                if type(rhs)!=bongtypes.Boolean:
                    raise bongtypes.BongtypeException("Logical 'and' expects boolean operands. Right operand is not boolean.")
                return bongtypes.Boolean()
            if op == "||":
                if type(lhs)!=bongtypes.Boolean:
                    raise bongtypes.BongtypeException("Logical 'or' expects boolean operands. Left operand not boolean.")
                if type(rhs)!=bongtypes.Boolean:
                    raise bongtypes.BongtypeException("Logical 'or' expects boolean operands. Right operand is not boolean.")
                return bongtypes.Boolean()
            if op == "==":
                return lhs.eq(rhs)
            if op == "!=":
                return lhs.ne(rhs)
            if op == "<":
                return lhs < rhs
            if op == ">":
                return lhs > rhs
            if op == "<=":
                return lhs <= rhs
            if op == ">=":
                return lhs >= rhs
            else:
                raise Exception("unrecognised binary operator: " + str(node.op))
        elif isinstance(node, ast.UnaryOp):
            op = node.op
            if op == "!":
                if type(node.rhs)!=bongtypes.Boolean:
                    raise bongtypes.BongtypeException("Logical 'not' expects boolean operand.")
                return bongtypes.Boolean()
            if op == "-":
                if not (type(node.rhs)==bongtypes.Integer or type(node.rhs)==bongtypes.Float):
                    raise bongtypes.BongtypeException("Negate expects number.")
                return node.rhs
            raise Exception("unrecognised unary operator: " + str(node.op))
        elif isinstance(node, ast.Integer):
            return bongtypes.Integer()
        elif isinstance(node, ast.Float):
            return bongtypes.Float()
        elif isinstance(node, ast.String):
            return bongtypes.String()
        elif isinstance(node, ast.Bool):
            return bongtypes.Boolean()
        elif isinstance(node, ast.Pipeline):
            # TODO Pipelines unchecked until now!
            raise Exception("not implemented yet")
            """
            if len(node.elements) < 2:
                raise Exception("Pipelines should have more than one element. This seems to be a parser bug.")
            syscalls = []
            if isinstance(node.elements[0], ast.SysCall):
                syscalls.append(node.elements[0])
                stdin = None
            else:
                stdin = self.evaluate(node.elements[0])
            syscalls.extend(node.elements[1:-1])
            if isinstance(node.elements[-1], ast.SysCall):
                syscalls.append(node.elements[-1])
                assignto = None
            else:
                assignto = node.elements[-1]
            # Special case: piping an ordinary expression into a variable
            if len(syscalls) == 0:
                if assignto == None:
                    raise Exception("Assertion error: Whenever a pipeline has no syscalls, it should consist of an expression that is assigned to something. No assignment was found here.")
                return self.assign(assignto, stdin)
            processes = []
            for syscall in syscalls[:-1]:
                process = self.callprogram(syscall, stdin, True)
                processes.append(process)
                stdin = process.stdout
            numOutputPipes = 0 if assignto==None else self.numInputsExpected(assignto)
            lastProcess = self.callprogram(syscalls[-1], stdin, numOutputPipes)
            # So, there is this single case that is different from everything else
            # and that needs special treatment:
            # Whenever the first process is opened with stdin=PIPE, we must
            # close its stdin except when this is the only process, then we
            # must not close the stdin, because then communicate() will fail.
            if not isinstance(node.elements[0], ast.SysCall) and len(processes):
                processes[0].stdin.close()
            outstreams = lastProcess.communicate()
            for process in processes:
                process.wait()
            if assignto != None:
                self.assign(assignto, list(outstreams[:numOutputPipes]))
                return lastProcess.returncode
            else:
                return lastProcess.returncode
                """
        elif isinstance(node, ast.Variable):
            return self.symbol_table.get(node.name).typ
        elif isinstance(node, ast.IndexAccess):
            index = self.check(node.rhs)
            if type(index)!=bongtypes.Integer:
                raise bongtypes.BongtypeException("Indexing requires Integer.")
            lhs = some(self.check(node.lhs)) # assert
            if isinstance(lhs, bongtypes.String): # bong string
                return bongtypes.String()
            if isinstance(lhs, bongtypes.Array): # bong array
                return lhs.contained_type
            # TODO!
            """
            if isinstance(lhs, list): # sys_argv
                return lhs[index]
                """
            raise bongtypes.BongtypeException("IndexAccess with unsupported type.")
        if isinstance(node, ast.FunctionDefinition):
            # The function interface should already be completely in the symbol table.
            # Here, we only check that the function block is valid and that it returns
            # what we expect!
            func = self.symbol_table[node.name].typ # bongtypes.Function
            self.push_symtable(node.symbol_table)
            try:
                # TODO If something goes wrong here, we have to remove the name from the symbol-table
                expect = func.return_types
                actual = bongtypes.TypeList([])
                ret = self.check(node.body)
                if isinstance(ret, bongtypes.TypeList): # None is not iterable
                    for typ in ret:
                        actual.append(ret)
                if not expect.sametype(actual):
                    raise bongtypes.BongtypeException("Function return type does not match function declaration. Declared '{}' but returned '{}'.".format(expect, actual))
            finally:
                self.pop_symtable()
            return None # FunctionDefinition itself returns nothing
        if isinstance(node, ast.FunctionCall):
            if not self.symbol_table.exists(node.name):
                raise bongtypes.BongtypeException("Function '{}' not found.".format(node.name))
            func = self.symbol_table[node.name].typ
            if type(func)!=bongtypes.Function:
                raise bongtypes.BongtypeException("'{}' is not a function.".format(node.name))
            argtypes = self.check(node.args)
            if not func.parameter_types.sametype(argtypes):
                raise bongtypes.BongtypeException("Function '{}' expects parameters of type '{}' but '{}' were given.".format(node.name, func.parameter_types, argtypes))
            # If everything goes fine (function can be called), it returns
            # whatever the function declaration says \o/
            return func.return_types
        elif isinstance(node, ast.SysCall):
            return bongtypes.Integer()
        elif isinstance(node, ast.Print):
            return None
        elif isinstance(node, ast.Let):
            # TODO I guess we have to enforce that the rhs of a let definitely contains an expressionlist
            results = self.check(node.expr)
            assert isinstance(results, bongtypes.TypeList)
            if len(node.names) != len(results):
                raise bongtypes.BongtypeException("Number of expressions on rhs of let statement does not match the number of variables.")
            for name, result in zip(node.names,results):
                sym = self.symbol_table[name]
                if sym.typ.sametype(bongtypes.AutoType()):
                    sym.typ = result
                elif not sym.typ.sametype(result):
                    raise bongtypes.BongtypeException("Assignment in let statement impossible: '{}' has type '{}' but expression has type '{}'.".format(node.name, sym.typ, result))
                return None
        elif isinstance(node, ast.Array):
            if len(node.elements)==0:
                raise bongtypes.BongtypeException("Empty arrays are not supported (yet?) because the type of the array can not be determined.")
            typ = self.check(node.elements[0])
            if typ==None:
                raise bongtypes.BongtypeException("Arrays must contain values of any type. First element has no type.")
            #for index, e in enumerate(node.elements, start=1): # TODO will this work?
            for i, expr in enumerate(node.elements): # TODO will this work?
                t = self.check(node.elements[index])
                if not typ.sametype(t):
                    raise bongtypes.BongtypeException("All elements in an array must be of the same type. First element is '{}' but '{}' was found (element index {}).".format(typ, t, index))
            return bongtypes.Array(typ)
        elif isinstance(node, ast.ExpressionList):
            types = bongtypes.TypeList([])
            for exp in node:
                typ = self.check(exp)
                if typ != None:
                    types.append(typ) # TypeList is automatically flattened
            return types
        else:
            raise Exception("unknown ast node")
        return None

    def assign(self, lhs : ast.ExpressionList, rhs : ast.ExpressionList) -> bongtypes.BaseType:
        if len(lhs)!=len(rhs):
            raise bongtypes.BongtypeException("Number of variables and number of expressions for assignment do not match.")
        for i in range(len(lhs)):
            var = lhs[i]
            exp = rhs[i]
            if not (isinstance(var, ast.Variable) or isinstance(var, ast.IndexAccess)):
                raise bongtypes.BongtypeException("Lhs of assignment must be a variable!")
            vartyp = self.check(var)
            exptyp = self.check(exp)
            if not vartyp.sametype(exptyp):
                raise bongtypes.BongtypeException("Types of variable and expression in assignment do not match. Variable is '{}', expression is '{}'.".format(vartyp, exptyp))
            return vartyp

    def push_symtable(self, new_symtable : symbol_table.SymbolTable):
        self.symbol_table = new_symtable

    def pop_symtable(self):
        self.symbol_table = self.symbol_table.parent
