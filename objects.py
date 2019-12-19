class ReturnValue:
    def __init__(self, value=None):
        self.value = value
    def __eq__(self, other):
        return self.value == other.value
    def __str__(self):
        result = "ReturnValue"
        if self.value != None:
            result += " "
            result += str(self.value)
        return result
