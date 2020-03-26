import ast
import symbol_table
import bongtypes
from bongtypes import TypeList, BongtypeException

import typing
from enum import Enum
import sys # stderr

# For each checked node, indicates if that node is/contains ...
class Return(Enum):
    NO = 1    # no return statement (default)
    MAYBE = 2 # a conditionally invoked return statement (e.g. in if-else)
    YES = 3   # a possibly nested return statement that is definitely invoked

class TypeChecker:
    def __init__(self):
        pass

    def checkprogram(self, program : ast.Program) -> bool:
        try:
            self.checkprogram_uncaught(program)
        except TypecheckException as e:
            if e.node != None:
                loc = e.node.get_location()
                posstring = f" in {loc[0]}, line {loc[1]} col {loc[2]} to line {loc[3]} col {loc[4]}"
            else:
                posstring = ""
            print(f"TypecheckError{posstring}: {str(e.msg)}", file=sys.stderr)
            return False
        return True

    def checkprogram_uncaught(self, program : ast.Program):
        # DEBUG
        #print(program.symbol_table)
        #print(program)
        self.symbol_table = program.symbol_table
        for stmt in program.statements:
            res, turn = self.check(stmt)
            # If there is a possible return value,
            if turn != Return.NO:
                # ensure it is an int
                expect = bongtypes.TypeList([bongtypes.Integer()])
                if not res.sametype(expect):
                    raise TypecheckException("Return type of program does not evaluate to int.", stmt)

    # Determine the type of the ast node.
    # This method returns the TypeList (0, 1 or N elements) that the node will
    # evaluate to and a return hint that tells us if the node contains a
    # return statement and if it is sure that this return will be invoked. This
    # information is required to check/guarantee the return type of function
    # definitions.
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
                                raise TypecheckException("Return type does not match previous return type in block.", stmt)
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
                raise TypecheckException("If statement requires boolean condition.", node.cond)
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
                    raise TypecheckException("'If' and 'Else' branch's return type do not match.", node)
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
                raise TypecheckException("While statement requires boolean condition.", node.cond)
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
                        raise TypecheckException("Assignment expected!", node.rhs)
                rhs, turn = self.check(node.rhs)
                assert isinstance(node.lhs, ast.ExpressionList)
                for var in node.lhs:
                    if not (isinstance(var, ast.Variable) or isinstance(var, ast.IndexAccess)):
                        raise TypecheckException("Lhs of assignment must be a variable!", var)
                lhs, turn = self.check(node.lhs)
                match_types(lhs, rhs, node,
                        ("Variable and expression types in assignment do"
                        f" not match. Lhs expects '{lhs}' but rhs evaluates"
                        f" to '{rhs}'"))
                return lhs, Return.NO
            # For BinOps, most bongtypes' operators are overloaded
            # Not overloaded: 'and' and 'or'
            lhslist, turn = self.check(node.lhs)
            rhslist, turn = self.check(node.rhs)
            assert len(lhslist)==1 and len(rhslist)==1
            lhstyp = lhslist[0]
            rhstyp = rhslist[0]
            try: # Catch all BongtypeExceptions
                if op == "+":
                    # TODO "+" is a valid operator for arrays but we do not do
                    # the proper empty-array check with match_types() here. Should
                    # we do that?
                    return TypeList([lhstyp + rhstyp]), Return.NO
                if op == "-":
                    return TypeList([lhstyp - rhstyp]), Return.NO
                if op == "*":
                    return TypeList([lhstyp * rhstyp]), Return.NO
                if op == "/":
                    return TypeList([lhstyp / rhstyp]), Return.NO
                if op == "%":
                    return TypeList([lhstyp % rhstyp]), Return.NO
                if op == "^":
                    return TypeList([lhstyp ** rhstyp]), Return.NO
                if op == "&&":
                    if type(lhstyp)!=bongtypes.Boolean:
                        raise TypecheckException("Logical 'and' expects boolean operands. Left operand is not boolean.", node.lhs)
                    if type(rhstyp)!=bongtypes.Boolean:
                        raise TypecheckException("Logical 'and' expects boolean operands. Right operand is not boolean.", node.rhs)
                    return TypeList([bongtypes.Boolean()]), Return.NO
                if op == "||":
                    if type(lhstyp)!=bongtypes.Boolean:
                        raise TypecheckException("Logical 'or' expects boolean operands. Left operand not boolean.", node.lhs)
                    if type(rhstyp)!=bongtypes.Boolean:
                        raise TypecheckException("Logical 'or' expects boolean operands. Right operand is not boolean.", node.rhs)
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
            except BongtypeException as e: # ... and transform to TypecheckExc
                raise TypecheckException(e.msg, node)
        elif isinstance(node, ast.UnaryOp):
            try: # Catch all BongtypeExceptions ...
                op = node.op
                if op == "!":
                    rhs, turn = self.check(node.rhs)
                    if len(rhs)!=1 or type(rhs[0])!=bongtypes.Boolean:
                        raise TypecheckException("Logical 'not' expects boolean operand.", node)
                    return TypeList([bongtypes.Boolean()]), Return.NO
                if op == "-":
                    rhstype, turn = self.check(node.rhs)
                    if len(rhstype)!=1 or not (type(rhstype[0])==bongtypes.Integer or type(rhstype[0])==bongtypes.Float):
                        raise TypecheckException("Negate expects number.", node)
                    return rhstype, Return.NO
                raise Exception("unrecognised unary operator: " + str(node.op))
            except BongtypeException as e: # ... and transform to TypecheckExc
                raise TypecheckException(e.msg, node)
        elif isinstance(node, ast.Integer):
            return TypeList([bongtypes.Integer()]), Return.NO
        elif isinstance(node, ast.Float):
            return TypeList([bongtypes.Float()]), Return.NO
        elif isinstance(node, ast.String):
            return TypeList([bongtypes.String()]), Return.NO
        elif isinstance(node, ast.Bool):
            return TypeList([bongtypes.Boolean()]), Return.NO
        elif isinstance(node, ast.SysCall):
            return TypeList([bongtypes.Integer()]), Return.NO
        elif isinstance(node, ast.Pipeline):
            # TODO Pipelines unchecked until now!
            # Also see evaluator -> ast.Pipeline, it is very similar
            if len(node.elements) < 2:
                raise TypecheckException("Pipelines should have more than one element. This seems to be a parser bug.", node)
            programcalls = []
            strtype = TypeList([bongtypes.String()]) # used for checking stdin and stdout
            # Check pipeline input types
            if isinstance(node.elements[0], ast.SysCall):
                programcalls.append(node.elements[0])
            else:
                stdin, turn = self.check(node.elements[0]) # turn == NO
                if not stdin.sametype(strtype):
                    raise TypecheckException("The input to a pipeline should evaluate to a string, {} was found instead.".format(stdin), node.elements[0])
            # Collect programcalls
            for elem in node.elements[1:-1]:
                if not isinstance(elem, ast.SysCall):
                    raise TypecheckException("The main part of a pipeline (all"
                        " elements but the first and last) should only consist"
                        f" of program calls, '{elem}' found instead.", elem)
                programcalls.append(elem)
            # Check pipeline output types
            if isinstance(node.elements[-1], ast.SysCall):
                programcalls.append(node.elements[-1])
            else:
                assignto = node.elements[-1]
                # a) Variable
                # a2) Variables in ExpressionList
                # b) IndexAccess (not supported in parser yet)
                # c) PipelineLet
                # For all three (currently two) cases, the assignee must evaluate to string
                # TODO It seems to me that stronger typing would clear things here a bit
                if isinstance(assignto, ast.Variable): # a)
                    stdout, turn = self.check(assignto)
                    if not stdout.sametype(strtype):
                        raise TypecheckException("The output of a pipeline can only be written to a string variable, {} was found instead.".format(stdout), assignto)
                elif isinstance(assignto, ast.ExpressionList): # a2)
                    outNerr, turn = self.check(assignto)
                    if not outNerr.sametype(TypeList([bongtypes.String(), bongtypes.String()])):
                        raise TypecheckException("The output of a pipeline can only be written to two string variables, '{}' was found instead.".format(outNerr), assignto)
                elif isinstance(assignto, ast.PipelineLet):
                    names = assignto.names
                    if len(names) > 2 or len(names)==0:
                        raise TypecheckException("The output of a pipeline can only be written to one or two string variables, let with {} variables  was found instead.".format(len(names)), assignto)
                    for name in names:
                        sym = self.symbol_table[name]
                        if sym.typ.sametype(bongtypes.AutoType()):
                            sym.typ = strtype
                        elif not sym.typ.sametype(strtype):
                            raise TypecheckException("The output of a pipeline can only be written to string variables, let with explicit type '{}' was found instead.".format(sym.typ), assignto)
                else:
                    raise TypecheckException("The output of a pipeline can only"
                            f" be written to string variables, {assignto} found"
                            " instead.", assignto)
            # Check that everything in between actually is a program call
            for pcall in programcalls:
                if not isinstance(pcall, ast.SysCall):
                    raise TypecheckException("Everything in the center of a pipeline must be a programmcall, '{}' was found instead.".format(pcall), pcall)
            return TypeList([bongtypes.Integer()]), Return.NO
        elif isinstance(node, ast.Variable):
            return TypeList([self.symbol_table.get(node.name).typ]), Return.NO
        elif isinstance(node, ast.IndexAccess):
            index, turn = self.check(node.rhs)
            if len(index)!=1 or type(index[0])!=bongtypes.Integer:
                raise TypecheckException("Indexing requires Integer.", node.rhs)
            lhs, turn = self.check(node.lhs)
            if len(lhs)!=1:
                raise TypecheckException("Indexing requires a single variable.", node.lhs)
            if isinstance(lhs[0], bongtypes.String): # bong string
                return lhs, Return.NO
            if isinstance(lhs[0], bongtypes.Array): # bong array
                return TypeList([lhs[0].contained_type]), Return.NO
            raise TypecheckException("IndexAccess with unsupported type.", node.lhs)
        if isinstance(node, ast.FunctionDefinition):
            # The function interface should already be completely in the symbol table.
            # Here, we only check that the function block is valid and that it returns
            # what we expect!
            func = self.symbol_table[node.name].typ # bongtypes.Function
            self.push_symtable(node.symbol_table)
            try:
                expect = func.return_types
                actual, turn = self.check(node.body)
                match_types(expect, actual, node, "Function return type does not"
                    f" match function declaration. Declared '{expect}' but"
                    f" returned '{actual}'.")
                # Enforce that there is a return statement if we require it
                if len(expect) > 0: # Return required
                    if turn != Return.YES: # Return not guaranteed
                        raise TypecheckException("Point of no return reached!", node)
                        raise TypecheckException(
                                "Function declaration expects return type"
                                f" '{expect}' but a return statement that"
                                " will definitely be invoked is missing.", node)
            except TypecheckException as e:
                # In case of error, remove function from symbol table
                self.symbol_table.remove(node.name)
                raise
            finally:
                self.pop_symtable()
            return TypeList([]), Return.NO # FunctionDefinition itself returns nothing
        if isinstance(node, ast.FunctionCall):
            if not self.symbol_table.exists(node.name):
                raise TypecheckException("Function '{}' not found.".format(node.name), node)
            func = self.symbol_table[node.name].typ
            if type(func)!=bongtypes.Function and type(func)!=bongtypes.BuiltinFunction:
                raise TypecheckException("'{}' is not a function.".format(node.name), node)
            argtypes, turn = self.check(node.args)
            # Check builtin functions
            if isinstance(func, bongtypes.BuiltinFunction):
                try:
                    return func.check(argtypes), Return.NO
                except BongtypeException as e: # Convert to TypecheckException
                    raise TypecheckException(e.msg, node)
            # Otherwise, it is a bong function that has well-defined parameter types
            match_types(func.parameter_types, argtypes, node,
                    (f"Function '{node.name}' expects parameters of type "
                    f"'{func.parameter_types}' but '{argtypes}' were given."))
            # If everything goes fine (function can be called), it returns
            # whatever the function declaration says \o/
            return func.return_types, Return.NO
        elif isinstance(node, ast.Print):
            self.check(node.expr) # We can print anything but don't care
            return TypeList([]), Return.NO
        elif isinstance(node, ast.Let):
            try: # If anything goes wrong, remove name from symbol table
                results, turn = self.check(node.expr)
                if len(node.names) != len(results):
                    raise TypecheckException("Number of expressions on rhs of let statement does not match the number of variables.", node)
                for name, result in zip(node.names,results):
                    sym = self.symbol_table[name]
                    #if sym.typ.sametype(bongtypes.AutoType()): # Depending on syntax definition, this condition is enough. But the other is stronger
                    if not is_specific_type(sym.typ):
                        if not is_specific_type(result):
                            raise TypecheckException("Automatic type for variable '{}' but rhs is no definitive type either, '{}' found instead.".format(name, result), node)
                        sym.typ = result
                    #elif not sym.typ.sametype(result): # Former condition, without empty arrays
                    else:
                        merge_types(sym.typ, result, node, "Assignment in let statement impossible: '{}' has type '{}' but expression has type '{}'.".format(name, sym.typ, result))
            except TypecheckException as e:
                for name in node.names:
                    self.symbol_table.remove(name)
                raise
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
            inner_type : bongtypes.BaseType = bongtypes.AutoType()
            # Otherwise, all contained types should match
            for i, typ in enumerate(types):
                inner_type = merge_types(inner_type, typ, node)
            return TypeList([bongtypes.Array(inner_type)]), Return.NO
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

# merge_types() has two usages:
# 1. It is used in ast.Array to merge inner types that occur. For example,
# if an array is given as ''[[], [[]], []]'', it's type must be at least 
# Array(Array(Array(auto))). Merging [], [[]] and [] which are the types
# seen by the topmost array is done by this function.
# This merge fails whenever the two given types are incompatible, e.g. [[],1].
# 2. Whenever an array type is required as a value (assignments, function
# call, ...), this function can be used to match the expected type and the
# array that was given (and could possibly empty or contain empty arrays). If
# this fails, this automatically raises a TypecheckException. To distinguish
# the different cases, an optional error message can be supplied.
def merge_types(x : bongtypes.BaseType, y : bongtypes.BaseType, node : ast.BaseNode, msg : typing.Optional[str] = None) -> bongtypes.BaseType:
    if x.sametype(bongtypes.AutoType()):
        return y
    if y.sametype(bongtypes.AutoType()):
        return x
    if isinstance(x, bongtypes.Array) and isinstance(y, bongtypes.Array):
        return bongtypes.Array(merge_types(x.contained_type, y.contained_type, node, msg))
    if not x.sametype(y):
        if isinstance(msg, str):
            raise TypecheckException(msg, node)
        else:
            raise TypecheckException("Types '{}' and '{}' are incompatible.".format(x, y), node)
    return x

def match_types(lhs : TypeList, rhs : TypeList, node : ast.BaseNode, msg : str):
    if len(lhs)!=len(rhs):
        raise TypecheckException(msg, node)
    for l,r in zip(lhs,rhs):
        merge_types(l, r, node, msg)

def is_specific_type(x : bongtypes.BaseType) -> bool:
    if isinstance(x, bongtypes.AutoType):
        return False
    if isinstance(x, bongtypes.Array):
        return is_specific_type(x.contained_type)
    return True

class TypecheckException(Exception):
    def __init__(self, msg : str, node : ast.BaseNode):
        super().__init__(self, msg)
        self.msg = msg
        self.node = node
    def __str__(self):
        return super().__str__()
