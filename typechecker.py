import ast
from symbol_tree import SymbolTree
import bongtypes
from bongtypes import TypeList, BongtypeException
import lexer, parser

import typing
from enum import Enum
import sys # stderr

# For each checked node, indicates if that node is/contains ...
class Return(Enum):
    NO = 1    # no return statement (default)
    MAYBE = 2 # a conditionally invoked return statement (e.g. in if-else)
    YES = 3   # a possibly nested return statement that is definitely invoked

class TypeChecker:
    def __init__(self, symbol_table_snapshot = None, modules : typing.Optional[typing.Dict[str, ast.TranslationUnit]] = None):
        self.symbol_tree = SymbolTree(symbol_table_snapshot)
        self.modules : typing.Dict[str, ast.TranslationUnit] = modules if isinstance(modules, dict) else {}

    def checkprogram(self, main_unit : ast.TranslationUnit) -> typing.Optional[ast.Program]:
        try:
            return self.checkprogram_uncaught(main_unit)
        except TypecheckException as e:
            if e.node != None:
                loc = e.node.get_location()
                posstring = f" in {loc[0]}, line {loc[1]} col {loc[2]} to line {loc[3]} col {loc[4]}"
            else:
                posstring = ""
            print(f"TypecheckError{posstring}: {str(e.msg)}", file=sys.stderr)
            return None

    # The typechecker has to assign types in the symbol table for
    # - function definitions (parameter types, return types)
    # - struct definitions
    # - let statements
    # Since assigning types for let statements requires a full
    # ast pass, we do all type assignments in the typechecker.
    # Like this, it is not split on several components.
    #
    # Anyways, resolving custom types has to be done first so that
    # types are available for subsequent steps.
    # Next, function interfaces can/must be resolved so that their
    # type requirements are available for function calls.
    # Finally, everything else can be checked (function bodies
    # can only be checked here, not earlier).
    # This pattern resembles how the evaluator handles
    # FunctionDefinitions and all other statements differently.
    #
    # If we want to be insane, we could do all of this in one
    # single pass: Collect all type- and function-definitions first,
    # then resolve types and function interfaces as needed (check
    # the symbol-table if this has to be done yet).
    # Anyways, it can safely be assumed that the split approach
    # is more maintainable, debuggable, understandable.
    # If you want to try out the insane approach, just insert
    # resolve_type() and resolve_function_interface() at the
    # appropriate places when check()ing the ast.
    def checkprogram_uncaught(self, main_unit : ast.TranslationUnit) -> ast.Program:
        # DEBUG
        #print("Global symbols:", main_unit.symbols_global)
        #print(main_unit.symbol_tree)
        #print(main_unit)
        # Theoretically, everything is accessible via this chain:
        # self.program.main_unit.symbols_global
        # Anyways, for convenience, we make everything accessible here.
        self.main_unit = main_unit
        self.symbols_global = main_unit.symbols_global
        program = ast.Program(self.modules, main_unit)
        # Resolve module imports first
        self.parse_imports(main_unit)
        # Then resolve types
        self.resolve_types(main_unit)
        for unit in self.modules.values():
            self.symbols_global = unit.symbols_global
            self.resolve_types(unit)
        # Resolve function interfaces
        self.symbols_global = main_unit.symbols_global
        self.resolve_function_interfaces(main_unit)
        for unit in self.modules.values():
            self.symbols_global = unit.symbols_global
            self.resolve_function_interfaces(unit)
        # Typecheck the rest (also assigning variable types)
        # Functions in modules
        for unit in self.modules.values():
            self.symbols_global = unit.symbols_global
            for func in unit.function_definitions.values():
                res, turn = self.check(func)
        # Functions in main_module / main_unit
        self.symbols_global = main_unit.symbols_global
        for func in main_unit.function_definitions.values():
            res, turn = self.check(func)
        # Statements in main_module / main_unit
        for stmt in main_unit.statements:
            res, turn = self.check(stmt)
            # If there is a possible return value,
            if turn != Return.NO:
                # ensure it is an int
                expect = bongtypes.TypeList([bongtypes.Integer()])
                if not res.sametype(expect):
                    raise TypecheckException("Return type of program does not evaluate to int.", stmt)
        return program

    def parse_imports(self, parent_unit : ast.TranslationUnit):
        for imp_stmt in parent_unit.import_statements:
            if imp_stmt.path not in self.modules:
                # Parse
                # TODO this should be encapsulated more nicely. Currently, same code
                # as in main.py
                try:
                    with open(imp_stmt.path) as f:
                        code = f.read()
                except Exception as e:
                    raise TypecheckException(f"Importing {imp_stmt.path} impossible:"
                            f" '{e}'", imp_stmt)
                l = lexer.Lexer(code, imp_stmt.path)
                p = parser.Parser(l)
                child_unit = p.compile()
                # add2modmap
                self.modules[imp_stmt.path] = child_unit
                # Recurse
                self.parse_imports(child_unit)
            # Add to symbol table
            parent_unit.symbols_global[imp_stmt.name] = bongtypes.Module(imp_stmt.path)

    def resolve_types(self, unit : ast.TranslationUnit):
        for typename, struct_def in unit.struct_definitions.items():
            self.resolve_type(ast.BongtypeIdentifier([typename], 0), unit, struct_def)

    # Resolve a given BongtypeIdentifier to an actual type. For custom types,
    # this method will not return the bongtypes.Typedef, but the value type instead,
    # i.e. the Typedefs will be unpacked.
    # It can crash whenever an inner type in a struct, a type hint in a function
    # interface or a type hint in a let statement uses a typename that is not defined.
    # TODO Prevent recursive types: Actually, we will do something different:
    # 1. Allow recursive types by adding a struct's name to the symbol table
    # before resolving the inner types.
    # 2. We check if there is a recursive circle without arrays (which can be
    # empty):
    # struct T { x : T } is an error because it is infinite
    # struct T { x : []T } is OK because the array can be empty at some point
    def resolve_type(self, identifier : ast.BongtypeIdentifier, unit : ast.TranslationUnit, node : ast.BaseNode) -> bongtypes.ValueType:
        # Arrays are resolved recursively
        if identifier.num_array_levels > 0:
            return bongtypes.Array(self.resolve_type(ast.BongtypeIdentifier(identifier.typename, identifier.num_array_levels-1), unit, node))
        # If a module name is given, propagate to the module
        if len(identifier.typename) > 1:
            modulename = identifier.typename[0]
            remaining_typename = identifier.typename[1:]
            if (not modulename in unit.symbols_global
                    or not isinstance(unit.symbols_global[modulename], bongtypes.Module)
                    or not unit.symbols_global[modulename].path in self.modules):
                raise TypecheckException(f"Module {modulename} can not be"
                        " resolved.", node)
            modulepath = unit.symbols_global[modulename].path
            child_unit = self.modules[modulepath]
            remaining_typeidentifier = ast.BongtypeIdentifier(remaining_typename, 0)
            return self.resolve_type(remaining_typeidentifier, child_unit, node)
        # Otherwise, the typename is the only item in the list
        typename = identifier.typename[0]
        # Check missing type
        if not typename in unit.symbols_global:
            raise TypecheckException(f"Type {typename} can not be"
                    " resolved.", node)
        # Already known types can be returned
        if not unit.symbols_global[typename].sametype(bongtypes.UnknownType()):
            if not isinstance(unit.symbols_global[typename], bongtypes.Typedef):
                raise TypecheckException(f"Type {typename} can not be"
                        " resolved.", node)
            return unit.symbols_global[typename].value_type # unpack
        # Everything else (structs) will be determined by determining the inner types
        if not typename in unit.struct_definitions:
            raise TypecheckException(f"Type {typename} can not be"
                    " resolved.", node)
        struct_def = unit.struct_definitions[typename]
        fields : typing.Dict[str, bongtypes.ValueType] = {}
        for name, type_identifier in struct_def.fields.items():
            fields[name] = self.resolve_type(type_identifier, unit, struct_def)
        value_type = bongtypes.Struct(typename, fields)
        unit.symbols_global[typename] = bongtypes.Typedef(value_type)
        return value_type

    def resolve_function_interfaces(self, unit : ast.TranslationUnit):
        for func_definition in unit.function_definitions.values():
            self.resolve_function_interface(func_definition, unit)
    
    def resolve_function_interface(self, function : ast.FunctionDefinition, unit : ast.TranslationUnit):
        parameters = bongtypes.TypeList([])
        returns = bongtypes.TypeList([])
        for param_name, param_type in zip(function.parameter_names, function.parameter_types):
            typ = self.resolve_type(param_type, unit, function)
            parameters.append(typ)
            SymbolTree(function.symbol_tree_snapshot)[param_name] = typ
        for ret in function.return_types:
            returns.append(self.resolve_type(ret, unit, function))
        unit.symbols_global[function.name] = bongtypes.Function(parameters, returns)

    def is_writable(self, node : ast.BaseNode):
        # Identifiers can describe modules, function names, types, variables. Only variables
        # are writable and only those will be as ValueTypes in the symbol table so this is
        # how we can determine the writability of this node.
        if isinstance(node, ast.Identifier):
            if node.name in self.symbol_tree:
                return True
            else:
                return False
            #return isinstance(self.symbol_table[node.name].typ, bongtypes.ValueType)
        # IndexAccess and DotAccess are writable whenever the lhs is writable, e.g.
        # foo().bar not writable
        # foo.bar[0] writable if foo is a writable variable
        # foo.bar()[0].baz not writable because function call's result is not writable
        # mod.foo not writable if mod is a module, then mod.foo is a type
        elif isinstance(node, ast.IndexAccess):
            return self.is_writable(node.lhs)
        elif isinstance(node, ast.DotAccess):
            return self.is_writable(node.lhs)
        elif isinstance(node, ast.ExpressionList):
            for n in node.inner_nodes:
                if not self.is_writable(n):
                    return False
            return True
        # Everything else shouldn't be writable (function calls, blocks, ...)
        else:
            return False

    # Determine the type of the ast node.
    # This method returns the TypeList (0, 1 or N elements) that the node will
    # evaluate to and a return hint that tells us if the node contains a
    # return statement and if it is sure that this return will be invoked. This
    # information is required to check/guarantee the return type of function
    # definitions.
    def check(self, node : ast.BaseNode) -> typing.Tuple[TypeList, Return]:
        if isinstance(node, ast.Block):
            symbol_tree_snapshot = self.symbol_tree.take_snapshot()
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
            # Restore scope
            self.symbol_tree.restore_snapshot(symbol_tree_snapshot)
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
            types, turn = self.check(node.cond)
            if len(types)!=1:
                raise TypecheckException("While statement requires a single"
                        " boolean value as condition.", node.cond)
            if type(types[0])!=bongtypes.Boolean:
                raise TypecheckException("While statement requires boolean condition.", node.cond)
            types, turn = self.check(node.t)
            if turn != Return.NO:
                return types, Return.MAYBE
            return types, turn
        if isinstance(node, ast.AssignOp):
            rhs, turn = self.check(node.rhs)
            lhs, turn = self.check(node.lhs)
            match_types(lhs, rhs, node, 
                    ("Variable and expression types in assignment do"
                    f" not match. Lhs expects '{lhs}' but rhs evaluates"
                    f" to '{rhs}'"))
            if not self.is_writable(node.lhs):
                raise TypecheckException("Lhs of assignment is no writable variable!", node.lhs)
            return lhs, Return.NO
        if isinstance(node, ast.BinOp):
            op = node.op
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
                # Either the assignto is a PipelineLet, then check it manually,
                # or the assignto is something else, then do the same checks as for assignments.
                if isinstance(assignto, ast.PipelineLet):
                    names = assignto.names
                    if len(names) > 2 or len(names)==0:
                        raise TypecheckException("The output of a pipeline can only be written to one or two string variables, let with {} variables  was found instead.".format(len(names)), assignto)
                    for name, type_identifier in zip(assignto.names, assignto.types):
                        if isinstance(type_identifier, ast.BongtypeIdentifier):
                            typ = self.resolve_type(type_identifier, self.main_unit, assignto)
                            if not typ.sametype(bongtypes.String()):
                                raise TypecheckException("The output of a pipeline"
                                    " can only be written to string variables, let"
                                    f" with explicit type '{typ}' was found instead.", assignto)
                        else:
                            pass
                        self.symbol_tree.restore_snapshot(assignto.symbol_tree_snapshot)
                        self.symbol_tree[name] = bongtypes.String()
                else:
                    output, turn = self.check(assignto)
                    writable = self.is_writable(assignto)
                    if (not writable or 
                            (not output.sametype(strtype)
                                and not output.sametype(TypeList([bongtypes.String(), bongtypes.String()]))
                                )
                            ):
                        raise TypecheckException("The output of a pipeline can only"
                            f" be written to string variables, {assignto} found"
                            " instead.", assignto)
            # Check that everything in between actually is a program call
            for pcall in programcalls:
                if not isinstance(pcall, ast.SysCall):
                    raise TypecheckException("Everything in the center of a pipeline must be a programmcall, '{}' was found instead.".format(pcall), pcall)
            return TypeList([bongtypes.Integer()]), Return.NO
        elif isinstance(node, ast.Identifier):
            if node.name in self.symbol_tree:
                return TypeList([self.symbol_tree[node.name]]), Return.NO
            elif node.name in self.symbols_global:
                return TypeList([self.symbols_global[node.name]]), Return.NO
            raise TypecheckException(f"{node.name} is undefined.", node)
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
        elif isinstance(node, ast.DotAccess):
            lhs, turn = self.check(node.lhs)
            if len(lhs)!=1:
                raise TypecheckException("DotAccess requires a single variable/identifier.", node.lhs)
            if isinstance(lhs[0], bongtypes.Struct): # bong struct
                if node.rhs not in lhs[0].fields:
                    raise TypecheckException(f"Name '{node.rhs}' not found in"
                            f" struct '{node.lhs}'.", node)
                value_type = lhs[0].fields[node.rhs]
                return TypeList([value_type]), Return.NO
            elif isinstance(lhs[0], bongtypes.Module): # module
                modulepath = lhs[0].path
                if not modulepath in self.modules:
                    raise TypecheckException(f"Module {node.lhs} can not be"
                            " resolved.", node)
                module = self.modules[modulepath]
                if node.rhs not in module.symbols_global:
                    raise TypecheckException(f"Name '{node.rhs}' not found in"
                            f" module '{node.lhs}' which resolved to '{lhs[0]}'.", node)
                return TypeList([module.symbols_global[node.rhs]]), Return.NO
            raise TypecheckException("DotAccess with unsupported type.", node.lhs)
        elif isinstance(node, ast.FunctionDefinition):
            # The function interface should already be completely in the symbol table.
            # Here, we only check that the function block is valid and that it returns
            # what we expect!
            func = self.symbols_global[node.name] # bongtypes.Function
            assert(isinstance(func, bongtypes.Function))
            # Before function body checking, save/restore symbol table
            # The current snapshot should be empty here because function
            # definitions are typechecked before the main statements are
            # checked. But anyways, logically, this is the right approach!
            symbol_tree_snapshot = self.symbol_tree.take_snapshot()
            self.symbol_tree.restore_snapshot(node.symbol_tree_snapshot)
            # Compare expected with actual result/return
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
            # Restore symbol table before function call
            self.symbol_tree.restore_snapshot(symbol_tree_snapshot)
            return TypeList([]), Return.NO # FunctionDefinition itself returns nothing
        if isinstance(node, ast.FunctionCall):
            funcs, turn = self.check(node.name)
            if len(funcs)!=1:
                raise TypecheckException(f"'{node.name}' does not resolve to a function.", node.name)
            func = funcs[0]
            if type(func)!=bongtypes.Function and type(func)!=bongtypes.BuiltinFunction:
                raise TypecheckException(f"'{node.name}' is not a function.", node)
            argtypes, turn = self.check(node.args)
            # Check builtin functions
            if isinstance(func, bongtypes.BuiltinFunction):
                try:
                    return func.check(argtypes), Return.NO
                except BongtypeException as e: # Convert to TypecheckException
                    raise TypecheckException(e.msg, node)
            # Otherwise, it is a bong function that has well-defined parameter types
            assert(isinstance(func, bongtypes.Function))
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
            # Check rhs expression
            results, turn = self.check(node.expr)
            if len(node.names) != len(results):
                raise TypecheckException("Number of expressions on rhs of let statement does not match the number of variables.", node)
            # Before handling the lhs of the let statement, set the correct
            # scope symbol table. This is necessary so that all symbol table
            # interaction affects the variables that are declared by the
            # let statement
            self.symbol_tree.restore_snapshot(node.symbol_tree_snapshot)
            # Then, check the type information and store to symbol table
            for name, type_identifier, result in zip(node.names, node.types, results):
                if isinstance(type_identifier, ast.BongtypeIdentifier):
                    typ = self.resolve_type(type_identifier, self.main_unit, node)
                    result = merge_types(typ, result, node, "Assignment in let statement impossible: '{}' has type '{}' but expression has type '{}'.".format(name, typ, result))
                else:
                    if not is_specific_type(result):
                        raise TypecheckException("Automatic type for variable '{}' but rhs is no definitive type either, '{}' found instead.".format(name, result), node)
                self.symbol_tree[name] = result
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
            inner_type : bongtypes.ValueType = bongtypes.AutoType()
            # Otherwise, all contained types should match
            for i, typ in enumerate(types):
                inner_type = merge_types(inner_type, typ, node)
            return TypeList([bongtypes.Array(inner_type)]), Return.NO
        elif isinstance(node, ast.StructValue):
            struct_types, turn = self.check(node.name)
            if len(struct_types)!=1:
                raise TypecheckException(f"'{node.name}' does not resolve to a (single) struct.", node.name)
            struct_type = struct_types[0]
            if (type(struct_type)!=bongtypes.Typedef
                    or type(struct_type.value_type)!=bongtypes.Struct):
                raise TypecheckException(f"'{node.name}' is not a struct type.", node)
            fields : typing.Dict[str, bongtypes.ValueType] = {}
            for name, value in node.fields.items():
                argtypes, turn = self.check(value)
                if len(argtypes) != 1:
                    raise TypecheckException("Expression does not evaluate"
                            " to a single value.", value)
                # Duplicates are caught in the parser, we can just assign here.
                if not isinstance(argtypes[0], bongtypes.ValueType):
                    raise TypecheckException("ValueType expected", value)
                fields[name] = argtypes[0]
            # TODO See issue #27: Currently, we only write the resolved struct
            # type's name into the struct value here.
            struct_val = bongtypes.Struct(struct_type.value_type.name, fields)
            typ = merge_types(struct_type.value_type, struct_val, node)
            return TypeList([typ]), Return.NO
        elif isinstance(node, ast.ExpressionList):
            types = bongtypes.TypeList([])
            for exp in node:
                typlist, turn = self.check(exp)
                types.append(typlist) # TypeLists are automatically flattened
            return types, Return.NO
        else:
            raise Exception("unknown ast node")
        return None

# merge_types() has multiple usages:
# 1. It is used in ast.Array to merge inner types that occur. For example,
# if an array is given as ''[[], [[]], []]'', it's type must be at least
# Array(Array(Array(auto))). Merging [], [[]] and [] which are the types
# seen by the topmost array is done by this function.
# This merge fails whenever the two given types are incompatible, e.g. [[],1].
# 2. Whenever an array type is required as a value (assignments, function
# call, ...), this function can be used to match the expected type and the
# array that was given (and could possibly be empty or contain empty arrays). If
# this fails, this automatically raises a TypecheckException. To distinguish
# the different cases, an optional error message can be supplied.
# 3. Struct instantiation (currently: when the struct value contains an empty
# array, in the future possibly: when the struct def contains an automatic type)
def merge_types(x : bongtypes.ValueType, y : bongtypes.ValueType, node : ast.BaseNode, msg : typing.Optional[str] = None) -> bongtypes.ValueType:
    if x.sametype(bongtypes.AutoType()):
        """ TODO Not required (changed y from BaseType to ValueType)
        if not isinstance(y, bongtypes.ValueType):
            raise TypecheckException(mergemsg(f"Types '{x}' and '{y}' can not be"
                " merged because type {y} can not be instantiated.", msg), node)
        """
        return y
    if y.sametype(bongtypes.AutoType()):
        return x
    if isinstance(x, bongtypes.Array) and isinstance(y, bongtypes.Array):
        return bongtypes.Array(merge_types(x.contained_type, y.contained_type, node, msg))
    if isinstance(x, bongtypes.Struct) and isinstance(y, bongtypes.Struct):
        if x.name != y.name:
            raise TypecheckException(mergemsg(f"Structs {x.name} and {y.name}"
                " are incompatible (different names).", msg), node)
        for xfield in x.fields:
            if xfield not in y.fields:
                raise TypecheckException(mergemsg(f"Field {xfield} is missing"
                    " in rhs.", msg), node)
        for yfield in y.fields:
            if yfield not in x.fields:
                raise TypecheckException(mergemsg(f"Field {yfield} is missing"
                    " in lhs.", msg), node)
        # Prevent Python's call by reference to change the arguments by 
        # creating a new struct here!
        fields : typing.Dict[str, bongtypes.ValueType] = {}
        for n in x.fields:
            fields[n] = merge_types(x.fields[n], y.fields[n], node, msg)
        return bongtypes.Struct(x.name, fields)
    if not x.sametype(y):
        raise TypecheckException(mergemsg(f"Types '{x}' and '{y}' are"
            " incompatible.", msg), node)
    return x
def mergemsg(a, b):
    return b if isinstance(b,str) else a

# TODO rename to merge_typelists
def match_types(lhs : TypeList, rhs : TypeList, node : ast.BaseNode, msg : str) -> TypeList:
    if len(lhs)!=len(rhs):
        raise TypecheckException(msg, node)
    types = TypeList([])
    for l,r in zip(lhs,rhs):
        types.append(merge_types(l, r, node, msg))
    return types

def is_specific_type(x : bongtypes.BaseType) -> bool:
    if isinstance(x, bongtypes.AutoType):
        return False
    if isinstance(x, bongtypes.Array):
        return is_specific_type(x.contained_type)
    if isinstance(x, bongtypes.Struct):
        for contained_type in x.fields.values():
            if not is_specific_type(contained_type):
                return False
    return True
def is_specific_types(x : bongtypes.TypeList) -> bool:
    for t in x:
        if not is_specific_type(t):
            return False
    return True

class TypecheckException(Exception):
    def __init__(self, msg : str, node : ast.BaseNode):
        super().__init__(self, msg)
        self.msg = msg
        self.node = node
    def __str__(self):
        return super().__str__()
