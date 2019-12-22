import ast
from environment import Environment
import objects

# For subprocesses
import os
import subprocess
import _io

class Eval:
    # Poor man's python enum :)
    # Determines what a syscall should return
    EXITCODE = 0
    PIPE = 1
    VALUE = 2
    def __init__(self, printfunc=print):
        self.environment = Environment()
        self.printfunc = printfunc
        self.functions = Environment()

    # Eval.EXITCODE -> "name 'Eval' is not defined" ... But why does it work?
    def evaluate(self, node, stdin=None, stdout=EXITCODE):
        if isinstance(node, ast.Program):
            self.functions.add_definitions(node.functions)
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
                if isinstance(node.lhs, ast.Variable):
                    name = node.lhs.name
                    value = self.evaluate(node.rhs)
                    self.environment.set(name, value)
                    return value
                if isinstance(node.lhs, ast.IndexAccess):
                    # 1. Evaluate value (rhs)
                    value = self.evaluate(node.rhs)
                    # 2. Evaluate index which is on the lhs of the assignment
                    index_access = node.lhs
                    if not isinstance(index_access.lhs, ast.Variable):
                        raise(Exception("Can only index variables"))
                    name = index_access.lhs.name
                    index = self.evaluate(index_access.rhs)
                    self.environment.get(name)[index] = value
                raise Exception("Can only assign to variable or indexed variable")
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
            return self.environment.get(node.name)
        elif isinstance(node, ast.IndexAccess):
            index = self.evaluate(node.rhs)
            return self.environment.get(node.lhs.name)[index]
        if isinstance(node, ast.FunctionCall):
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
        else:
            raise Exception("unknown ast node")

    def callprogram(self, program, stdin, stdout):
        if program.args[0] == "cd":
            if stdin != None or stdout!=Eval.EXITCODE:
                print("bong: cd: can not be piped")
                # TODO Here, the calling pipe will crash :( return something
                # usable instead!
                return None
            return self.call_cd(program.args)
        path_var = os.environ['PATH'].split(':')
        # Special case: Syscalls with relative or absolute path ('./foo', '../foo' and '/foo/bar')
        if program.args[0].startswith('./') or program.args[0].startswith('../') or program.args[0].startswith('/'):
            path_var = [""]
        for path in path_var:
            if len(path) > 0:
                if not path.endswith('/'):
                    path += "/"
                filepath = path+program.args[0]
            else:
                filepath = program.args[0]
            if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
                # TODO It seems to me that this distinction between simple
                # syscalls and piped syscalls can be removed. Let's try that
                # soon!
                # Simple syscall
                if stdin == None and stdout==Eval.EXITCODE:
                    compl = subprocess.run(program.args)
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
                            program.args, stdin=stdin_arg, stdout=stdout_arg)
                    if case_c:
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
        print("bong: {}: command not found".format(program.args[0]))

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
