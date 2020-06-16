from __future__ import annotations
import ast
import bong_builtins
import bongtypes
from bongvalues import ValueList, StructValue
import collections
from symbol_tree import SymbolTree, SymbolTreeNode
import copy

# For subprocesses
import os
import subprocess
import io

# For cmdline arguments
import sys

import typing

class Eval:
    # Defined here so that it can be used by the parser
    BUILTIN_ENVIRONMENT = {
                "sys_argv": sys.argv
            }
    def __init__(self, printfunc=print):
        self.printfunc = printfunc
        # The following structures must
        # already be defined here so that they are retained for shell
        # input (which is split on several ast.Programs).
        # Everything that can be accessed with a name/identifier, is stored
        # either in globals or locals.
        # Globals is a dictionary that maps global names to instances. It
        # contains modules, typedefs, functions.
        # Locals is an array which acts as a stack for local variables.
        # Top-level statements behave like being encapsulated in an implicit
        # main()-function, i.e. their variables are not global!
        # I think that we could always use a self.locals.append() whenever
        # new names are pushed on the stack (function arguments and in let
        # statements) but it looks more high-level to access the variables
        # always in the same way, which is: self.locals[symbol_tree.get_index()].
        # To enable this when declaring variables, we use a list that
        # automatically grows.
        #self.globals : typing.Dict[str, ]
        self.locals = StackList()
        # Modules/Imports, custom types and function definitions are accessed through
        # the ast.TranslationUnit directly. The evaluator can access/read the symbol table
        # to identify stuff.
        # Here, initialized empty, filled with content when evaluating.
        self.current_unit = TranslationUnitRef(ast.TranslationUnit([], collections.OrderedDict(), collections.OrderedDict(), [], {}))
        # All imported modules
        self.modules : typing.Dict[str, ast.TranslationUnit] = {}
        # 
        self.symbol_tree = SymbolTree()

    def restore_symbol_tree(self, node : SymbolTreeNode):
        self.symbol_tree.restore_snapshot(node)

    def evaluate(self, node: ast.BaseNode) -> ValueList:
        if isinstance(node, ast.Program):
            # Register all imported modules
            for k, m in node.modules.items():
                self.modules[k] = m
            # Then evaluate the main module/file/input
            return self.evaluate(node.main_unit)
        elif isinstance(node, ast.TranslationUnit):
            # First, retain/copy all function definitions. The other stuff seems
            # not to be required currently.
            # Here, we can not just set the current unit to node to retain
            # function definitions across evaluations in shell mode.
            for k, f in node.function_definitions.items():
                self.current_unit.unit.function_definitions[k] = f
            # Set the current symbol table (which could be a reused one)
            self.current_unit.unit.symbols_global = node.symbols_global
            # Afterwards, run all non-function statements
            res = ValueList([])
            for stmt in node.statements:
                res = self.evaluate(stmt)
                if res.returned():
                    # ast.Program is the top-level-node, return means exit then
                    # https://docs.python.org/3/library/sys.html#sys.exit says:
                    # int -> int, Null -> 0, other -> 1
                    # This behaviour seems reasonable here
                    sys.exit(res[0] if len(res) > 0 else None)
            return res
        elif isinstance(node, ast.Block):
            symtree = self.symbol_tree.take_snapshot()
            result = ValueList([])
            for stmt in node.stmts:
                result = self.evaluate(stmt)
                if result.returned():
                    break
            self.symbol_tree.restore_snapshot(symtree)
            return result
        elif isinstance(node, ast.Return):
            if node.result == None:
                return ValueList([], True)
            result = self.evaluate(node.result)
            result.unwind_return = True
            return result
        elif isinstance(node, ast.IfElseStatement):
            cond = node.cond
            if isTruthy(self.evaluate(cond)):
                return self.evaluate(node.thn)
            elif isinstance(node.els, ast.BaseNode):
                return self.evaluate(node.els)
            return ValueList([])
        elif isinstance(node, ast.WhileStatement):
            ret = ValueList([])
            while isTruthy(self.evaluate(node.cond)):
                ret = self.evaluate(node.t)
                if ret.returned():
                    break
            return ret
        elif isinstance(node, ast.AssignOp):
            values = self.evaluate(node.rhs)
            self.assign(node.lhs, values)
            return values
        elif isinstance(node, ast.BinOp):
            op = node.op
            lhs = self.evaluate(node.lhs)[0]
            rhs = self.evaluate(node.rhs)[0]
            if op == "+":
                res = lhs + rhs
            elif op == "-":
                res = lhs - rhs
            elif op == "*":
                res = lhs * rhs
            elif op == "/":
                if isinstance(lhs, int):
                    res = lhs // rhs
                else:
                    res = lhs / rhs
            elif op == "%":
                res = lhs % rhs
            elif op == "^":
                res = lhs ** rhs
            elif op == "&&":
                res = lhs and rhs
            elif op == "||":
                res = lhs or rhs
            elif op == "==":
                res = lhs == rhs
            elif op == "!=":
                res = lhs != rhs
            elif op == "<":
                res = lhs < rhs
            elif op == ">":
                res = lhs > rhs
            elif op == "<=":
                res = lhs <= rhs
            elif op == ">=":
                res = lhs >= rhs
            else:
                raise Exception("unrecognised operator: " + str(node.op))
            return ValueList([res])
        elif isinstance(node, ast.UnaryOp):
            op = node.op
            if op == "!":
                val = not self.evaluate(node.rhs)[0]
            elif op == "-":
                val = -self.evaluate(node.rhs)[0]
            else:
                raise Exception("unrecognised unary operator: " + str(node.op))
            return ValueList([val])
        elif isinstance(node, ast.Integer):
            return ValueList([node.value])
        elif isinstance(node, ast.Float):
            return ValueList([node.value])
        elif isinstance(node, ast.String):
            return ValueList([node.value])
        elif isinstance(node, ast.Bool):
            return ValueList([node.value])
        elif isinstance(node, ast.SysCall):
            return self.callprogram(node)
        elif isinstance(node, ast.Pipeline):
            if len(node.elements) < 2:
                raise Exception("Pipelines should have more than one element. This seems to be a parser bug.")
            syscalls = []
            # First pipeline element: First syscall or stdin
            if isinstance(node.elements[0], ast.SysCall):
                syscalls.append(node.elements[0])
                stdin = None
            else:
                stdin = self.evaluate(node.elements[0])
            # Other pipeline elements until last: syscalls
            for sc in node.elements[1:-1]:
                assert(isinstance(sc, ast.SysCall))
                syscalls.append(sc)
            # Last pipeline element: Last syscall or stdout (+stderr)
            if isinstance(node.elements[-1], ast.SysCall):
                syscalls.append(node.elements[-1])
                assignto = None
            else:
                assignto = node.elements[-1]
            # Special case: piping an ordinary expression into a variable
            if len(syscalls) == 0:
                raise Exception("The special case, assigning regular values"
                        " via pipelines, is not supported currently.")
                """
                if assignto == None:
                    raise Exception("Assertion error: Whenever a pipeline has no syscalls, it should consist of an expression that is assigned to something. No assignment was found here.")
                self.assign(assignto, stdin)
                return stdin
                """
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
            # Assign stdout,stderr to variables
            #results = ValueList(outstreams[:numOutputPipes])
            results = ValueList([])
            for o in outstreams[:numOutputPipes]:
                results.append(o.decode('utf-8'))
            if isinstance(assignto, ast.PipelineLet): # copied from ast.Let
                if len(assignto.names) != len(results):
                    raise Exception("number of expressions between rhs and lhs do not match")
                self.symbol_tree.restore_snapshot(assignto.symbol_tree_snapshot)
                for name, result in zip(assignto.names, results):
                    index = self.symbol_tree.get_index(name)
                    self.locals[index] = result
            elif isinstance(assignto, ast.ExpressionList):
                self.assign(assignto, results)
            elif isinstance(assignto, ast.BaseNode):
                self.assign(ast.ExpressionList(assignto.tokens, [assignto]), results)
            # Return exitcode of subprocess
            return ValueList([lastProcess.returncode])
        elif isinstance(node, ast.Identifier):
            if node.name in self.symbol_tree:
                index = self.symbol_tree.get_index(node.name)
                return ValueList([self.locals[index]])
            elif node.name in self.current_unit.unit.symbols_global:
                pass
                # TODO Add global environment
            raise Exception(f"Unknown identifier '{node.name}' specified. TODO: global environment.")
        elif isinstance(node, ast.IndexAccess):
            index = self.evaluate(node.rhs)[0]
            lhs = self.evaluate(node.lhs)[0]
            return ValueList([lhs[index]])
        elif isinstance(node, ast.DotAccess):
            # The following is only used for StructValue, modules are only used
            # for module- and function-access which is handled in FunctionCall below.
            val = self.evaluate(node.lhs)[0][node.rhs]
            return ValueList([val])
        elif isinstance(node, ast.FunctionCall):
            # node.name should either be an ast.Identifier, then we call a function
            # in the current module/unit, or an ast.DotAccess, then we call a function
            # in the specified module/unit.
            if isinstance(node.name, ast.Identifier):
                unit = self.current_unit.unit
                funcname = node.name.name
            elif isinstance(node.name, ast.DotAccess):
                unit = self.get_module(node.name.lhs)
                funcname = node.name.rhs
            else:
                raise Exception("Identifier or DotAccess for function name expected.")
            # Change (PUSH) the current unit. We also do this if we call a function
            # in the current unit/module because then we do not have to decide
            # afterwards if we have to pop the translation unit back, we just do it.
            self.current_unit = TranslationUnitRef(unit, self.current_unit)
            try:
                # Evaluate arguments (with old scope)
                # TODO Here, we can maybe use args = self.evaluate(ExprList)
                # instead of building a new array from scratch?
                args = []
                for a in node.args:
                    args.append(self.evaluate(a)[0])
                # Call by value!
                args = copy.deepcopy(args)
                # Call function, either builtin or defined
                if isinstance(unit.symbols_global[funcname], bongtypes.Function):
                    # Bong function
                    function = unit.function_definitions[funcname]
                    symbol_tree_snapshot = self.symbol_tree.take_snapshot()
                    self.symbol_tree.restore_snapshot(function.symbol_tree_snapshot)
                    local_env_snapshot = self.locals
                    self.locals = StackList()
                    try:
                        # Add arguments to new local environment, then eval func
                        for name, arg in zip(function.parameter_names, args):
                            index = self.symbol_tree.get_index(name)
                            self.locals[index] = arg
                        result = self.evaluate(function.body)
                    finally:
                        self.symbol_tree.restore_snapshot(symbol_tree_snapshot)
                        self.locals = local_env_snapshot
                    if result.returned():
                        result.unwind_return = False
                        return result
                    return result
                else:
                    # Builtin function
                    return bong_builtins.functions[funcname][0](args)
            finally:
                # Change back (POP) the current unit
                self.current_unit = self.current_unit.parent
        elif isinstance(node, ast.Print):
            self.printfunc(self.evaluate(node.expr))
        elif isinstance(node, ast.Let):
            # First, evaluate all rhses (those are possibly encapsulated in an
            # ExpressionList, so no need to iterate here
            results = self.evaluate(node.expr)
            # Then, assign results. This order of execution additionally prevents
            # the rhs of a let statement to use the variables declared on the
            # left side.
            if len(node.names) != len(results):
                raise Exception("number of expressions between rhs and lhs do not match")
            self.symbol_tree.restore_snapshot(node.symbol_tree_snapshot)
            for name, result in zip(node.names, results):
                index = self.symbol_tree.get_index(name)
                self.locals[index] = result
        elif isinstance(node, ast.Array):
            elements = []
            for e in node.elements:
                elements.append(self.evaluate(e)[0])
            return ValueList([elements])
        elif isinstance(node, ast.StructValue):
            assert(isinstance(node.name, ast.Identifier)
                    or isinstance(node.name, ast.DotAccess))
            structval = StructValue(node.name)
            for name, expr in node.fields.items():
                structval[name] = self.evaluate(expr)[0]
            return ValueList([structval])
        elif isinstance(node, ast.ExpressionList):
            results = ValueList([])
            for exp in node.elements:
                # ValueList is a FlatList and an append to FlatList is
                # automatically flattened. Not indexing into the result
                # of evaluate() here is crucial because the result could be
                # an empty ValueList (e.g. function calls)
                results.append(self.evaluate(exp))
            return results
        else:
            raise Exception("unknown ast node")
        return ValueList([]) # Satisfy mypy

    def assign(self, lhs: ast.ExpressionList, rhs: ValueList):
        if len(rhs)!=len(lhs):
            raise Exception("number of elements on lhs and rhs does not match")
        for l, value in zip(lhs, rhs):
            # lhs evaluation: The lhs can be a variable assignment, an
            # index access, a DotAccess
            if isinstance(l, ast.Identifier):
                name = l.name
                stack_index = self.symbol_tree.get_index(name)
                self.locals[stack_index] = value
            elif isinstance(l, ast.IndexAccess):
                index_access_index = self.evaluate(l.rhs)[0]
                array = self.evaluate(l.lhs)[0]
                array[index_access_index] = value
            elif isinstance(l, ast.DotAccess):
                struct = self.evaluate(l.lhs)[0]
                struct[l.rhs] = value
            else:
                raise Exception("Can only assign to variable or indexed variable")

    def numInputsExpected(self, assignto):
        if isinstance(assignto, ast.PipelineLet):
            return len(assignto.names)
        elif isinstance(assignto, ast.ExpressionList):
            return len(assignto.elements)
        else: # Currently only used in pipelines, it's a single variable then
            return 1

    def callprogram(self, program, stdin=None, numOutputPipes=0):
        # TODO We pass a whole ast.SysCall object to callprogram, only the args
        # list would be enough. Should we change that? This would simplify this
        # method itself and calling builtin functions.
        #
        # Before doing anything, expand ~ to user's home directory
        cmd = []
        home_directory = os.path.expanduser("~")
        for arg in program.args:
            if arg.startswith("~"):
                arg = home_directory+arg[1:]
            cmd.append(arg)
        # Check bong builtins first. Until now, only 'cd' defined
        if cmd[0] == "cd":
            if stdin != None or numOutputPipes != 0:
                print("bong: cd: can not be piped")
                # TODO Here, the calling pipe will crash :( return something
                # usable instead!
                return None
            return self.call_cd(cmd)
        path_var = os.environ['PATH'].split(':')
        # Special case: Syscalls with relative or absolute path ('./foo', '../foo', '/foo/bar', 'foo/bar')
        if (cmd[0].startswith('./') or
                cmd[0].startswith('../') or
                cmd[0].startswith('/') or
                '/' in cmd[0]):
            path_var = [""]
        for path in path_var:
            if len(path) > 0:
                if not path.endswith('/'):
                    path += "/"
                filepath = path+cmd[0]
            else:
                filepath = cmd[0]
            if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
                # Simple syscall
                if stdin == None and numOutputPipes == 0:
                    compl = subprocess.run(cmd)
                    return compl.returncode
                # Piped syscall
                # lhs = subprocess.Popen(["ls"], stdout=subprocess.PIPE)
                # rhs = subprocess.Popen(["grep", "foo"], stdin=lhs.stdout)
                # lhs.stdout.close()
                # rhs.communicate()
                # -> I call stdout.close() on all but the last subprocesses
                # -> I call communicate() only on the last subprocess
                # TODO Is that actually the right approach?
                else:
                    # a) this is the leftmost syscall of a pipe or
                    # -> Create the process with stdin=None
                    # b) the previous step of the pipe was a syscall
                    # -> Create the process with stdin=stdin
                    # c) lhs of the pipe was variable or function
                    # -> Create the process with stdin=PIPE and write the value into stdin
                    case_a = stdin==None
                    case_b = isinstance(stdin, io.BufferedReader) # _io.Buff...?
                    case_c = not (case_a or case_b)
                    stdin_arg = stdin if not case_c else subprocess.PIPE
                    stdout_arg = subprocess.PIPE if numOutputPipes>0 else None
                    stderr_arg = subprocess.PIPE if numOutputPipes>1 else None
                    proc = subprocess.Popen(
                            cmd, stdin=stdin_arg, stdout=stdout_arg, stderr=stderr_arg)
                    if case_c:
                        # Prevent possible bytestreams from being interpreted
                        # as strings. Currently 2019-12-22, this is not strictly
                        # required because we don't have bytestreams yet and
                        # everything is nicely decoded to strings but in the
                        # future, we have to do this here!
                        if type(stdin) == bytes:
                            proc.stdin.write(stdin)
                        else:
                            proc.stdin.write(str(stdin).encode("utf-8"))
                        #proc.stdin.close()
                    # Now, after having created this process, we can run the
                    # stdout.close() on the previous process (if there was one)
                    # stdout of the previous is stdin here.
                    if isinstance(stdin, io.BufferedReader): # _io.Buff...?
                        stdin.close()
                    return proc
        print("bong: {}: command not found".format(cmd[0]))

    def call_cd(self, args):
        if len(args) > 2:
            print("bong: cd: too many arguments")
            return 1
        try:
            if len(args) > 1:
                if (args[1]=="-"): # Everything bash can do, we can do better.
                    if hasattr(self, "prev_directory"):
                        self.change_dir(self.prev_directory)
                else:
                    self.change_dir(args[1])
            else:
                self.change_dir(os.path.expanduser('~'))
            return 0
        except Exception as e:
            print("bong: cd: {}".format(str(e)))
            return 1
    def change_dir(self, new_dir):
        prev_dir = os.getcwd()
        os.chdir(new_dir) # This can fail so everything else happens afterwards
        self.prev_directory = prev_dir
        # Now, we send the escape codes to tell the terminal (emulator) the
        # new directory
        current_dir = os.getcwd()
        sys.stdout.write("\x1b]7;file:"+current_dir+"\x07") # Tell the cwd to our terminal (emulator)
        home_directory = os.path.expanduser("~")
        if current_dir.startswith(home_directory):
            window_title = "~" + current_dir[len(home_directory):] # ~ + home-dir skipped in current dir
        else:
            window_title = current_dir
        sys.stdout.write("\x1b]2;bong "+window_title+"\x07") # Set the window title

    # Takes an Identifier or DotAccess which should describe a module
    # and returns the corresponding ast.TranslationUnit. The search
    # is started at self.current_unit's symbol table. For each resolution
    # step, another (the next) symbol table is used.
    def get_module(self, name : ast.BaseNode) -> ast.TranslationUnit: # name should be Identifier (returns current_unit) or DotAccess (returns resolved DotAccess.lhs)
        # DotAccesses are forwarded until an Identifier is found. The
        # Identifier uses the current_unit's symbol table to resolve
        # the module. The DotAccesses use the returned units to resolve
        # further modules afterwards.
        if isinstance(name, ast.Identifier):
            module = self.current_unit.unit.symbols_global[name.name]
        elif isinstance(name, ast.DotAccess):
            unit = self.get_module(name.lhs)
            module = unit.symbols_global[name.rhs]
        else:
            raise Exception("Identifier or DotAccess expected.")
        if not isinstance(module, bongtypes.Module):
            raise Exception("Module expected.")
        return self.modules[module.path]

def isTruthy(value):
    if value[0] == True:
        return True
    return False

def ensureValueList(value):
    if not isinstance(value, ValueList):
        return ValueList([value])
    return value

# https://stackoverflow.com/a/4544699
class StackList(list):
    def __setitem__(self, index, value):
        if index >= len(self):
            self.extend(["UninitializedStackValue"]*(index + 1 - len(self)))
        list.__setitem__(self, index, value)

class TranslationUnitRef:
    def __init__(self, unit : ast.TranslationUnit, parent : typing.Optional[TranslationUnitRef] = None):
        self.unit = unit
        self.parent = parent
