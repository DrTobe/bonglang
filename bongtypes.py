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
		raise BongtypeException("This operator is not defined for this Type.")
	def __lt__(self, other):
		return self.comp(other)
	def __le__(self, other):
		return self.comp(other)
	def __eq__(self, other):
		return self.comp(other)
	def __ne__(self, other):
		return self.comp(other)
	def __gt__(self, other):
		return self.comp(other)
	def __ge__(self, other):
		return self.comp(other)
	def comp(self, other):
		raise BongtypeException("This operator is not defined for this Type.")
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

# No first-class type but required to mark functions in the symbol table
class Function(BaseType):
	pass

class Integer(BaseType):
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
	def __eq__(self, other):
		return self.comp(other)
	def __ne__(self, other):
		return self.comp(other)
	def __gt__(self, other):
		return self.comp(other)
	def __ge__(self, other):
		return self.comp(other)
	def comp(self, other):
		if type(other)==Integer or type(other)==Float:
			return Boolean()
		raise BongtypeException("The second operand should be Integer or Float.")

class Float(BaseType):
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
	def __eq__(self, other):
		return self.comp(other)
	def __ne__(self, other):
		return self.comp(other)
	def __gt__(self, other):
		return self.comp(other)
	def __ge__(self, other):
		return self.comp(other)
	def comp(self, other):
		if type(other)==Integer or type(other)==Float:
			return Boolean()
		raise BongtypeException("The second operand should be Integer or Float.")

class Boolean(BaseType):
	def __eq__(self, other):
		return self.comp(other)
	def __ne__(self, other):
		return self.comp(other)
	def comp(self, other):
		if type(other)==Boolean:
			return Boolean()
		raise BongtypeException("The second operand should be a Boolean.")
class String(BaseType):
	def __add__(self, other):
		if type(other)==String:
			return String()
		raise BongtypeException("The second operand should be a String.")
	def __eq__(self, other):
		return self.comp(other)
	def __ne__(self, other):
		return self.comp(other)
	def comp(self, other):
		if type(other)==String:
			return Boolean()
		raise BongtypeException("The second operand should be a String.")

class Array(BaseType):
	def __init__(self, contained_type : BaseType):
		self.contained_type : BaseType = contained_type
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

