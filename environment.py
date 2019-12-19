class Environment:
    def __init__(self, parent=None):
        self.parent = parent
        self.values = {}

    def register(self, name):
        if name in self.values:
            raise Exception("cannot redefine " + name)
        self.values[name] = None

    def set(self, name, value):
        if name in self.values:
            self.values[name] = value
            return
        if self.parent != None:
            self.parent.set(name, value)
            return
        raise Exception("Cannot set variable called " + name)

    def get(self, name):
        if name in self.values:
            return self.values[name]
        if self.parent != None:
            return self.parent.get(name)
        raise Exception("There is no variable called " + name)

    def exists(self, name):
        if name in self.values:
            return True
        if self.parent == None:
            return False
        return self.parent.exists(name)

    def add_definitions(self, otherEnv):
        for d in otherEnv.values:
            key = d
            value = otherEnv.get(d)
            self.register(key)
            self.set(key, value)

    def __str__(self):
        x = "Environment "
        if self.parent != None:
            x += "(" + str(self.parent) + ") "
        x += "{\n"
        for name,value in self.values.items():
            x += name + " = " + str(value) + "\n"
        x += "}"
        return x

