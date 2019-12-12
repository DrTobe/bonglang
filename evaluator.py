import ast

# For subprocesses
import os
import subprocess
from symbol_table import SymbolTable

class Eval:
    def __init__(self, printfunc=print):
        self.variables = SymbolTable(None)
        self.printfunc = printfunc

    def evaluate(self, node):
        if isinstance(node, ast.Block):
            self.variables = node.symbol_table
            result = None
            for stmt in node.stmts:
                result = self.evaluate(stmt)
            self.variables = node.symbol_table.parent
            return result
        if isinstance(node, ast.IfElseStatement):
            cond = node.cond
            if self.evaluate(cond):
                return self.evaluate(node.t)
            elif node.e != None:
                return self.evaluate(node.e)
            return None
        if isinstance(node, ast.WhileStatement):
            ret = None
            while self.evaluate(node.cond):
                ret = self.evaluate(node.t)
            return ret
        if isinstance(node, ast.BinOp):
            op = node.op
            if op == "=":
                if not isinstance(node.lhs, ast.Variable):
                    raise Exception("Fucker")
                name = node.lhs.name
                value = self.evaluate(node.rhs)
                self.variables.get(name).value = value
                return value
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
        elif isinstance(node, ast.Bool):
            return node.value
        elif isinstance(node, ast.Variable):
            return self.variables.get(node.name).value
        elif isinstance(node, ast.SysCall):
            return self.callprogram(node)
        elif isinstance(node, ast.Print):
            self.printfunc(self.evaluate(node.expr))
        elif isinstance(node, ast.Let):
            self.variables.get(node.name).value = self.evaluate(node.expr)

    def callprogram(self, program):
        if program.args[0] == "cd":
            return self.call_cd(program.args)
        path_var = ["/usr/local/bin", "/usr/bin", "/bin", "/usr/local/sbin"]
        for path in path_var:
            filepath = path+"/"+program.args[0]
            if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
                compl = subprocess.run(program.args)
                return compl.returncode
        print("bong: {}: command not found".format(program.args[0]))

    def call_cd(self, args):
        if len(args) > 2:
            print("bong: cd: too many arguments")
            return 1
        try:
            os.chdir(args[1])
            return 0
        except Exception as e:
            print("bong: cd: {}".format(e.strerror))
            return 1
