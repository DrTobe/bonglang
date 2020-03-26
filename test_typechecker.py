#!/usr/bin/python

import unittest
from lexer import Lexer
from parser import Parser
from typechecker import TypeChecker, TypecheckException
import sys # for stderr printing

# To test the typechecker, we only check code here that should fail.
# Everything else is tested in test_evaluator.py (we just need to check that
# the typechecker returns True which is a task that can be done easily there).

class TestTypechecker(unittest.TestCase):
    def test_function(self):
        self.check("func f() : int {}")
        self.check("func f() { return 5 } f()")
        self.check("func f() : int { return 1337.0 } f()")
        self.check("func add(a : int, b : int) : int { return a + b } add(21, true)")
        self.check("func calc(a:int, b:int, c:int) : float { return a + b * c } calc(3, 5, 7)")
        self.check("func faculty(n:int) : int { if n <= 1 { /* return 1 */ } else { return n * faculty(n-1) }  } faculty(5)")

    def test_return(self):
        self.check("return \"no int\"\n")
        self.check("return 1337.0")
        self.check("return 21.0 ^ 2.0")
        self.check("return 21 * 2.0; 13.37")

    def test_syscall(self):
        # TODO How can program calls fail the typechecking stage? Is there
        # another possibility?
        self.check("let a : float = ls examples")
        self.check("let a : float = grep -nr bong .")
        self.check("let a : float = cd")
        self.check("let a : float = /usr/bin/true")
        self.check("let a : float = /usr/bin/false")

    def test_pipe(self):
        self.check("ls -la | grep foobar | len(\"mystring\") ")
        self.check("ls -la | grep test | nonexistentfunc() | /usr/bin/true")
        self.check("ls | grep foobar | sameasabove(1.0, 2.0) ")

    def test_advanced_pipe(self):
        self.check('let a = 1337 a | grep foo | /usr/bin/true')
        self.check('let a = "foo" a | grep bar | len(a)')
        # TODO Too lazy now
        """
        self.check('func a() : str { return "foo" } a() | grep foo | /usr/bin/true')
        self.check('func a() : str { return "foo" } a() | grep bar')
        self.check('let a = ""; echo "foo" | a; a')
        self.check('let a=""; let b=""; echo "foo\nbar" | grep foo | a,b; a')
        self.check('let a=""; let b=""; echo "foo\nbar" | grep foo | grep bar | b,a; b')
        self.check('let a = "foo"; a | grep foo | let b; b')
        """

    def test_builtin_functions(self):
        self.check('len(1337)')
        self.check('let a = 1337.5; len(a)')

    def test_let(self):
        self.check("let a : float = 1337")
        self.check("let a = 42 let b : str = a + 1337")
        self.check("let a,b : float = 1,0")

    def test_if(self):
        self.check("let a = 1337 if a == \"no number\" { true } else { false }")
        self.check("if false { return 1337 } else { return 42.0 }")
        self.check("if \"no_bool\" { 1337 }")
        self.check("if 0.0 { 1337 }")

    """ No shadowing anymore. Just look for a different name :)
    def test_shadowing(self):
        tests = [
                "let a = 5 { let a = 10 { a } }", 10,
                "let a = 5 { let a = 10 } a", 5,
                ]
        test_eval_list(self, tests)
    """

    def test_print_arith(self):
        self.check("print 2.0 + 4 - 2")
        self.check("print 4^2.0")
        self.check("print 2^2 + 2^3.0")
        self.check("print (1+2)*3.0")
        self.check("print (27%5)^2.0")

    def test_expression_statements(self):
        self.check("let a : str = 1337")
        self.check("2 + 4 - 2.0")
        self.check("4^2.0")
        self.check("2^2 + 2^3 * \"a_string\"")
        self.check("2*3 - 12.5")
        self.check("12 - 2.0^3" )
        self.check("(1+0.2)*3")
        self.check("1 + 2.0 *3")
        self.check("(1+2.0)^(1+2)")
        self.check("27.0%5")
        self.check("(27%5)^2.0")
        self.check("!true + 1")
        self.check("let a = 42 a = 1337.0")
        # TODO Do the following or don't do it???? -> also see test_evaluator.py
        # Assignments don't return anything anymore.
        # Reasons: 1. Consistency with let statement,
        # 2. For multiple assignments at once, use ExpressionList syntax: a,b = 0,0
        # 3. Assignments don't feel like expressions anymore (which they aren't due to ExpList syntax!)
        self.check("let a = 1337 let b = 42.0 a = b = 15")
        self.check("let a = 1337 let b = 42.0 a = b = 15")
        self.check("let a : [][]int = [1, 2, 3] a[0]")
        self.check("[1, 2, 3][0][0]")
        self.check("\"1, 2, 3\"[0] + 7")
        self.check("let a,b = 1,0.0 a,b=b,a")

    def test_let_array(self):
        self.check("let a : []float = [1]")
        self.check("let a = []")

    def test_error_messages(self):
        # The following tests fail for various reasons, they are used to
        # (manually) test the error reporting capabilities of the typechecker
        self.check("123 + 22.0 * 13.1")
        self.check("123 + 22.0 * 13")
        self.check("let a : int = []")
        self.check("let a : []int = [1.0]")
        self.check("let a = 5; let b : float = a")
        self.check("if 5 == \"asdf\" { }")
        self.check("let a = 5; while a {}")

    def check(self, code):
        worked = typecheck(code)
        self.assertFalse(worked, "Expected typechecker to fail.")
    
def typecheck(code):
    l = Lexer(code, "test_typechecker.py input")
    p = Parser(l)
    tc= TypeChecker()
    program = p.compile()
    try:
        tc.checkprogram_uncaught(program)
    except TypecheckException as e:
        # DEBUG: Print error messages
        if False:
            print(f"\nTypecheckError when checking '{code}'", file=sys.stderr)
            loc = e.node.get_location()
            posstring = f" in {loc[0]}, line {loc[1]} col {loc[2]} to line {loc[3]} col {loc[4]}"
            print(f"TypecheckError{posstring}: ", file=sys.stderr, end='')
            if loc[5]: # if location is valid
                for i, line in enumerate(code.split("\n")):
                    if i+1 == loc[1]:
                        print(f"\n{line}", file=sys.stderr)
                        print(" "*(loc[2]-1) + "^"*(loc[4]-loc[2]+1) , file=sys.stderr)
            print(f"{str(e.msg)}\n", file=sys.stderr)
        return False
    return True
