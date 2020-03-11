#!/usr/bin/python

import unittest
from lexer import Lexer
from parser import Parser
from typechecker import TypeChecker
from bongtypes import BongtypeException
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

    def test_tmp_error_messages(self):
        self.check("123 + 22.0 * 13.1", False)
        self.check("123 + 22.0 * 13", False)

    def check(self, code, should_work):
        worked = typecheck(code)
        self.assertEqual(worked, should_work, "Expected {} but got {}".format(worked, should_work))
    
def typecheck(code):
    l = Lexer(code, "test_evaluator.py input")
    p = Parser(l)
    tc= TypeChecker()
    program = p.compile()
    try:
        tc.checkprogram_uncaught(program)
    except BongtypeException as e:
        # DEBUG: Print error messages
        if True:
            if e.node != None:
                loc = e.node.get_location()
                posstring = f" in {loc[0]}, line {loc[1]} col {loc[2]} to line {loc[3]} col {loc[4]}"
            else:
                posstring = ""
            print(f"\n\nTypecheckError{posstring}: {str(e.msg)}", file=sys.stderr)
        return False
    return True
