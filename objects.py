class ReturnValue:
    def __init__(self, value=None):
        self.value = value
    def __eq__(self, other):
        if other == None: # Comparing to None should be possible without error message
            return False
        if not isinstance(other, ReturnValue):
            print("dont compare this")
            return False
        return self.value == other.value
    def __str__(self):
        result = "ReturnValue"
        if self.value != None:
            result += " "
            result += str(self.value)
        return result

class Array:
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
