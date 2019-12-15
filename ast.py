import token_def as token

class Program:
    def __init__(self, body, functions):
        self.body = body
        self.functions = functions
    def __str__(self):
        return str(self.body)

class Block:
    def __init__(self, stmts, symbol_table):
        self.stmts = stmts
        self.symbol_table = symbol_table
    def __str__(self):
        result = []
        for stmt in self.stmts:
            result.append(str(stmt))
        return "{\n" + "\n".join(result) + "\n}"

class BinOp:
    def __init__(self, lhs, op, rhs):
        self.lhs = lhs
        self.op = op
        self.rhs = rhs
    def __str__(self):
        return "("+str(self.lhs)+self.op+str(self.rhs)+")"

class UnaryOp:
    def __init__(self, op, rhs):
        self.op = op
        self.rhs = rhs
    def __str__(self):
        return "("+str(self.op)+str(self.rhs)+")"

class Integer:
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)

class String:
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)

class Bool:
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return "true" if self.value == True else "false"

class Variable:
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name

class Print:
    def __init__(self, expr):
        self.expr = expr
    def __str__(self):
        return "print "+str(self.expr)+";"

class Let:
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr
    def __str__(self):
        return "let " + self.name + " = " + str(self.expr)

class IfElseStatement:
    def __init__(self, cond, t, e=None):
        self.cond = cond
        self.t = t
        self.e = e
    def __str__(self):
        result = "if "
        result += str(self.cond)
        result += " "
        result += str(self.t)
        if self.e != None:
            result += " else "
            result += str(self.e)
        return result

class WhileStatement:
    def __init__(self, cond, t):
        self.cond = cond
        self.t = t
    def __str__(self):
        return "while {} {}".format(str(self.cond), str(self.t))

class Pipe:
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs
    def __str__(self):
        return "{} | {}".format(str(self.lhs), str(self.rhs))

class SysCall:
    def __init__(self, args):
        self.args = args
    def __str__(self):
        return "(call " + " ".join(self.args) + ")"

class FunctionDefinition:
    def __init__(self, name, parameters, body, symbol_table):
        self.name = name
        self.parameters = parameters
        self.body = body
        self.symbol_table = symbol_table
    def __str__(self):
        result = self.name + "("
        result += ", ".join(self.parameters)
        result += ") "
        result += str(self.body)
        return result

class FunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args
    def __str__(self):
        result = self.name + "("
        args = []
        for a in self.args:
            args.append(str(s))
        result += ", ".join(args)
        result += ")"
        return result
