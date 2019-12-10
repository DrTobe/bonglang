import token_def as token

class Program:
    def __init__(self, stmts):
        self.stmts = stmts
    def __str__(self):
        result = []
        for stmt in self.stmts:
            result.append(str(stmt))
        return "\n".join(result) + "\n"

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

class Bool:
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return "true" if self.value == True else "false"

class Variable:
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return name

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
