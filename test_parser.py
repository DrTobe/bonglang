import unittest
import lexer
import parser

class TestData():
    def __init__(self, sourcecode, expectedStr):
        self.sourcecode = sourcecode
        self.expectedStr = expectedStr

class TestParser(unittest.TestCase):
    def test_program(self):
        testData = [
                TestData("print 1 + 2 13 + 37", "{\nprint (1+2);\n(13+37)\n}"),
                TestData("13 42 print 13 + 37 == 42 41 - 21", "{\n13\n42\nprint ((13+37)==42);\n(41-21)\n}"),
                TestData("print 1 + 2\n13 + 37\n", "{\nprint (1+2);\n(13+37)\n}"),
                ]
        test_strings(self, testData)

    def test_return(self):
        testData = [
                TestData("return\n", "{\nreturn\n}"),
                TestData("return 1337", "{\nreturn 1337\n}"),
                TestData("return 42 / 2", "{\nreturn (42/2)\n}"),
                ]
        test_strings(self, testData)

    def test_let(self):
        test_string(self, "let a = 0; let b = 0;", "{\nlet a = 0\nlet b = 0\n}")
        test_string(self, "let a = 0; let b = 0; a | b", "{\nlet a = 0\nlet b = 0\na | b\n}")
        test_string(self, "let a,b = 1,2", "{\nlet a, b = 1, 2\n}")

    def test_functioncall(self):
        testData = [
                TestData("someFunc()", "{\nsomeFunc()\n}"),
                TestData("add(1, 2)", "{\nadd(1, 2)\n}"),
                TestData("add(1 + 2, 2*3+4)", "{\nadd((1+2), ((2*3)+4))\n}"),
                ]
        test_strings(self, testData)

    def test_syscall(self):
        data = [
                "ls -la", "{\n(call ls -la)\n}",
                "grep foo", "{\n(call grep foo)\n}",
                "cd /home/bong/unittest", "{\n(call cd /home/bong/unittest)\n}",
                "grep foo\nls -la", "{\n(call grep foo)\n(call ls -la)\n}",
                ]
        test_strings_list(self, data)

    def test_pipe(self):
        data = [
                "ls -la | grep foo", "{\n(call ls -la) | (call grep foo)\n}",
                "cd | grep", "{\n(call cd) | (call grep)\n}", # parses, but does not run
                "ls | grep foo | grep bar", "{\n(call ls) | (call grep foo) | (call grep bar)\n}",
                "let a = 0; let b = 0; a + 1 | grep foo | b", "{\nlet a = 0\nlet b = 0\n(a+1) | (call grep foo) | b\n}",
                ]
        test_strings_list(self, data)

    def test_function_definition(self):
        testData = [
                TestData("func someFunc() { let a = 1337 }", "someFunc"),
                TestData("func add(a : Int, b : Int) : Int { return a + b }", "add"),
                ]
        for td in testData:
            program = translate(td.sourcecode)
            try:
                self.assertNotEqual(program.functions.get(td.expectedStr), None)
            except:
                self.fail("Expected function to exist")


    def test_if(self):
        testData = [
                TestData("if true { 1337 }", "{\nif true {\n1337\n}\n}"),
                TestData("if true { 1337 } else { 42 }", "{\nif true {\n1337\n} else {\n42\n}\n}"),
                TestData("if true { 1337 } else if false { 42 }", "{\nif true {\n1337\n} else if false {\n42\n}\n}"),
                TestData("if true { 1337 } else if false { 42 } else { 31415 }", "{\nif true {\n1337\n} else if false {\n42\n} else {\n31415\n}\n}"),
                ]
        test_strings(self, testData)

    def test_while(self):
        testData = [
                "while 3 { 1337 }", "{\nwhile 3 {\n1337\n}\n}",
                "let x = 0 while x > 0 { print x }", "{\nlet x = 0\nwhile (x>0) {\nprint x;\n}\n}",
                ]
        test_strings_list(self, testData)

    def test_print(self):
        test_string(self, "print 1 + 2", "{\nprint (1+2);\n}"),
        test_string(self, "print 13 + 37 == 42", "{\nprint ((13+37)==42);\n}")

    def test_expression_statement(self):
        test_string(self, "1", "{\n1\n}")
        test_string(self, "-1", "{\n(-1)\n}")
        test_string(self, "true", "{\ntrue\n}")
        test_string(self, "!false", "{\n(!false)\n}")
        test_string(self, "1 + 2", "{\n(1+2)\n}")
        test_string(self, "1 + 2 + 3", "{\n((1+2)+3)\n}")
        test_string(self, "1 - 2 - 3", "{\n((1-2)-3)\n}")
        test_string(self, "1 + 2 * 3", "{\n(1+(2*3))\n}")
        test_string(self, "4 * 2 + 3", "{\n((4*2)+3)\n}")
        test_string(self, "1 + 2 ^ 3", "{\n(1+(2^3))\n}")
        test_string(self, "1 ^ 2 ^ 3", "{\n(1^(2^3))\n}")
        test_string(self, "13.37 + 4.2", "{\n(13.37+4.2)\n}")
        test_string(self, "add(1, 2) * 2", "{\n(add(1, 2)*2)\n}")
        test_string(self, "true || false && 1 < 2 + 3 * 3 ^ 5" , "{\n(true||(false&&(1<(2+(3*(3^5))))))\n}")
        test_string(self, "let a = 1337\n a = 42", "{\nlet a = 1337\n(a=42)\n}")
        test_string(self, "[1, 2, 3][0]", "{\n[1, 2, 3][0]\n}")
        test_string(self, "\"abc\"[0]", "{\nabc[0]\n}")
        test_string(self, "let a,b = 1,0; a,b = b,a", "{\nlet a, b = 1, 0\n(a, b=b, a)\n}")
        test_string(self, """
let a = 1337
let b = 42
let c = 31415
a = b = c = 15
    """,               """{
let a = 1337
let b = 42
let c = 31415
(a=(b=(c=15)))
}""")

def test_strings(test_class, testData):
    for td in testData:
        test_string(test_class, td.sourcecode, td.expectedStr)

def test_strings_list(test_class, test_data):
    for i in range(0,len(test_data),2):
        source = test_data[i]
        expected = test_data[i+1]
        test_string(test_class, source, expected)

def test_string(test_class, sourcecode, expectedStr):
    program = translate(sourcecode)
    test_class.assertNotEqual(None, program, "program shouldn't be None")
    program_string = str(program)
    test_class.assertEqual(program_string, expectedStr, "Expected \"" + expectedStr + "\", but got \" " + program_string + "\"")

def createParser(sourcecode):
    return parser.Parser(lexer.Lexer(sourcecode, "test_parser.py input"))

def translate(sourcecode):
    return createParser(sourcecode).compile()
