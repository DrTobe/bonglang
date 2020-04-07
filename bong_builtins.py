import bongtypes

# TODO Currently, the argument checker function raise BongtypeExceptions
# which are converted to TypecheckerExceptions in typechecker.py. This
# approach does not allow to specify the error location more specifically
# here because only TypecheckerExpcetion takes an ast.Node as a second
# argument which is used to calculate an error location.
#
# The same problem holds true for BongtypeExceptions generated in
# bongtypes.py.

def builtin_func_len(args):
    return len(args[0])
def check_len(argument_types : bongtypes.TypeList) -> bongtypes.TypeList:
    if len(argument_types)!=1:
        raise bongtypes.BongtypeException("Function 'len' expects one single argument.")
    arg = argument_types[0]
    if not isinstance(arg, bongtypes.Array) and not isinstance(arg, bongtypes.String):
        raise bongtypes.BongtypeException("Function 'len' expects an Array or a String, '{}' was found instead.".format(arg))
    return bongtypes.TypeList([bongtypes.Integer()])

def builtin_func_get_argv(args):
    import sys
    return sys.argv
def check_get_argv(argument_types : bongtypes.TypeList) -> bongtypes.TypeList:
    if len(argument_types)!=0:
        raise bongtypes.BongtypeException("Function 'get_argv' expects no arguments.")
    return bongtypes.TypeList([bongtypes.Array(bongtypes.String())])

def builtin_func_append(args):
    return args[0].append(args[1])
def check_append(argument_types):
    if len(argument_types)!=2:
        raise bongtypes.BongtypeException("Function 'append' expects exactly two arguments.")
    if not isinstance(argument_types[0], bongtypes.Array):
        raise bongtypes.BongtypeException("Function 'append' expects first parameter of type Array.")
    if not argument_types[0].contained_type.sametype(argument_types[1]):
        raise bongtypes.BongtypeException("Appended type does not match array type in function 'append'.")
    return argument_types[0]

functions = {
    #"call": self.callprogram,
    "len": (
        builtin_func_len,   # function to call
        check_len           # function to check params
    ),
    "get_argv": (builtin_func_get_argv, check_get_argv),
    "append": (builtin_func_append, check_append),
}
