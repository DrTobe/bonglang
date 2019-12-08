import ast

class Eval:
    def __init__(self):
        self.variables = {}
    def evaluate(self, program):
        if isinstance(program, ast.BinOp):
            lhs = self.evaluate(program.lhs)
            rhs = self.evaluate(program.rhs)
            if program.op == "+":
                return lhs + rhs
            elif program.op == "-":
                return lhs - rhs
            if program.op == "*":
                return lhs * rhs
            if program.op == "/":
                return lhs // rhs
            if program.op == "%":
                return lhs % rhs
            if program.op == "^":
                return lhs ** rhs
            if program.op == "&&":
                return lhs and rhs
            if program.op == "||":
                return lhs or rhs
            if program.op == "==":
                return lhs == rhs
            if program.op == "!=":
                return lhs != rhs
            if program.op == "<":
                return lhs < rhs
            if program.op == ">":
                return lhs > rhs
            if program.op == "<=":
                return lhs <= rhs
            if program.op == ">=":
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
        elif isinstance(program, ast.Variable):
            return self.variables[program.name]
        elif isinstance(program, ast.Print):
            print(self.evaluate(program.expr))
        elif isinstance(program, ast.Let):
            self.variables[program.name] = self.evaluate(program.expr)
