import ast
import symbol_table
import bongtypes
from bongtypes import TypeList, BongtypeException

import typing
from enum import Enum

# For each checked node, indicates if that node is/contains ...
class Return(Enum):
    NO = 1    # no return statement (default)
    MAYBE = 2 # a conditionally invoked return statement (e.g. in if-else)
    YES = 3   # a possibly nested return statement that is definitely invoked

class TypeChecker:
    def __init__(self):
        pass

    def checkprogram(self, program : ast.Program):
        # DEBUG
        #print(program.symbol_table)
        #print(program)
        self.symbol_table = program.symbol_table
        for stmt in program.statements:
            res, turn = self.check(stmt)
            if turn:
                # TODO check that expression evaluates to INT
                pass
        return True # TODO is there any return type?

    def check(self, node : ast.BaseNode) -> typing.Tuple[TypeList, Return]:
        if isinstance(node, ast.Block):
            self.push_symtable(node.symbol_table)
            try:
                # All return statements in a whole block must match so that the
                # whole block is consistent.
                block_return : typing.Tuple[TypeList, Return] = (TypeList([]), Return.NO)
                for stmt in node.stmts:
                    stmt_return = self.check(stmt)
                    if stmt_return[1] != Return.NO:
                        if block_return[1] == Return.NO:
                            # initialize
                            block_return = stmt_return
                        else:
                            # ensure that all return types are the same
                            if not block_return[0].sametype(stmt_return[0]):
                                raise BongtypeException("Return type does not match previous return type in block.")
                            # If at least one statement in the block definitely
                            # returns, the whole block definitely returns
                            # -> a YES overwrites a MAYBE
                            if stmt_return[1] == Return.YES:
                                block_return = stmt_return # block_return[1] = Return.YES
                                # Here, we could theoretically break from the
                                # loop because subsequent statements will not
                                # be executed. But no break has the benefit
                                # that the following code is already typechecked.
                                # When the return is removed, the typechecker 
                                # result will not change.
            finally:
                self.pop_symtable()
            return block_return
        if isinstance(node, ast.Return):
            if node.result == None:
                return bongtypes.TypeList([]), Return.YES
            res, turn = self.check(node.result) # turn should be false here
            return res, Return.YES
        if isinstance(node, ast.IfElseStatement):
            cond, turn = self.check(node.cond)
            if len(cond)==0 or type(cond[0])!=bongtypes.Boolean:
                raise BongtypeException("If statement requires boolean condition.")
            # TODO
            a, aturn = self.check(node.thn)
            if isinstance(node.els, ast.BaseNode):
                b, bturn = self.check(node.els)
            else:
                b, bturn = a, Return.NO # if there is no else, it won't return
            # 1. if { } else { } -> OK
            # 2. if { return } else { } -> OK
            # 3. if { } else { return } -> OK
            # 4. if { return } else { return } -> returns should match!
            # If there is no 'else', this is covered by 1. and 2.
            if aturn!=Return.NO and bturn!=Return.NO: # 4
                if not a.sametype(b):
                    raise BongtypeException("'If' and 'Else' branch's return type do not match.")
                # Here, only if both are YES, the whole if-else is YES
                if aturn==Return.YES and bturn==Return.YES:
                    return a, Return.YES
                return a, Return.MAYBE
            if aturn!=Return.NO:           # 2
                return a, Return.MAYBE
            if bturn!=Return.NO:           # 3
                return b, Return.MAYBE
            return TypeList([]), Return.NO # 1
        if isinstance(node, ast.WhileStatement):
            if type(self.check(node.cond))!=bongtypes.Boolean:
                raise BongtypeException("While statement requires boolean condition.")
            types, turn = self.check(node.t)
            if turn != Return.NO:
                return types, Return.MAYBE
            return types, turn
        if isinstance(node, ast.BinOp):
            op = node.op
            if op == "=":
                # Multiple assignments are parsed/executed rhs-first
                # so we only have to switch-case the rhs
                if isinstance(node.rhs, ast.BinOp): # Multiple assignments at once
                    if node.rhs.op != "=":
                        raise BongtypeException("Assignment expected!")
                rhs, turn = self.check(node.rhs)
                assert isinstance(node.lhs, ast.ExpressionList)
                for var in node.lhs:
                    if not (isinstance(var, ast.Variable) or isinstance(var, ast.IndexAccess)):
                        raise BongtypeException("Lhs of assignment must be a variable!")
                lhs, turn = self.check(node.lhs)
                if not lhs.sametype(rhs):
                    raise BongtypeException("Variable and expression types in assignment do not match.")
                return lhs, Return.NO
            # For BinOps, most bongtypes' operators are overloaded
            # Not overloaded: 'and' and 'or'
            lhslist, turn = self.check(node.lhs)
            rhslist, turn = self.check(node.rhs)
            assert len(lhslist)==1 and len(rhslist)==1
            lhstyp = lhslist[0]
            rhstyp = rhslist[0]
            if op == "+":
                return TypeList([lhstyp + rhstyp]), Return.NO
            if op == "-":
                return TypeList([lhstyp - rhstyp]), Return.NO
            if op == "*":
                return TypeList([lhstyp * rhstyp]), Return.NO
            if op == "/":
                return TypeList([lhstyp // rhstyp]), Return.NO
            if op == "%":
                return TypeList([lhstyp % rhstyp]), Return.NO
            if op == "^":
                return TypeList([lhstyp ** rhstyp]), Return.NO
            if op == "&&":
                if type(lhstyp)!=bongtypes.Boolean:
                    raise BongtypeException("Logical 'and' expects boolean operands. Left operand is not boolean.")
                if type(rhstyp)!=bongtypes.Boolean:
                    raise BongtypeException("Logical 'and' expects boolean operands. Right operand is not boolean.")
                return TypeList([bongtypes.Boolean()]), Return.NO
            if op == "||":
                if type(lhstyp)!=bongtypes.Boolean:
                    raise BongtypeException("Logical 'or' expects boolean operands. Left operand not boolean.")
                if type(rhstyp)!=bongtypes.Boolean:
                    raise BongtypeException("Logical 'or' expects boolean operands. Right operand is not boolean.")
                return TypeList([bongtypes.Boolean()]), Return.NO
            if op == "==":
                return TypeList([lhstyp.eq(rhstyp)]), Return.NO
            if op == "!=":
                return TypeList([lhstyp.ne(rhstyp)]), Return.NO
            if op == "<":
                return TypeList([lhstyp < rhstyp]), Return.NO
            if op == ">":
                return TypeList([lhstyp > rhstyp]), Return.NO
            if op == "<=":
                return TypeList([lhstyp <= rhstyp]), Return.NO
            if op == ">=":
                return TypeList([lhstyp >= rhstyp]), Return.NO
            else:
                raise Exception("unrecognised binary operator: " + str(node.op))
        elif isinstance(node, ast.UnaryOp):
            op = node.op
            if op == "!":
                rhs, turn = self.check(node.rhs)
                if len(rhs)!=1 or type(rhs[0])!=bongtypes.Boolean:
                    raise BongtypeException("Logical 'not' expects boolean operand.")
                return TypeList([bongtypes.Boolean()]), Return.NO
            if op == "-":
                rhstype, turn = self.check(node.rhs)
                if len(rhstype)!=1 or not (type(rhstype[0])==bongtypes.Integer or type(rhstype[0])==bongtypes.Float):
                    raise BongtypeException("Negate expects number.")
                return rhstype, Return.NO
            raise Exception("unrecognised unary operator: " + str(node.op))
        elif isinstance(node, ast.Integer):
            return TypeList([bongtypes.Integer()]), Return.NO
        elif isinstance(node, ast.Float):
            return TypeList([bongtypes.Float()]), Return.NO
        elif isinstance(node, ast.String):
            return TypeList([bongtypes.String()]), Return.NO
        elif isinstance(node, ast.Bool):
            return TypeList([bongtypes.Boolean()]), Return.NO
        elif isinstance(node, ast.Pipeline):
            # TODO Pipelines unchecked until now!
            import sys # To print on stderr
            print("Warning: ast.Pipeline not properly type-checked.", file=sys.stderr) # t.length unused
            return TypeList([bongtypes.Integer()]), Return.NO
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
            return TypeList([self.symbol_table.get(node.name).typ]), Return.NO
        elif isinstance(node, ast.IndexAccess):
            index, turn = self.check(node.rhs)
            if len(index)!=1 or type(index[0])!=bongtypes.Integer:
                raise BongtypeException("Indexing requires Integer.")
            lhs, turn = self.check(node.lhs)
            if len(lhs)!=1:
                raise BongtypeException("Indexing requires a single variable.")
            if isinstance(lhs[0], bongtypes.String): # bong string
                return lhs, Return.NO
            if isinstance(lhs[0], bongtypes.Array): # bong array
                return TypeList([lhs[0].contained_type]), Return.NO
            # TODO!
            """
            if isinstance(lhs, list): # sys_argv
                return lhs[index]
                """
            raise BongtypeException("IndexAccess with unsupported type.")
        if isinstance(node, ast.FunctionDefinition):
            # The function interface should already be completely in the symbol table.
            # Here, we only check that the function block is valid and that it returns
            # what we expect!
            func = self.symbol_table[node.name].typ # bongtypes.Function
            self.push_symtable(node.symbol_table)
            try:
                expect = func.return_types
                actual, turn = self.check(node.body)
                if not expect.sametype(actual):
                    raise BongtypeException("Function return type does not match function declaration. Declared '{}' but returned '{}'.".format(expect, actual))
                # Enforce that there is a return statement if we require it
                if len(expect) > 0: # Return required
                    if turn != Return.YES: # Return not guaranteed
                        raise BongtypeException("Function declaration expects return type '{}' but"
                            " a return statement that will definitely be invoked is missing.".format(expect))
            except BongtypeException as e:
                # In case of error, remove function from symbol table
                self.symbol_table.remove(node.name)
                raise
            finally:
                self.pop_symtable()
            return TypeList([]), Return.NO # FunctionDefinition itself returns nothing
        if isinstance(node, ast.FunctionCall):
            if not self.symbol_table.exists(node.name):
                raise BongtypeException("Function '{}' not found.".format(node.name))
            func = self.symbol_table[node.name].typ
            if type(func)!=bongtypes.Function:
                raise BongtypeException("'{}' is not a function.".format(node.name))
            argtypes, turn = self.check(node.args)
            if not func.parameter_types.sametype(argtypes):
                raise BongtypeException("Function '{}' expects parameters of type '{}' but '{}' were given.".format(node.name, func.parameter_types, argtypes))
            # If everything goes fine (function can be called), it returns
            # whatever the function declaration says \o/
            return func.return_types, Return.NO
        elif isinstance(node, ast.SysCall):
            return TypeList([bongtypes.Integer()]), Return.NO
        elif isinstance(node, ast.Print):
            return TypeList([]), Return.NO
        elif isinstance(node, ast.Let):
            results, turn = self.check(node.expr)
            if len(node.names) != len(results):
                raise BongtypeException("Number of expressions on rhs of let statement does not match the number of variables.")
            for name, result in zip(node.names,results):
                sym = self.symbol_table[name]
                if sym.typ.sametype(bongtypes.AutoType()):
                    sym.typ = result
                elif not sym.typ.sametype(result):
                    raise BongtypeException("Assignment in let statement impossible: '{}' has type '{}' but expression has type '{}'.".format(name, sym.typ, result))
            return TypeList([]), Return.NO
        elif isinstance(node, ast.Array):
            # Super complicated things can happen here:
            # Imagine the array contains function calls like
            # arr = [foonc(), baar()]
            # and those functions return multiple values.
            # Then, check(ast.Array.elements : ExpressionList) -- see below -- creates
            # a TypeList and the multiple return values from the functions are TypeLists
            # themselves. When those are added to the main TypeList, it is flattened
            # automatically. In the result, we just have a List of types. And here, we
            # just have to check that all those types are equal.
            # I'm fascinated how everything magically works automatically. Isn't that beautiful?
            types, turn = self.check(node.elements)
            if len(types)==0:
                raise BongtypeException("Empty arrays are not supported (yet?) because the type of the array can not be determined.")
            for i, typ in enumerate(types):
                if not typ.sametype(types[0]):
                    raise BongtypeException("All elements in an array must be of the same type. First element is '{}' but '{}' was found (element index {}).".format(types[0], typ, index))
            return TypeList([bongtypes.Array(typ)]), Return.NO
        elif isinstance(node, ast.ExpressionList):
            types = bongtypes.TypeList([])
            for exp in node:
                typ, turn = self.check(exp)
                types.append(typ) # TypeLists are automatically flattened
            return types, Return.NO
        else:
            raise Exception("unknown ast node")
        return None

    def push_symtable(self, new_symtable : symbol_table.SymbolTable):
        self.symbol_table = new_symtable

    def pop_symtable(self):
        self.symbol_table = self.symbol_table.parent
