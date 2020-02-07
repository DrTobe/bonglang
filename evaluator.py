import ast
from environment import Environment
import objects

# For subprocesses
import os
import subprocess
import _io

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
        for key, value in Eval.BUILTIN_ENVIRONMENT.items():
            self.environment.reg_and_set(key, value)
        self.functions = Environment()
        self.builtin_functions = {
                "call": self.callprogram,
                "len": self.builtin_func_len,
                }

    # Eval.EXITCODE -> "name 'Eval' is not defined" ... But why does it work?
    def evaluate(self, node):
        if isinstance(node, ast.Program):
            for key, value in node.functions.values.items():
                if key in self.builtin_functions:
                    raise(Exception("Cannot overwrite builtin "+key))
                self.functions.reg_and_set(key, value)
            res = None
            for stmt in node.statements:
                res = self.evaluate(stmt)
                if isinstance(res, objects.ReturnValue):
                    break
            return res
        if isinstance(node, ast.Block):
            self.push_new_env()
            result = None
            for stmt in node.stmts:
                result = self.evaluate(stmt)
                if isinstance(result, objects.ReturnValue):
                    break
            self.pop_env()
            return result
        if isinstance(node, ast.IfElseStatement):
            cond = node.cond
            if isTruthy(self.evaluate(cond)):
                return self.evaluate(node.t)
            elif node.e != None:
                return self.evaluate(node.e)
            return None
        if isinstance(node, ast.WhileStatement):
            ret = None
            while isTruthy(self.evaluate(node.cond)):
                ret = self.evaluate(node.t)
                if isinstance(ret, objects.ReturnValue):
                    break
            return ret
        if isinstance(node, ast.Return):
            if node.result == None:
                return objects.ReturnValue()
            result = self.evaluate(node.result)
            return objects.ReturnValue(result)
        if isinstance(node, ast.BinOp):
            op = node.op
            if op == "=":
                return self.assign(node.lhs, node.rhs)
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
            pipeLastOutput = assignto!=None
            lastProcess = self.callprogram(syscalls[-1], stdin, pipeLastOutput)
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
                self.assign(assignto, outstreams[0])
                return lastProcess.returncode
            else:
                return lastProcess.returncode
        elif isinstance(node, ast.Variable):
            return self.environment.get(node.name)
        elif isinstance(node, ast.IndexAccess):
            index = self.evaluate(node.rhs)
            lhs = self.evaluate(node.lhs)
            if isinstance(lhs, str):
                return lhs[index]
            if isinstance(lhs, objects.Array): # bong array
                return lhs.elements[index]
            if isinstance(lhs, list): # sys_argv
                return lhs[index]
            #return self.environment.get(node.lhs.name)[index]
        if isinstance(node, ast.FunctionCall):
            if node.name in self.builtin_functions:
                # TODO Here, code from the lower part of ast.FunctionCall was
                # copied. Bad style ...
                args = []
                for a in node.args:
                    args.append(self.evaluate(a))
                result = self.builtin_functions[node.name](ast.SysCall(args))
                if isinstance(result, objects.ReturnValue):
                    return result.value
                return result
            function = self.functions.get(node.name)
            if not isinstance(function, ast.FunctionDefinition):
                raise Exception("can only call functions")
            if len(function.parameters) != len(node.args):
                raise Exception("wrong number of arguments")
            args = []
            for a in node.args:
                args.append(self.evaluate(a))
            self.push_new_env()
            for i, param in enumerate(function.parameters):
                self.environment.register(param)
                self.environment.set(param, args[i])
            result = self.evaluate(function.body)
            self.pop_env()
            if isinstance(result, objects.ReturnValue):
                return result.value
            return result
        elif isinstance(node, ast.SysCall):
            return self.callprogram(node)
        elif isinstance(node, ast.Print):
            self.printfunc(self.evaluate(node.expr))
        elif isinstance(node, ast.Let):
            # First, evaluate all rhses (those are possibly encapsulated in an 
            # ExpressionList, so no need to iterate here
            results = ensureList(self.evaluate(node.expr))
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
            return objects.Array(elements)
        elif isinstance(node, ast.ExpressionList):
            results = []
            for exp in node.elements:
                results.append(self.evaluate(exp))
            if len(results)==1:
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
            raise Expression("number of elements on lhs and rhs does not match")
        for l, value in zip(lhs, results):
            # 2. lhs evaluation: The lhs can be a variable assignment or an
            # index access which is just handled differently here.
            if isinstance(l, ast.Variable):
                name = l.name
                self.environment.set(name, value)
            elif isinstance(l, ast.IndexAccess):
                index_access = l
                if not isinstance(index_access.lhs, ast.Variable):
                    raise(Exception("Can only index variables"))
                name = index_access.lhs.name
                index = self.evaluate(index_access.rhs)
                self.environment.get(name)[index] = value
            else:
                raise Exception("Can only assign to variable or indexed variable")
        if len(results)==1:
            return results[0]
        return results

    def callprogram(self, program, stdin=None, pipeOutput=False):
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
            if stdin != None or pipeOutput:
                print("bong: cd: can not be piped")
                # TODO Here, the calling pipe will crash :( return something
                # usable instead!
                return None
            return self.call_cd(cmd)
        path_var = os.environ['PATH'].split(':')
        # Special case: Syscalls with relative or absolute path ('./foo', '../foo' and '/foo/bar')
        if cmd[0].startswith('./') or cmd[0].startswith('../') or cmd[0].startswith('/'):
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
                if stdin == None and not pipeOutput:
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
                    case_b = isinstance(stdin, _io.BufferedReader)
                    case_c = not (case_a or case_b)
                    stdin_arg = stdin if not case_c else subprocess.PIPE
                    stdout_arg = subprocess.PIPE if pipeOutput else None
                    proc = subprocess.Popen(
                            cmd, stdin=stdin_arg, stdout=stdout_arg)
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
                    if isinstance(stdin, _io.BufferedReader):
                        stdin.close()
                    return proc
        print("bong: {}: command not found".format(cmd[0]))

    def call_cd(self, args):
        if len(args) > 2:
            print("bong: cd: too many arguments")
            return 1
        try:
            if len(args) > 1:
                os.chdir(args[1])
            else:
                os.chdir(os.path.expanduser('~'))
            return 0
        except Exception as e:
            print("bong: cd: {}".format(str(e)))
            return 1

    def builtin_func_len(self, val):
        return len(val.args[0])

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

def ensureList(value):
    if not isinstance(value, list):
        return [value]
    return value
