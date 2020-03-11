#!/usr/bin/python

import unittest
from lexer import Lexer
from parser import Parser
from typechecker import TypeChecker, TypecheckException
import sys # for stderr printing

class TestTypechecker(unittest.TestCase):
    def test_function(self):
        self.check("func f() {}", True)
        self.check("func f() {} f()", True)
        self.check("func f() : int { return 1337 } f()", True)
        self.check("func add(a : int, b : int) : int { return a + b } add(21, 21)", True)
        self.check("func calc(a:int, b:int, c:int) : int { return a + b * c } calc(3, 5, 7)", True)
        self.check("func faculty(n:int) : int { if n <= 1 { return 1 } else { return n * faculty(n-1) } return 0 } faculty(5)", True)

    def test_let_array(self):
        self.check("let a = [1]", True)
        self.check("let a = []", False)

    def test_error_messages(self):
        # The following tests fail for various reasons, they are used to
        # (manually) test the error reporting capabilities of the typechecker
        self.check("123 + 22.0 * 13.1", False)
        self.check("123 + 22.0 * 13", False)
        self.check("let a : int = []", False)
        self.check("let a : []int = [1.0]", False)
        self.check("let a = 5; let b : float = a", False)
        self.check("if 5 == \"asdf\" { }", False)
        self.check("let a = 5; while a {}", False)

    def check(self, code, should_work):
        worked = typecheck(code)
        self.assertEqual(should_work, worked, f"Expected {should_work} but got {worked}")
    
def typecheck(code):
    l = Lexer(code, "test_evaluator.py input")
    p = Parser(l)
    tc= TypeChecker()
    program = p.compile()
    try:
        tc.checkprogram_uncaught(program)
    except TypecheckException as e:
        # DEBUG: Print error messages
        if True:
            print(f"\nTypecheckError when checking '{code}'", file=sys.stderr)
            loc = e.node.get_location()
            posstring = f" in {loc[0]}, line {loc[1]} col {loc[2]} to line {loc[3]} col {loc[4]}"
            print(f"TypecheckError{posstring}: {str(e.msg)}\n", file=sys.stderr)
        return False
    return True
