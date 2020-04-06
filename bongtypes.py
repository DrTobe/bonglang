import typing
from flatlist import FlatList

# With the following BaseType, we can use
# python's type annotations whenever we expect type information in bong.
# To prevent BaseType itself from being instantiated, we raise an Exception
# in its constructor.
# Furthermore, we overload all bitwise operators to Exceptions. In bong, we do
# not support those currently. Most probably, this stays like this.
# And we also do this for all other operators. Like this, all subtypes that do
# not overload those operators just do not support them.
class BaseType:
	def __init__(self):
		if type(self) == BaseType:
			raise Exception("BaseType should not be initialized directly")
	def __add__(self, other):
		return self.arith(other)
	def __sub__(self, other):
		return self.arith(other)
	def __mul__(self, other):
		return self.arith(other)
	def __pow__(self, other):
		return self.arith(other)
	def __truediv__(self, other):
		return self.arith(other)
	def __floordiv__(self, other):
		return self.arith(other)
	def __mod__(self, other):
		return self.arith(other)
	def arith(self, other):
		raise BongtypeException(f"This operator is not defined for this type ({type(self)}).")
	def __lt__(self, other):
		return self.comp(other)
	def __le__(self, other):
		return self.comp(other)
	""" don't overload '==' and '!='
	    those two are used to check for None, e.g. in typechecker
	"""
	def __eq__(self, other):
		return self.sametype(other)
	def __ne__(self, other):
		return not self.__eq__(other)
	# Instead, use:
	def eq(self, other):
		return False
	def ne(self, other):
		return False
	def __gt__(self, other):
		return self.comp(other)
	def __ge__(self, other):
		return self.comp(other)
	def comp(self, other):
		raise BongtypeException(f"This operator is not defined for this type ({type(self)}).")
	def __lshift__(self, other):
		raise Exception("No bitwise operators used in bong.")
	def __rshift__(self, other):
		raise Exception("No bitwise operators used in bong.")
	def __and__(self, other):
		raise Exception("No bitwise operators used in bong.")
	def __or__(self, other):
		raise Exception("No bitwise operators used in bong.")
	def __xor__(self, other):
		raise Exception("No bitwise operators used in bong.")
	def __invert__(self, other):
		raise Exception("No bitwise operators used in bong.")
	# Because the comparison operators are overloaded, we need the following
	# function to determine equality between bongtypes.
	# It has to be overloaded for types that contain other types.
	def sametype(self, other):
		return type(self)==type(other)
	def __str__(self):
		return "BaseType (please override the __str__ method for subtypes!)"

# Meta-type for type hinting: ValueTypes are those types that expressions
# can evaluate to or that variables could be of. This is everything that is
# not Typedef, Function, BuiltinFunction, Module or some other meta type.
# The typechecker can then ensure that two types match
# and the matching types are ValueTypes. This prevents something like
# 'int == int', 'float = float' or whatever. For all overloaded operators,
# these checks are done automatically because the non ValueTypes do not
# implement those. For everything else, we have to think about what to do.
class ValueType(BaseType):
	pass

# Meta-type for expression lists
# TypeList does not derive from BaseType so it can not contain itself. Nice!
# The contained types are not ValueTypes because it could be function names or
# module names.
class TypeList(FlatList):
	def __init__(self, contained_types : typing.List[BaseType]):
		super().__init__(contained_types)
	def sametype(self, other):
		if type(other)!=TypeList:
			return False
		if len(self)!=len(other):
			return False
		for a,b in zip(self.elements, other.elements):
			if not a.sametype(b):
				return False
		return True
	def __str__(self):
		return "TypeList [" + ", ".join(map(str,self.elements)) + "]"

class Module(BaseType):
	def __init__(self, path : str):
		self.path = path
	def sametype(self, other):
		if type(other)!=Module:
			return False
		return self.path == other.path
	def __str__(self):
		return f"Module ({self.path})"

# Type that specifies types. For example, the identifiers 'int', 'str'
# and 'float' will be of that type, or identifiers that are names of structs.
# The 'value_type' field in this class will be of the same type as the values of
# 'int', 'str', 'float' or the instances of the respective structs.
# No first-class type because it can not be assigned to variables.
# This class is required so that type-names and type-values are of different
# types, e.g. 'int' and '5' should differ in type, i.e. 'int == 5' should fail!
class Typedef(BaseType):
	def __init__(self, typ : ValueType):
		self.value_type = typ
	def sametype(self, other):
		return type(other)==Typedef and self.value_type.sametype(other.value_type)
	def __str__(self):
		return f"Typedef ({self.value_type})"

# No first-class type but required to mark functions in the symbol table
class Function(BaseType):
	def __init__(self, parameter_types : TypeList, return_types : TypeList):
		self.parameter_types = parameter_types
		self.return_types = return_types
	def sametype(self, other):
		raise Exception("not implemented")
	def __str__(self):
		s = "Function (" + str(self.parameter_types) + ")"
		if len(self.return_types) > 0:
			s += " : " + str(self.return_types)
		return s
# Even less a first-class type that the user can use
import types # python types
class BuiltinFunction(BaseType):
	def __init__(self, check_func : types.FunctionType):
		self.check_func = check_func
	def check(self, argument_types : TypeList) -> TypeList:
		return self.check_func(argument_types)
	def sametype(self, other):
		raise Exception("not implemented")
	def __str__(self):
		return "BuiltinFunction (" + " ??? \o/ " + ")"

# Pseudo type used by the parser to comply to typing constraints
class UnknownType(BaseType):
	def sametype(self, other):
		if type(other)==UnknownType:
			return True
		return False
	def __str__(self):
		return "UnknownType"
# Pseudo-type for let statements with automatic type resolution and empty arrays.
# Currently, the AutoType is required to be a ValueType although this should
# be resolved before evaluating the code. Anyways, AutoTypes are used longer
# than UnknownTypes, e.g. they are added to Arrays when automatic type resolution
# happens. Arrays should only contain ValueTypes so AutoType has to be a
# ValueType.
# From one point of view AutoType should not be a ValueType because we can not
# actually work with that information at some point.
# On the other hand, all AutoTypes will be resolved to ValueTypes or the
# typechecker will fail, so it is ok to have it like this.
class AutoType(ValueType):
	def sametype(self, other):
		if type(other)==AutoType:
			return True
		return False
	def __str__(self):
		return "AutoType"

class Struct(ValueType):
	def __init__(self, name : str, fields : typing.Dict[str, ValueType]):
		self.name = name
		self.fields = fields
	def sametype(self, other):
		if not isinstance(other, Struct):
			return False
		if self.name != other.name:
			return False
		return self.fields == other.fields
		#if self.fields != other.fields:
			#return False
		#return self.field_types.sametype(other.field_types)
	def __str__(self):
		names = []
		for name, typ in self.fields.items():
			names.append(name + f" : {typ}")
		names = ", ".join(sorted(names))
		return f"Struct {self.name} "+"{" + f"{names}" + "}"

class Integer(ValueType):
	def __add__(self, other):
		return self.arith(other)
	def __sub__(self, other):
		return self.arith(other)
	def __mul__(self, other):
		return self.arith(other)
	def __pow__(self, other):
		return self.arith(other)
	def __truediv__(self, other):
		return self.arith(other)
	def __floordiv__(self, other):
		raise BongtypeException("Floordivision should not be used currently.")
	def __mod__(self, other):
		return self.arith(other)
	def arith(self, other):
		if type(other)==Integer:
			return Integer()
		raise BongtypeException("The second operand should be an Integer.")
	def __lt__(self, other):
		return self.comp(other)
	def __le__(self, other):
		return self.comp(other)
	def eq(self, other):
		return self.comp(other)
	def ne(self, other):
		return self.comp(other)
	def __gt__(self, other):
		return self.comp(other)
	def __ge__(self, other):
		return self.comp(other)
	def comp(self, other):
		if type(other)==Integer or type(other)==Float:
			return Boolean()
		raise BongtypeException("The second operand should be Integer or Float.")
	def __str__(self):
		return "Integer"

class Float(ValueType):
	def __add__(self, other):
		return self.arith(other)
	def __sub__(self, other):
		return self.arith(other)
	def __mul__(self, other):
		return self.arith(other)
	def __pow__(self, other):
		return self.arith(other)
	def __truediv__(self, other):
		return self.arith(other)
	def __floordiv__(self, other):
		raise BongtypeException("Floordivision should not be used currently.")
	def __mod__(self, other):
		raise BongtypeException("Modulo not supported for Floats currently.")
	def arith(self, other):
		if type(other)==Float:
			return Float()
		raise BongtypeException("The second operand should be a Float.")
	def __lt__(self, other):
		return self.comp(other)
	def __le__(self, other):
		return self.comp(other)
	def eq(self, other):
		return self.comp(other)
	def ne(self, other):
		return self.comp(other)
	def __gt__(self, other):
		return self.comp(other)
	def __ge__(self, other):
		return self.comp(other)
	def comp(self, other):
		if type(other)==Integer or type(other)==Float:
			return Boolean()
		raise BongtypeException("The second operand should be Integer or Float.")
	def __str__(self):
		return "Float"

class Boolean(ValueType):
	def eq(self, other):
		return self.comp(other)
	def ne(self, other):
		return self.comp(other)
	def comp(self, other):
		if type(other)==Boolean:
			return Boolean()
		raise BongtypeException("The second operand should be a Boolean.")
	def __str__(self):
		return "Boolean"

class String(ValueType):
	def __add__(self, other):
		if type(other)==String:
			return String()
		raise BongtypeException("The second operand should be a String.")
	def eq(self, other):
		return self.comp(other)
	def ne(self, other):
		return self.comp(other)
	def comp(self, other):
		if type(other)==String:
			return Boolean()
		raise BongtypeException("The second operand should be a String.")
	def __str__(self):
		return "String"

class Array(ValueType):
	def __init__(self, contained_type : ValueType):
		self.contained_type : ValueType = contained_type
	def __add__(self, other):
		if type(other)==Array:
			if type(other.contained_type)==type(self.contained_type):
				return Array(self.contained_type)
			raise BongtypeException("The second operand is an Array but it contains elements of a different Type.")
		raise BongtypeException("The second operand should be an Array.")
	""" ... We rather do Array.contained_type directly in IndexAccess
	def __getitem__(self, key):
		return self.contained_type
		"""
	def sametype(self, other):
		if type(other)==Array:
			return self.contained_type.sametype(other.contained_type)
		else:
			return False
	def __str__(self):
		return "Array [" + str(self.contained_type) + "]"

# Currently, this list of types is used to map type-strings to
# bongtypes.BaseType (subclass) instances. Maybe, this approach has to be
# revised in the future so that self-defined types can be used.
# -> coffee-discussion :)
basic_types = {
		"int": Integer,
		"float": Float,
		"bool": Boolean,
		"str": String,
}

# TODO Where and how does this class and the following function belong?
# Parser needs BongtypeIdentifier but BongtypeIdentifier.get_bongtype
# needs somehow access to self-defined types (not supported yet, 2020-03-05).
class BongtypeIdentifier:
	def __init__(self, typename : str, num_array_levels : int = 0):
		self.typename = typename
		self.num_array_levels = num_array_levels
	def __str__(self):
		#s = "BongtypeIdentifier ("
		s = ""
		s += "[]" * self.num_array_levels
		s += self.typename
		# s += ")"
		return s

class BongtypeException(Exception):
	def __init__(self, msg : str):
		super().__init__(self, msg)
		self.msg = msg
	def __str__(self):
		return super().__str__()

""" Operator overloading stuff in python
# Arithmetics
Operator				Expression	Internally
Addition				p1 + p2		p1.__add__(p2)
Subtraction				p1 - p2		p1.__sub__(p2)
Multiplication			p1 * p2		p1.__mul__(p2)
Power					p1 ** p2	p1.__pow__(p2)
Division				p1 / p2		p1.__truediv__(p2)
Floor Division			p1 // p2	p1.__floordiv__(p2)
Remainder (modulo)		p1 % p2		p1.__mod__(p2)
# Comparisons
Less than				p1 < p2		p1.__lt__(p2)
Less than or equal to	p1 <= p2	p1.__le__(p2)
Equal to				p1 == p2	p1.__eq__(p2)
Not equal to			p1 != p2	p1.__ne__(p2)
Greater than			p1 > p2		p1.__gt__(p2)
Greater or equal to		p1 >= p2	p1.__ge__(p2)
# Bitwise stuff
Bitwise Left Shift		p1 << p2	p1.__lshift__(p2)
Bitwise Right Shift		p1 >> p2	p1.__rshift__(p2)
Bitwise AND				p1 & p2		p1.__and__(p2)
Bitwise OR				p1 | p2		p1.__or__(p2)
Bitwise XOR				p1 ^ p2		p1.__xor__(p2)
Bitwise NOT				~p1			p1.__invert__()
# Other stuff
Index access			p1[p2]		p1.__getitem__(p2):
"""

