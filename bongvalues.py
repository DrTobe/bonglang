from flatlist import FlatList
from collections import UserDict
import ast
import typing

class ValueList(FlatList):
    def __init__(self, elements, unwind_return=False):
        super().__init__(elements)
        # Stores if this value(s) was generated from a return statement.
        # If so, the stack of nested blocks has to be unwinded.
        self.unwind_return = unwind_return
    def returned(self):
        return self.unwind_return
    def __str__(self):
        return ", ".join(map(str,self.elements))

class StructValue(UserDict):
    def __init__(self, name : typing.Union[ast.Identifier, ast.DotAccess]):
        super().__init__()
        if isinstance(name, ast.Identifier):
            self.name = name.name
        elif isinstance(name, ast.DotAccess):
            self.name = name.rhs
        else:
            raise Exception("StructValues should be initialized with ast.Identifier"
                    " or ast.DotAccess!")
    def __str__(self):
        fields = []
        for name, value in self.data.items():
            fields.append(name + " : " + str(value))
        return str(self.name) + " { " + ", ".join(sorted(fields)) + " }"
