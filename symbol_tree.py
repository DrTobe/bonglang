from __future__ import annotations
import bongtypes
import typing

class SymbolTreeNode:
    def __init__(self, name : str, typ : bongtypes.BaseType, stack_index : int, parent : typing.Optional[SymbolTreeNode]):
        self.name = name
        self.typ = typ
        self.stack_index = stack_index
        self.parent = parent

class SymbolTree:
    def __init__(self, leaf : typing.Optional[SymbolTreeNode] = None):
        self.current_leaf = leaf
    def register(self, name : str, typ : bongtypes.BaseType):
        if not isinstance(self.current_leaf, SymbolTreeNode): # init
            self.current_leaf = SymbolTreeNode(name, typ, 0, None)
        else:
            cl = self.current_leaf
            self.current_leaf = SymbolTreeNode(name, typ, cl.stack_index+1, cl)
    def __contains__(self, name : str): # 'in' operator
        node = self.current_leaf
        while isinstance(node, SymbolTreeNode):
            if node.name == name:
                return True
            node = node.parent
        return False
    def get_node(self, name): # Helper method for the following methods
        node = self.current_leaf
        while node != None:
            if node.name == name:
                return node
            node = node.parent
        raise Exception("Check if element exists before trying to access it!")
    def __setitem__(self, name, typ): # '[...]' operator write
        self.get_node(name).typ = typ
    def __getitem__(self, name): # '[...]' operator read
        return self.get_node(name).typ
    def get_index(self, name):
        return self.get_node(name).stack_index
    def take_snapshot(self) -> typing.Optional[SymbolTreeNode]:
        return self.current_leaf
    def restore_snapshot(self, node : typing.Optional[SymbolTreeNode]):
        self.current_leaf = node
    def __str__(self):
        x = "SymbolTree {\n"
        symbol = self.current_leaf
        while symbol != None:
            x += f"  {symbol.name} : {symbol.typ}\n"
            symbol = symbol.parent
        x += "}"
        return x
