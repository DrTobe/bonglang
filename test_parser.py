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
                TestData("print 1 + 2 13 + 37", "{\nprint (1+2);\n(13+37)\n}\n"),
                TestData("13 42 print 13 + 37 == 42 41 - 21", "{\n13\n42\nprint ((13+37)==42);\n(41-21)\n}\n")
                ]
        test_strings(self, testData)

    def test_print(self):
        testData = [
                TestData("print 1 + 2", "{\nprint (1+2);\n}\n"),
                TestData("print 13 + 37 == 42", "{\nprint ((13+37)==42);\n}\n")
                ]
        test_strings(self, testData)

    def test_expression_statement(self):
        testData = [
                TestData("1", "{\n1\n}\n"),
                TestData("-1", "{\n(-1)\n}\n"),
                TestData("true", "{\ntrue\n}\n"),
                TestData("!false", "{\n(!false)\n}\n"),
                TestData("1 + 2", "{\n(1+2)\n}\n"),
                TestData("1 + 2 + 3", "{\n((1+2)+3)\n}\n"),
                TestData("1 - 2 - 3", "{\n((1-2)-3)\n}\n"),
                TestData("1 + 2 * 3", "{\n(1+(2*3))\n}\n"),
                TestData("4 * 2 + 3", "{\n((4*2)+3)\n}\n"),
                TestData("1 + 2 ^ 3", "{\n(1+(2^3))\n}\n"),
                TestData("1 ^ 2 ^ 3", "{\n(1^(2^3))\n}\n"),
                TestData("true || false && 1 < 2 + 3 * 3 ^ 5" , "{\n(true||(false&&(1<(2+(3*(3^5))))))\n}\n"),
                ]
        test_strings(self, testData)

def test_strings(test_class, testData):
    for td in testData:
        test_string(test_class, td.sourcecode, td.expectedStr)

def test_string(test_class, sourcecode, expectedStr):
    program = translate(sourcecode)
    test_class.assertNotEqual(None, program, "program shouldn't be None")
    program_string = str(program)
    test_class.assertEqual(program_string, expectedStr, "Expected \"" + expectedStr + "\", but got \" " + program_string + "\"")

def createParser(sourcecode):
    return parser.Parser(lexer.Lexer(sourcecode))

def translate(sourcecode):
    return createParser(sourcecode).compile()
