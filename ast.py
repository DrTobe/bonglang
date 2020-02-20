import token_def as token
import symbol_table
import typing

class BaseNode:
    def __init__(self):
        if type(self) == BaseNode:
            raise Exception("BaseNode should not be initialized directly")

class Program(BaseNode):
    def __init__(self, statements : typing.List[BaseNode], symbol_table : symbol_table.SymbolTable):
        self.statements = statements
        self.symbol_table = symbol_table
    def __str__(self):
        result = []
        for stmt in self.statements:
            result.append(str(stmt))
        return "{\n" + "\n".join(result) + "\n}"

class Block(BaseNode):
    def __init__(self, stmts : typing.List[BaseNode], symbol_table : symbol_table.SymbolTable):
        self.stmts = stmts
        self.symbol_table = symbol_table
    def __str__(self):
        result = []
        for stmt in self.stmts:
            result.append(str(stmt))
        return "{\n" + "\n".join(result) + "\n}"

class BinOp(BaseNode):
    def __init__(self, lhs, op, rhs):
        self.lhs = lhs
        self.op = op
        self.rhs = rhs
    def __str__(self):
        return "("+str(self.lhs)+self.op+str(self.rhs)+")"

class UnaryOp(BaseNode):
    def __init__(self, op, rhs):
        self.op = op
        self.rhs = rhs
    def __str__(self):
        return "("+str(self.op)+str(self.rhs)+")"

class Integer(BaseNode):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)

class Float(BaseNode):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)

class String(BaseNode):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)

class Bool(BaseNode):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return "true" if self.value == True else "false"

class Variable(BaseNode):
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name

class IndexAccess(BaseNode):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs
    def __str__(self):
        return str(self.lhs) + "[" + str(self.rhs) + "]"

class Print(BaseNode):
    def __init__(self, expr):
        self.expr = expr
    def __str__(self):
        return "print "+str(self.expr)+";"

class ExpressionList(BaseNode):
    def __init__(self, elements : typing.List[BaseNode]):
        self.elements : typing.List[BaseNode] = elements
    def append(self, element : BaseNode):
        self.elements.append(element)
    def __str__(self):
        return ", ".join(map(str,self.elements))

class Let(BaseNode):
    def __init__(self, names : typing.List[str], expr : BaseNode):
        self.names : typing.List[str] = names
        self.expr : BaseNode = expr
    def __str__(self):
        names = ", ".join(self.names)
        return "let " + names + " = " + str(self.expr)

class IfElseStatement(BaseNode):
    def __init__(self, cond : BaseNode, t : Block, e : BaseNode = None): # actually, it is: typing.Union[None, Block, IfElseStatement] = None):
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

class WhileStatement(BaseNode):
    def __init__(self, cond, t):
        self.cond = cond
        self.t = t
    def __str__(self):
        return "while {} {}".format(str(self.cond), str(self.t))

class Pipeline(BaseNode):
    def __init__(self, elements, nonblocking):
        self.elements = elements
        self.nonblocking = nonblocking
    def __str__(self):
        pipeline = " | ".join(map(str,self.elements))
        if self.nonblocking:
            pipeline += " &"
        return pipeline

class PipelineLet(BaseNode):
    def __init__(self, names):
        self.names = names
    def __str__(self):
        names = ", ".join(self.names)
        return "let " + names

class SysCall(BaseNode):
    def __init__(self, args):
        self.args = args
    def __str__(self):
        return "(call " + " ".join(self.args) + ")"

class FunctionDefinition(BaseNode):
    def __init__(self, name : str, parameter_names : typing.List[str], parameter_types : typing.List[str], return_types : typing.List[str], body : Block, symbol_table : symbol_table.SymbolTable):
        self.name = name
        self.parameter_names = parameter_names
        self.parameter_types = parameter_types
        self.return_types = return_types
        self.body = body
        self.symbol_table = symbol_table
    def __str__(self):
        parameters = []
        for name, typ in zip(self.parameter_names, self.parameter_types):
            parameters.append(name + " : " + typ)
        result = self.name + "("
        result += ", ".join(parameters)
        result += ") "
        if len(self.return_types) > 0:
            result += ": " + ", ".join(self.return_types) + " "
        result += str(self.body)
        return result

class FunctionCall(BaseNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args
    def __str__(self):
        result = self.name + "("
        args = []
        for a in self.args:
            args.append(str(a))
        result += ", ".join(args)
        result += ")"
        return result

class Return(BaseNode):
    def __init__(self, result=None):
        self.result = result
    def __str__(self):
        result = "return"
        if self.result != None:
            result += " "
            result += str(self.result)
        return result

class Array(BaseNode):
    def __init__(self, elements):
        self.elements = elements
    def __str__(self):
        elements = []
        for e in self.elements:
            elements.append(str(e))
        result = "["
        result += ", ".join(elements)
        result += "]"
        return result
