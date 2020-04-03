#!/usr/bin/python

import unittest
from lexer import Lexer
from parser import Parser
from typechecker import TypeChecker
from evaluator import Eval
from test_typechecker import typecheck

class TestEvaluator(unittest.TestCase):
    def test_function(self):
        test_eval("func f() {}", None, self)
        test_eval("func f() {} f()", None, self)
        test_eval("func f() : int { return 1337 } f()", 1337, self)
        test_eval("func add(a : int, b : int) : int { return a + b } add(21, 21)", 42, self)
        test_eval("func calc(a:int, b:int, c:int) : int { return a + b * c } calc(3, 5, 7)", 38, self)
        test_eval("func faculty(n:int) : int { if n <= 1 { return 1 } else { return n * faculty(n-1) } return 0 } faculty(5)", 120, self)

    def test_return(self):
        self.single_return_test("return 0\n", None)
        self.single_return_test("return 1337", 1337)
        self.single_return_test("return 21 * 2", 42)
        self.single_return_test("return 21 * 2; 13.37", 42)
    def single_return_test(self, code, expected_value):
        try:
            checked = typecheck(code) # see below test_eval()
            self.assertTrue(checked, "Expected typechecker to succeed.")
            x = evaluate(code, self.printer)
            self.assertTrue(False, "Expected 'return' to raise a SystemExit exception.")
        except SystemExit as e:
            if expected_value != None:
                self.assertEqual(e.code, expected_value, "Expected return value {} but got {}".format(expected_value, e.code))

    def test_syscall(self):
        # TODO output should be redirected somewhere to reduce testing output
        # For now, I only run commands which do not produce any output
        #test_eval("ls examples", 0, self)
        #test_eval("grep -nr bong .", 0, self)
        test_eval("cd", 0, self) # builtin
        test_eval("/usr/bin/true", 0, self)
        test_eval("/usr/bin/false", 1, self)

    def test_pipe(self):
        # Since we are not able yet to redirect output, we just run pipelines
        # here that do not produce output
        test_eval("ls -la | grep foobar", 1, self)
        test_eval("ls -la | grep test | grep py | grep lexer | /usr/bin/true", 0, self)
        test_eval("ls | grep foobar", 1, self)

    def test_advanced_pipe(self):
        # Since we are not able yet to redirect output, we just run pipelines
        # here that do not produce output
        test_eval('let a = "foo" a | grep foo | /usr/bin/true', 0, self)
        test_eval('let a = "foo" a | grep bar', 1, self)
        test_eval('func a() : str { return "foo" } a() | grep foo | /usr/bin/true', 0, self)
        test_eval('func a() : str { return "foo" } a() | grep bar', 1, self)
        test_eval('let a = ""; echo "foo" | a; a', "foo\n", self)
        test_eval('let a=""; let b=""; echo "foo\nbar" | grep foo | a,b; a', "foo\n", self)
        test_eval('let a=""; let b=""; echo "foo\nbar" | grep foo | grep bar | b,a; b', "", self)
        test_eval('let a = "foo"; a | grep foo | let b; b', "foo\n", self)

    def test_builtin_functions(self):
        # TODO The call() builtin will be removed 
        #test_eval('let yes = "/usr/bin/true"; call(yes)', 0, self)
        #test_eval('let no = "/usr/bin/false"; call(no)', 1, self)
        #TODO piping builtins currently not supported, 2020-02-06
        #test_eval('call("ls") | call("grep", "foobar")', 1, self)
        test_eval('len("foo")', 3, self)
        test_eval('let a = "foo"; len(a)', 3, self)

    def test_let(self):
        test_eval("let a = 1337 a", 1337, self)
        test_eval("let a = 42 let b = a + 1337 b", 1379, self)
        test_eval("let a,b = 1,0  b", 0, self)

    def test_if(self):
        test_eval("let a = 1337 if a == 1337 { true } else { false }", True, self)
        test_eval("if false { 1337 } else { 42 }", 42, self)
        test_eval("if true { 1337 }", 1337, self)
        test_eval("if false { 1337 }", None, self) # currently blocks work like expressions but cannot be used as expressions

    """ No shadowing anymore. Just look for a different name :)
    def test_shadowing(self):
        tests = [
                "let a = 5 { let a = 10 { a } }", 10,
                "let a = 5 { let a = 10 } a", 5,
                ]
        test_eval_list(self, tests)
    """

    def test_print_arith(self):
        self.single_print_test("print 2 + 4 - 2", 4)
        self.single_print_test("print 4^2", 16)
        self.single_print_test("print 2^2 + 2^3", 12)
        self.single_print_test("print 2*3 - 12", -6)
        self.single_print_test("print 12 - 2^3" , 4)
        self.single_print_test("print (1+2)*3", 9)
        self.single_print_test("print 1 +2 *3", 7)
        self.single_print_test("print (1+2)^(1+2)", 27)
        self.single_print_test("print 27%5", 2)
        self.single_print_test("print (27%5)^2", 4)
    def single_print_test(self, code, expected_result):
        test_eval(code, None, self)
        self.assertEqual(self.result, expected_result, "Expected to print {} but got {}".format(expected_result, self.result))


    def test_expression_statements(self):
        test_eval("let a = 1337 a", 1337, self)
        test_eval("2 + 4 - 2", 4, self)
        test_eval("4^2", 16, self)
        test_eval("2^2 + 2^3", 12, self)
        test_eval("2*3 - 12", -6, self)
        test_eval("12 - 2^3" , 4, self)
        test_eval("(1+2)*3", 9, self)
        test_eval("1 +2 *3", 7, self)
        test_eval("(1+2)^(1+2)", 27, self)
        test_eval("27%5", 2, self)
        test_eval("(27%5)^2", 4, self)
        test_eval("-2 * 3", -6, self)
        test_eval("13.37 + 4.2", 17.57, self)
        test_eval("!true", False, self)
        test_eval("let a = 42 a = 1337 a", 1337, self)
        # TODO Do the following or don't do it????
        # Assignments don't return anything anymore.
        # Reasons: 1. Consistency with let statement,
        # 2. For multiple assignments at once, use ExpressionList syntax: a,b = 0,0
        # 3. Assignments don't feel like expressions anymore (which they aren't due to ExpList syntax!)
        test_eval("let a = 1337 let b = 42 a = b = 15 a", 15, self)
        test_eval("let a = 1337 let b = 42 a = b = 15 b", 15, self)
        test_eval("let a = [1, 2, 3] a[0]", 1, self)
        test_eval("[1, 2, 3][0]", 1, self)
        test_eval("\"1, 2, 3\"[0]", "1", self)
        test_eval("let a,b = 1,0 a,b=b,a a", 0, self)

    def test_struct_definition(self):
        self.check("struct T { x : int, y : float }", None)
        self.check("struct A { x : int } struct B { y : A}", None)
        self.check("struct B { y : A } struct A { x : int }", None)

    def test_struct_value(self):
        self.check("struct T { x : int } T { x : 5 }", "T { x : 5 }")
        self.check("struct T { x : int } let a = T { x : 5 }; a", "T { x : 5 }")
        self.check("struct T { x : B } struct B { y : int } T { x : B { y : 7 } }", "T { x : B { y : 7 } }")
        self.check("struct T { x : B } struct B { y : int } let a = T { x : B { y : 7 } }; a", "T { x : B { y : 7 } }")

    def test_dot_access(self):
        self.check("struct T { x : int } T { x : 5 }.x", 5)
        self.check("struct T { x : int } let a = T { x : 5 }; a.x", 5)
        self.check("struct T { x : B } struct B { y : int } T { x : B { y : 7 } }.x", "B { y : 7 }")
        self.check("struct T { x : B } struct B { y : int } let t = T { x : B { y : 7 } }; t.x", "B { y : 7 }")
        self.check("struct T { x : B } struct B { y : int } let t = T { x : B { y : 7 } }; t.x.y", "7")

    # Helper method to typecheck the given code chunk
    def typecheck(self, code):
        checked = typecheck(code)
        self.assertTrue(checked, "Expected typechecker to succeed.")

    # Helper method to typecheck and evaluate-check the given code chunk
    def check(self, code, expected):
        # Here, we do typechecker-testing first, evaluator testing afterwards.
        # This can be done because all code here should pass the typechecker.
        # For testing that the typechecker catches invalid code, we have
        # an additional test_typechecker.py
        self.typecheck(code)
        evaluated = evaluate(code, self.printer)
        if type(expected) == str:
            evaluated = str(evaluated)
        self.assertEqual(evaluated, expected, f"Expected {expected} but"
            f" got {evaluated}")

    def printer(self, string):
        self.result = string

# Just for backwards compatibility
def test_eval(code, expected, test_class):
    test_class.check(code, expected)
    
# Evaluate the given code chunk, assert that typechecking works
def evaluate(code, printer):
    l = Lexer(code, "test_evaluator.py input")
    p = Parser(l)
    tc= TypeChecker()
    e = Eval(printer)
    program = p.compile()
    if not tc.checkprogram(program):
        return "Typechecker failed!"
    return e.evaluate(program)
