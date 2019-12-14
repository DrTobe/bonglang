class Environment:
    def __init__(self, parent=None):
        self.parent = parent
        self.values = {}

    def set(self, name, value):
        self.values[name] = value

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
            self.set(key, value)
