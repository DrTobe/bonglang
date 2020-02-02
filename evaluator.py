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
    # Poor man's python enum :)
    # Determines what a syscall should return
    EXITCODE = 0
    PIPE = 1
    VALUE = 2
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
    def evaluate(self, node, stdin=None, stdout=EXITCODE):
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
        elif isinstance(node, ast.Pipe):
            if isinstance(node.rhs, ast.SysCall):
                pipe = Eval.PIPE
            else:
                pipe = Eval.VALUE
            lhs = self.evaluate(node.lhs, stdin=stdin, stdout=pipe)
            return self.evaluate(node.rhs, stdin=lhs, stdout=stdout)
        elif isinstance(node, ast.Variable):
            if stdin != None: # oops, piped input :)
                return self.assign(node, stdin)
            return self.environment.get(node.name)
        elif isinstance(node, ast.IndexAccess):
            if stdin != None:
                return self.assign(node, stdin)
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
                result = self.builtin_functions[node.name](ast.SysCall(args), stdin, stdout)
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
            return self.callprogram(node, stdin, stdout)
        elif isinstance(node, ast.Print):
            self.printfunc(self.evaluate(node.expr))
        elif isinstance(node, ast.Let):
            self.environment.register(node.name)
            self.environment.set(node.name, self.evaluate(node.expr))
        elif isinstance(node, ast.Array):
            elements = []
            for e in node.elements:
                elements.append(self.evaluate(e))
            return objects.Array(elements)
        else:
            raise Exception("unknown ast node")

    def assign(self, lhs, rhs):
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
        if (isinstance(rhs, bytes) or
                isinstance(rhs, bool) or
                isinstance(rhs, int) or
                isinstance(rhs, str)):
            # TODO The following distinction is just made so that we can work
            # nicely with syscall output. Done properly, the value would just
            # by a bytestream that has to be decoded by the user.
            if isinstance(rhs, bytes):
                value = rhs.decode("utf-8")
            else:
                value = rhs
        else:
            value = self.evaluate(rhs)
        # 2. lhs evaluation: The lhs can be a variable assignment or an
        # index access which is just handled differently here.
        if isinstance(lhs, ast.Variable):
            name = lhs.name
            self.environment.set(name, value)
            return value
        if isinstance(node.lhs, ast.IndexAccess):
            index_access = node.lhs
            if not isinstance(index_access.lhs, ast.Variable):
                raise(Exception("Can only index variables"))
            name = index_access.lhs.name
            index = self.evaluate(index_access.rhs)
            self.environment.get(name)[index] = value
            return value
        raise Exception("Can only assign to variable or indexed variable")

    def callprogram(self, program, stdin, stdout):
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
            if stdin != None or stdout!=Eval.EXITCODE:
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
                # TODO It seems to me that this distinction between simple
                # syscalls and piped syscalls can be removed. Let's try that
                # soon!
                # Simple syscall
                if stdin == None and stdout==Eval.EXITCODE:
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
                    # b) the previous step of the pipe was a syscall
                    # -> just create the process
                    # c) lhs of the pipe was variable or function
                    # -> create the process and write the value into stdin
                    case_c = not (stdin==None or                   # a)
                            isinstance(stdin, _io.BufferedReader)) # b)
                    stdin_arg = stdin if not case_c else subprocess.PIPE
                    stdout_arg = subprocess.PIPE if stdout!=Eval.EXITCODE else None
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
                    # Now, after having created this process, we can run the
                    # stdout.close() on the previous process (if there was one)
                    # stdout of the previous is stdin here.
                    if isinstance(stdin, _io.BufferedReader):
                        stdin.close()
                    # a) output should not be piped
                    # -> evaluate the subprocess, return what is requested
                    # b) output should be piped
                    # -> return the pipe
                    if stdout==Eval.EXITCODE:
                        proc.communicate()
                        return proc.returncode
                    elif stdout==Eval.VALUE:
                        return proc.communicate()[0]
                    else:
                        return proc.stdout
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

    def builtin_func_len(self, val, stdin, stdout):
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
