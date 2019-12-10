#!/usr/bin/python

import unittest
from lexer import Lexer
from parser import Parser
from evaluator import Eval

class TestEvaluator(unittest.TestCase):
    def test_print_arith(self):
        tests = [
                "print 2 + 4 - 2", 4,
                "print 4^2", 16,
                "print 2^2 + 2^3", 12,
                "print 2*3 - 12", -6,
                "print 12 - 2^3" , 4,
                "print (1+2)*3", 9,
                "print 1 +2 *3", 7,
                "print (1+2)^(1+2)", 27,
                "print 27%5", 2,
                "print (27%5)^2", 4,
                ]
        for i in range(0, len(tests), 2):
            statement = tests[i]
            expected = tests[i+1]
            test_eval(statement, None, self)
            self.assertEqual(self.result, expected, "Expected to print {} but got {}".format(expected, self.result))

    def test_expression_statements(self):
        tests = [
                "2 + 4 - 2", 4,
                "4^2", 16,
                "2^2 + 2^3", 12,
                "2*3 - 12", -6,
                "12 - 2^3" , 4,
                "(1+2)*3", 9,
                "1 +2 *3", 7,
                "(1+2)^(1+2)", 27,
                "27%5", 2,
                "(27%5)^2", 4,
                "-2 * 3", -6,
                "!true", False,
                ]
        for i in range(0, len(tests), 2):
            statement = tests[i]
            expected = tests[i+1]
            test_eval(statement, expected, self)

    def printer(self, string):
        self.result = string

def test_eval(code, expected, test_class):
    evaluated = evaluate(code, test_class.printer)
    test_class.assertEqual(evaluated, expected, "Expected {} but got {}".format(expected, evaluated))
    
def evaluate(code, printer):
    l = Lexer(code)
    p = Parser(l)
    e = Eval(printer)
    program = p.compile()
    return e.evaluate(program)
