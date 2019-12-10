import ast

# For subprocesses
import os
import subprocess

class Eval:
    def __init__(self, printfunc=print):
        self.variables = {}
        self.printfunc = printfunc

    def evaluate(self, program):
        if isinstance(program, ast.BinOp):
            op = program.op
            lhs = self.evaluate(program.lhs)
            rhs = self.evaluate(program.rhs)
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
                raise Exception("unrecognised operator: " + str(program.op))
        elif isinstance(program, ast.UnaryOp):
            op = program.op
            if op == "!":
                return not self.evaluate(program.rhs)
            if op == "-":
                return -self.evaluate(program.rhs)
            raise Exception("unrecognised unary operator: " + str(program.op))
        elif isinstance(program, ast.Integer):
            return program.value
        elif isinstance(program, ast.Bool):
            return program.value
        elif isinstance(program, ast.Variable):     # for identifiers, ...
            if program.name in self.variables:      # ... try variables first
                return self.variables[program.name]
            else:                                   # ... external call then
                return self.callprogram(program)
        elif isinstance(program, ast.Print):
            self.printfunc(self.evaluate(program.expr))
        elif isinstance(program, ast.Let):
            self.variables[program.name] = self.evaluate(program.expr)

    def callprogram(self, program):
        path_var = ["/usr/local/bin", "/usr/bin", "/bin", "/usr/local/sbin"]
        for path in path_var:
            filepath = path+"/"+program.name
            if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
                compl = subprocess.run(program.name)
                return compl.returncode
        print("bong: {}: command not found".format(program.name))

