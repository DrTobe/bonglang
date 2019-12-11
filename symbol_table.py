class SymbolTable:
    def __init__(self, parent=None):
        self.parent = parent
        self.names = {}
    def register(self, name):
        self.names[name] = Symbol()
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

class Symbol:
    def __init__(self):
        self.typ = None
        self.value = None
