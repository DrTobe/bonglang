import token_def as token
from token_def import Token
import symbol_table
import typing
import bongtypes
from flatlist import FlatList
import functools # reduce
import itertools # chain
import sys

# A "location" of tokens/nodes is defined as
# tuple: filename, line from, col from, line to, col to.
# values are inclusive (col from == col to for a one-char token/node)
Location = typing.Tuple[str, int, int, int, int]

class BaseNode:
    def __init__(self, tokens : typing.List[token.Token], inner_nodes): # inner_nodes : List[BaseNode]
        if type(self) == BaseNode:
            raise Exception("BaseNode should not be initialized directly")
        # Assert inner_nodes : typing.List[BaseNode] manually
        assert isinstance(inner_nodes, list)
        if len(inner_nodes):
            assert isinstance(inner_nodes[0], BaseNode)
        if len(tokens) + len(inner_nodes) == 0:
            raise Exception("An ast node needs at least one inner item"
                    " (token or other ast nodes) so that a location of this"
                    " ast node can be determined.")
        self.tokens = tokens
        self.inner_nodes = inner_nodes

    def get_location(self) -> Location:
        return functools.reduce(location_minmax, itertools.chain(map(tok2loc, self.tokens), map(nod2loc, self.inner_nodes)))

def tok2loc(tok : Token) -> Location:
    """
        self.filepath = filepath
        self.line = line
        self.col = col
        self.length = length
    """
    return (tok.filepath, tok.line, tok.col, tok.line, tok.col+tok.length-1)
def nod2loc(node : BaseNode) -> Location:
    return node.get_location()
def location_minmax(lhs : Location, rhs : Location) ->  Location:
    if lhs[0] != rhs[0]:
        print("Filenames of tokens / ast-nodes do not match! Using filename of leftmost item.", file=sys.stderr)
    if lhs[1] < rhs[1]:
        minline, mincol = lhs[1], lhs[2]
    elif rhs[1] < lhs[1]:
        minline, mincol = rhs[1], rhs[2]
    else:
        minline, mincol = lhs[1], min(lhs[2], rhs[2])
    if lhs[3] > rhs[3]:
        maxline, maxcol = lhs[3], lhs[4]
    elif rhs[3] > lhs[3]:
        maxline, maxcol = rhs[3], rhs[4]
    else:
        maxline, maxcol = lhs[3], max(lhs[4], rhs[4])
    return (lhs[0], minline, mincol, maxline, maxcol)

class Program(BaseNode):
    def __init__(self, statements : typing.List[BaseNode], symbol_table : symbol_table.SymbolTable):
        super().__init__([] if len(statements) else [token.Token(token.BONG, "", 0, 0, 0)], statements) # Prevent ast node without inner items
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
    def __init__(self, tokens : typing.List[Token], stmts : typing.List[BaseNode], symbol_table : symbol_table.SymbolTable):
        super().__init__(tokens, stmts)
        self.stmts = stmts
        self.symbol_table = symbol_table
    def __str__(self):
        result = []
        for stmt in self.stmts:
            result.append(str(stmt))
        return "{\n" + "\n".join(result) + "\n}"

class Import(BaseNode):
    def __init__(self, tokens : typing.List[Token], name: str, path: str):
        super().__init__(tokens, [])
        self.name = name
        self.path = path
    def __str__(self):
        return "import " + self.path + " as " + self.name;

class Return(BaseNode):
    def __init__(self, tokens : typing.List[Token], result=None):
        super().__init__(tokens, [result] if result!=None else [])
        self.result = result
    def __str__(self):
        result = "return"
        if self.result != None:
            result += " "
            result += str(self.result)
        return result

class BinOp(BaseNode):
    def __init__(self, tokens : typing.List[Token], lhs : BaseNode, op : str, rhs : BaseNode):
        super().__init__(tokens, [lhs, rhs])
        self.lhs = lhs
        self.op = op
        self.rhs = rhs
    def __str__(self):
        return "("+str(self.lhs)+self.op+str(self.rhs)+")"

class UnaryOp(BaseNode):
    def __init__(self, tokens : typing.List[Token], op, rhs):
        super().__init__(tokens, [rhs])
        self.op = op
        self.rhs = rhs
    def __str__(self):
        return "("+str(self.op)+str(self.rhs)+")"

class Integer(BaseNode):
    def __init__(self, tokens : typing.List[Token], value):
        super().__init__(tokens, [])
        self.value = value
    def __str__(self):
        return str(self.value)

class Float(BaseNode):
    def __init__(self, tokens : typing.List[Token], value):
        super().__init__(tokens, [])
        self.value = value
    def __str__(self):
        return str(self.value)

class String(BaseNode):
    def __init__(self, tokens : typing.List[Token], value):
        super().__init__(tokens, [])
        self.value = value
    def __str__(self):
        return str(self.value)

class Bool(BaseNode):
    def __init__(self, tokens : typing.List[Token], value):
        super().__init__(tokens, [])
        self.value = value
    def __str__(self):
        return "true" if self.value == True else "false"

class Variable(BaseNode):
    def __init__(self, tokens : typing.List[Token], name):
        super().__init__(tokens, [])
        self.name = name
    def __str__(self):
        return self.name

class IndexAccess(BaseNode):
    def __init__(self, tokens : typing.List[Token], lhs, rhs):
        super().__init__(tokens, [lhs, rhs])
        self.lhs = lhs
        self.rhs = rhs
    def __str__(self):
        return str(self.lhs) + "[" + str(self.rhs) + "]"

# TODO Convert to builtin function
class Print(BaseNode):
    def __init__(self, tokens : typing.List[Token], expr):
        super().__init__(tokens, [expr])
        self.expr = expr
    def __str__(self):
        return "print "+str(self.expr)+";"

class ExpressionList(FlatList, BaseNode):
    def __init__(self, tokens : typing.List[Token], elements : typing.List[BaseNode]):
        super().__init__(elements)
        # Initializing BaseNode has to be done manually because of the python
        # multiple inheritance approach
        self.tokens = tokens
        # Use Python's turbo-error:
        # self.inner_nodes = elements causes BaseNode.inner_nodes to be a
        # reference to the same list as FlatList.elements. Like this,
        # ExpressionList.append() adds the element for FlatList and for BaseNode
        self.inner_nodes = elements
    def __str__(self):
        return ", ".join(map(str,self.elements))

class Let(BaseNode):
    def __init__(self, tokens : typing.List[Token], names : typing.List[str], expr : typing.Union[ExpressionList, BinOp]): # rhs = Expressions or Assignment
        super().__init__(tokens, [expr])
        self.names = names
        self.expr = expr
    def __str__(self):
        names = ", ".join(self.names)
        return "let " + names + " = " + str(self.expr)

class IfElseStatement(BaseNode):
    def __init__(self, tokens : typing.List[Token], cond : BaseNode, thn : Block, els : BaseNode = None): # actually, it is: typing.Union[None, Block, IfElseStatement] = None):
        super().__init__(tokens, [cond, thn, els] if isinstance(els, BaseNode) else [cond, thn])
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
    def __init__(self, tokens : typing.List[Token], cond : BaseNode, t : Block):
        super().__init__(tokens, [cond, t])
        self.cond = cond
        self.t = t
    def __str__(self):
        return "while {} {}".format(str(self.cond), str(self.t))

class Pipeline(BaseNode):
    def __init__(self, tokens : typing.List[Token], elements : typing.List[BaseNode], nonblocking):
        super().__init__(tokens, elements)
        self.elements = elements
        self.nonblocking = nonblocking
    def __str__(self):
        pipeline = " | ".join(map(str,self.elements))
        if self.nonblocking:
            pipeline += " &"
        return pipeline

class PipelineLet(BaseNode):
    def __init__(self, tokens : typing.List[Token], names):
        super().__init__(tokens, [])
        self.names = names
    def __str__(self):
        names = ", ".join(self.names)
        return "let " + names

class SysCall(BaseNode):
    def __init__(self, tokens : typing.List[Token], args : typing.List[str]):
        super().__init__(tokens, [])
        self.args = args
    def __str__(self):
        return "(call " + " ".join(self.args) + ")"

class FunctionDefinition(BaseNode):
    def __init__(self, tokens : typing.List[Token], name : str, parameter_names : typing.List[str], parameter_types : typing.List[bongtypes.BongtypeIdentifier], return_types : typing.List[bongtypes.BongtypeIdentifier], body : Block, symbol_table : symbol_table.SymbolTable):
        super().__init__(tokens, [body])
        self.name = name
        self.parameter_names = parameter_names
        self.parameter_types = parameter_types
        self.return_types = return_types
        self.body = body
        self.symbol_table = symbol_table
    def __str__(self):
        parameters = []
        for name, typ in zip(self.parameter_names, self.parameter_types):
            parameters.append(name + " : " + str(typ))
        result = self.name + "("
        result += ", ".join(parameters)
        result += ") "
        if len(self.return_types) > 0:
            result += ": " + ", ".join(map(str,self.return_types)) + " "
        result += str(self.body)
        return result

class FunctionCall(BaseNode):
    def __init__(self, tokens : typing.List[Token], name, args):
        super().__init__(tokens, [args])
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
    def __init__(self, tokens : typing.List[Token], elements : ExpressionList):
        super().__init__(tokens, [elements])
        self.elements = elements
    def __str__(self):
        elements = []
        for e in self.elements:
            elements.append(str(e))
        result = "["
        result += ", ".join(elements)
        result += "]"
        return result
