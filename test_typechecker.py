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
            print(f"TypecheckError{posstring}: {str(e.msg)}\n", file=sys.stderr)
        return False
    return True
