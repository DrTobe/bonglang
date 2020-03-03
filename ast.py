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
        """ Alternative string representation that contains the symbol table, too
        program = "Program {\n"
        program += str(self.symbol_table) + "\n"
        stmts = []
        for stmt in self.statements:
            stmts.append(str(stmt))
        stmts = "Statements:\n" + "\n".join(stmts)
        program += stmts + "\n} EOP"
        return program
        """
        stmts = []
        for stmt in self.statements:
            stmts.append(str(stmt))
        return "{\n" + "\n".join(stmts) + "\n}"

class Block(BaseNode):
    def __init__(self, stmts : typing.List[BaseNode], symbol_table : symbol_table.SymbolTable):
        self.stmts = stmts
        self.symbol_table = symbol_table
    def __str__(self):
        result = []
        for stmt in self.stmts:
            result.append(str(stmt))
        return "{\n" + "\n".join(result) + "\n}"

class Import(BaseNode):
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
    def __str__(self):
        return "import " + self.path + " as " + self.name;

class Return(BaseNode):
    def __init__(self, result=None):
        self.result = result
    def __str__(self):
        result = "return"
        if self.result != None:
            result += " "
            result += str(self.result)
        return result

class BinOp(BaseNode):
    def __init__(self, lhs : BaseNode, op : str, rhs : BaseNode):
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

# TODO Convert to builtin function
class Print(BaseNode):
    def __init__(self, expr):
        self.expr = expr
    def __str__(self):
        return "print "+str(self.expr)+";"

# TODO Very similar to bongtypes.TypeList! Can this be generalized to
# FlatList that ExpressionList and TypeList inherit from?
class ExpressionList(BaseNode):
    def __init__(self, elements : typing.List[BaseNode]):
        self.elements : typing.List[BaseNode] = elements
    # Flattened append (no ExpressionList inside an ExpressionList)
    def append(self, node : BaseNode):
        if isinstance(node,ExpressionList):
            explist = typing.cast(ExpressionList,node)
            for elem in explist.elements:
                self.elements.append(elem)
        else:
            self.elements.append(node)
    # The next two methods for index-access and length
    def __len__(self):
        return len(self.elements)
    def __getitem__(self, index):
        return self.elements[index]
    # The next two methods make this class iterable
    def __iter__(self):
        self.iterationCounter = -1
        return self
    def __next__(self):
        self.iterationCounter += 1
        if self.iterationCounter < len(self.elements):
            return self.elements[self.iterationCounter]
        raise StopIteration
    def __str__(self):
        return ", ".join(map(str,self.elements))

class Let(BaseNode):
    def __init__(self, names : typing.List[str], expr : ExpressionList):
        self.names = names
        self.expr = expr
    def __str__(self):
        names = ", ".join(self.names)
        return "let " + names + " = " + str(self.expr)

class IfElseStatement(BaseNode):
    def __init__(self, cond : BaseNode, thn : Block, els : BaseNode = None): # actually, it is: typing.Union[None, Block, IfElseStatement] = None):
        self.cond = cond
        self.thn = thn
        self.els = els
    def __str__(self):
        result = "if "
        result += str(self.cond)
        result += " "
        result += str(self.thn)
        if self.els != None:
            result += " else "
            result += str(self.els)
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

class Array(BaseNode):
    def __init__(self, elements : ExpressionList):
        self.elements = elements
    def __str__(self):
        elements = []
        for e in self.elements:
            elements.append(str(e))
        result = "["
        result += ", ".join(elements)
        result += "]"
        return result
