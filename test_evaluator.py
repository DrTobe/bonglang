#!/usr/bin/python

import unittest
from lexer import Lexer
from parser import Parser
from evaluator import Eval

class TestEvaluator(unittest.TestCase):
    def test_function(self):
        tests = [
                "func f() {}", None,
                "func f() {} f()", None,
                ]
        test_eval_list(self, tests)

    def test_syscall(self):
        # TODO output should be redirected somewhere to reduce testing output
        # For now, I 'ls examples' because there is not too many examples yet
        # and 'cd' does not produce output.
        tests = [
                "ls examples", 0,
                #"grep -nr bong .", 0,
                "cd", 0,
                ]
        test_eval_list(self, tests)

    def test_pipe(self):
        # TODO Testing piped subprocesses produced a warning:
        # /usr/lib/python3.8/subprocess.py:942: ResourceWarning: subprocess 1745 is still running
        # _warn("subprocess %s is still running" % self.pid,
        # ResourceWarning: Enable tracemalloc to get the object allocation traceback
        # Is there a problem?
        tests = [
                "ls -la | grep test", 0,
                "ls -la | grep test | grep py | grep lexer", 0,
                "ls | grep foobar", 1,
                ]
        test_eval_list(self, tests)

    def test_let(self):
        tests = [
                "let a = 1337 a", 1337,
                "let a = 42 let b = a + 1337 b", 1379,
                ]
        test_eval_list(self, tests)

    def test_if(self):
        tests = [
                "let a = 1337 if a == 1337 { true } else { false }", True,
                "if false { 1337 } else { 42 }", 42,
                "if true { 1337 }", 1337,
                "if false { 1337 }", None, # currently blocks work like expressions but cannot be used as expressions
                ]
        test_eval_list(self, tests)

    def test_shadowing(self):
        tests = [
                "let a = 5 { let a = 10 { a } }", 10,
                "let a = 5 { let a = 10 } a", 5,
                ]
        test_eval_list(self, tests)

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
                "let a = 42 a = 1337 a", 1337,
                "let a = 1337 let b = 42 a = b = 15 a", 15,
                "let a = 1337 let b = 42 a = b = 15 b", 15,
                ]
        test_eval_list(self, tests)

    def printer(self, string):
        self.result = string

def test_eval_list(test_class, tests):
    for i in range(0, len(tests), 2):
        statement = tests[i]
        expected = tests[i+1]
        test_eval(statement, expected, test_class)

def test_eval(code, expected, test_class):
    evaluated = evaluate(code, test_class.printer)
    test_class.assertEqual(evaluated, expected, "Expected {} but got {}".format(expected, evaluated))
    
def evaluate(code, printer):
    l = Lexer(code)
    p = Parser(l)
    e = Eval(printer)
    program = p.compile()
    return e.evaluate(program)
