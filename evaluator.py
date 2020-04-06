import ast
from environment import Environment
import bong_builtins
from flatlist import FlatList
from collections import UserDict

# For subprocesses
import os
import subprocess
import io

# For cmdline arguments
import sys

class Eval:
    # Defined here so that it can be used by the parser
    BUILTIN_ENVIRONMENT = {
                "sys_argv": sys.argv
            }
    def __init__(self, printfunc=print):
        self.printfunc = printfunc
        self.environment = Environment()
        self.functions = Environment()
        # Register all builtin-functions in the environment
        for bfuncname, bfunc in bong_builtins.functions.items():
            #if not self.functions.exists(bfuncname): # For re-using in shell mode
            self.functions.reg_and_set(bfuncname, bfunc[0])

    def evaluate(self, node):
        if isinstance(node, ast.TranslationUnit):
            # Register all functions in the environment before evaluating the
            # top-level-statements
            toplevel_statements = []
            for statement in node.statements:
                if isinstance(statement, ast.StructDefinition):
                    pass
                elif isinstance(statement, ast.FunctionDefinition):
                    func = statement
                    self.functions.reg_and_set(func.name, func)
                else:
                    toplevel_statements.append(statement)
            res = None
            # Afterwards, run all non-function statements
            for stmt in toplevel_statements:
                res = self.evaluate(stmt)
                if isinstance(res, ReturnValue):
                    # ast.Program is the top-level-node, return means exit then
                    # https://docs.python.org/3/library/sys.html#sys.exit says:
                    # int -> int, Null -> 0, other -> 1
                    # This behaviour seems reasonable here
                    sys.exit(res.value)
            return res
        if isinstance(node, ast.Block):
            self.push_new_env()
            result = None
            for stmt in node.stmts:
                result = self.evaluate(stmt)
                if isinstance(result, ReturnValue):
                    break
            self.pop_env()
            return result
        if isinstance(node, ast.Return):
            if node.result == None:
                return ReturnValue()
            result = self.evaluate(node.result)
            return ReturnValue(result)
        if isinstance(node, ast.IfElseStatement):
            cond = node.cond
            if isTruthy(self.evaluate(cond)):
                return self.evaluate(node.thn)
            elif node.els != None:
                return self.evaluate(node.els)
            return None
        if isinstance(node, ast.WhileStatement):
            ret = None
            while isTruthy(self.evaluate(node.cond)):
                ret = self.evaluate(node.t)
                if isinstance(ret, ReturnValue):
                    break
            return ret
        if isinstance(node, ast.AssignOp):
            return self.assign(node.lhs, node.rhs)
        if isinstance(node, ast.BinOp):
            op = node.op
            lhs = self.evaluate(node.lhs)
            rhs = self.evaluate(node.rhs)
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
                return lhs and rhs
            if op == "||":
                return lhs or rhs
            if op == "==":
                return lhs == rhs
            if op == "!=":
                return lhs != rhs
            if op == "<":
                return lhs < rhs
            if op == ">":
                return lhs > rhs
            if op == "<=":
                return lhs <= rhs
            if op == ">=":
                return lhs >= rhs
            else:
                raise Exception("unrecognised operator: " + str(node.op))
        elif isinstance(node, ast.UnaryOp):
            op = node.op
            if op == "!":
                return not self.evaluate(node.rhs)
            if op == "-":
                return -self.evaluate(node.rhs)
            raise Exception("unrecognised unary operator: " + str(node.op))
        elif isinstance(node, ast.Integer):
            return node.value
        elif isinstance(node, ast.Float):
            return node.value
        elif isinstance(node, ast.String):
            return node.value
        elif isinstance(node, ast.Bool):
            return node.value
        elif isinstance(node, ast.SysCall):
            return self.callprogram(node)
        elif isinstance(node, ast.Pipeline):
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
        elif isinstance(node, ast.Identifier):
            return self.environment.get(node.name)
        elif isinstance(node, ast.IndexAccess):
            index = self.evaluate(node.rhs)
            lhs = self.evaluate(node.lhs)
            return lhs[index]
        elif isinstance(node, ast.DotAccess):
            return self.evaluate(node.lhs)[node.rhs]
        if isinstance(node, ast.FunctionCall):
            assert(isinstance(node.name, ast.Identifier)) # TODO this changes with modules
            funcname = node.name.name
            function = self.functions.get(funcname)
            if isinstance(function, ast.FunctionDefinition):
                # TODO Obsolete thanks to typechecker?
                if len(function.parameter_names) != len(node.args):
                    raise Exception("wrong number of arguments")
            args = []
            for a in node.args:
                args.append(self.evaluate(a))
            if isinstance(function, ast.FunctionDefinition):
                # Bong function
                self.push_new_env()
                try:
                    for i, param in enumerate(function.parameter_names):
                        self.environment.register(param)
                        self.environment.set(param, args[i])
                    result = self.evaluate(function.body)
                finally:
                    self.pop_env()
                if isinstance(result, ReturnValue):
                    return result.value
                return result
            else:
                # Builtin function
                return function(args)
        elif isinstance(node, ast.Print):
            self.printfunc(self.evaluate(node.expr))
        elif isinstance(node, ast.Let):
            # First, evaluate all rhses (those are possibly encapsulated in an
            # ExpressionList, so no need to iterate here
            results = ensureValueList(self.evaluate(node.expr))
            # Then, assign results. This order of execution additionally prevents
            # the rhs of a let statement to use the variables declared on the
            # left side.
            if len(node.names) != len(results):
                raise Exception("number of expressions between rhs and lhs do not match")
            for name, result in zip(node.names,results):
                self.environment.register(name)
                self.environment.set(name, result)
        elif isinstance(node, ast.Array):
            elements = []
            for e in node.elements:
                elements.append(self.evaluate(e))
            return elements
        elif isinstance(node, ast.StructValue):
            structval = StructValue(node.name)
            for name, expr in node.fields.items():
                structval[name] = self.evaluate(expr)
            return structval
        elif isinstance(node, ast.ExpressionList):
            results = ValueList([])
            for exp in node.elements:
                results.append(self.evaluate(exp))
            if len(results)==1: # TODO Maybe switch to always return ValueLists like with TypeLists in typechecker?
                return results[0]
            return results
        else:
            raise Exception("unknown ast node")

    def assign(self, lhs, rhs):
        if isinstance(rhs, ast.ExpressionList):
            rhs = rhs.elements
        elif not isinstance(rhs, list):
            rhs = [rhs]
        if isinstance(lhs, ast.ExpressionList):
            lhs = lhs.elements
        elif isinstance(lhs, ast.PipelineLet):
            let = lhs
            lhs = []
            for name in let.names:
                # It's not strictly correct to already register the variable here
                # because they could be accessed during evaluation of the rhses
                # but it is the end of a pipeline so the rhses are already evaled.
                self.environment.register(name)
                lhs.append(ast.Identifier(let.tokens, name)) # ugly :( 'let' is required because we can not instantiate an ast node without inner elements, but that's not the only ugly thing here :)
        elif not isinstance(lhs, list):
            lhs = [lhs]
        # First, evaluate all rhses, then assign to all lhses
        results = []
        for r in rhs:
            # In typical assignments, the rhs is evaluated first (this distinction
            # is especially necessary if lhs and rhs contain expressions with
            # possible side-effects and the lhs contains an IndexAccess)
            #
            # 1. rhs evaluation: The rhs can be an expression or it can be the
            # output value of a pipeline.
            # Therefore, we need to check vs the list of python types that an
            # Eval.evaluate() call could return.
            # TODO I feel that there could be a nicer way to do this, but
            # I don't see it yet.
            if (isinstance(r, bytes) or
                    isinstance(r, bool) or
                    isinstance(r, int) or
                    isinstance(r, str)):
                # TODO The following distinction is just made so that we can work
                # nicely with syscall output. Done properly, the value would just
                # by a bytestream that has to be decoded by the user.
                if isinstance(r, bytes):
                    value = r.decode("utf-8")
                else:
                    value = r
            else:
                value = self.evaluate(r)
            results.append(value)
        if len(results)!=len(lhs):
            raise Exception("number of elements on lhs and rhs does not match")
        for l, value in zip(lhs, results):
            # 2. lhs evaluation: The lhs can be a variable assignment or an
            # index access which is just handled differently here.
            if isinstance(l, ast.Identifier):
                name = l.name
                self.environment.set(name, value)
            elif isinstance(l, ast.IndexAccess):
                index_access = l
                if not isinstance(index_access.lhs, ast.Identifier):
                    raise(Exception("Can only index variables"))
                name = index_access.lhs.name
                index = self.evaluate(index_access.rhs)
                self.environment.get(name)[index] = value
            else:
                raise Exception("Can only assign to variable or indexed variable")
        if len(results)==1:
            return results[0]
        return results

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

    def push_env(self, new_env):
        current_env = self.environment
        self.environment = new_env
        return current_env

    def push_new_env(self):
        return self.push_env(Environment(self.environment))

    def pop_env(self):
        self.environment = self.environment.parent

def isTruthy(value):
    if value == None or value == False:
        return False
    return True

class ValueList(FlatList):
    def __init__(self, elements):
        super().__init__(elements)
    def __str__(self):
        return ", ".join(map(str,self.elements))

def ensureValueList(value):
    if not isinstance(value, ValueList):
        return ValueList([value])
    return value

class ReturnValue:
    def __init__(self, value=None):
        self.value = value
    def __eq__(self, other):
        if other == None: # Comparing to None should be possible without error message
            return False
        if not isinstance(other, ReturnValue):
            print("dont compare this")
            return False
        return self.value == other.value
    def __str__(self):
        result = "ReturnValue"
        if self.value != None:
            result += " "
            result += str(self.value)
        return result

class StructValue(UserDict):
    def __init__(self, name : ast.BaseNode): # name should be Identifier or DotAccess
        super().__init__()
        self.name = name
    def __str__(self):
        fields = []
        for name, value in self.data.items():
            fields.append(name + " : " + str(value))
        return str(self.name) + " { " + ", ".join(sorted(fields)) + " }"
