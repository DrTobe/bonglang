#!/usr/bin/python

import unittest
from lexer import Lexer
from parser import Parser
from evaluator import Eval

class TestEvaluator(unittest.TestCase):
    def test_print_arith(self):
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
                ]
        for i in range(0, len(tests), 2):
            expr = "print "+tests[i]
            expected = tests[i+1]
            self.runn(expr, expected)
    def runn(self, expr, expected):
        l = Lexer(expr)
        p = Parser(l)
        e = Eval(self.printer)
        program = p.compile()
        e.evaluate(program)
        self.assertEqual(self.result, expected, "Expected {} but got {}".format(expected, self.result))
    def printer(self, string):
        self.result = string
