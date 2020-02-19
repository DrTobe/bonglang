import bongtypes
import typing

class SymbolTable:
    def __init__(self, parent=None):
        self.parent = parent
        self.names = {}
    def register(self, name):
        if name in self.names:
            raise Exception("cannot redefine " + name)
        self.names[name] = Symbol()
    def remove(self, name):
        self.names.pop(name, None)
    def contains(self, name):
        return name in self.names
    def exists(self, name):
        if self.contains(name):
            return True
        if self.parent != None:
            return self.parent.exists(name)
        return False
    def get(self, name):
        if name in self.names:
            return self.names[name]
        if self.parent != None:
            return self.parent.get(name)
        raise(Exception("symbol {} does not exist in table".format(name)))
    def __getitem__(self, name):
        return self.get(name)
    def __str__(self):
        x = "SymbolTable "
        if self.parent != None:
            x += "(" + str(self.parent) + ") "
        x += "{\n"
        for name,symbol in self.names.items():
            x += name + " : " + str(symbol.typ) + " = " + str(symbol.value) + "\n"
        x += "}"
        return x

class Symbol:
    def __init__(self):
        self.typ : typing.Optional[bongtypes.BaseType] = None
        #self.value = None
