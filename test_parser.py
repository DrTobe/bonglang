import unittest
import lexer
import parser

class TestParser(unittest.TestCase):
    def test_print(self):
        sourcecode = "print 1 + 2"
        expected = "print (1+2);"
        test_string(self, sourcecode, expected)

def test_string(test_class, sourcecode, expectedStr):
    program = translate(sourcecode)
    test_class.assertNotEqual(None, program, "program shouldn't be None")
    program_string = str(program)
    test_class.assertEqual(program_string, expectedStr, "Expected \"" + expectedStr + "\", but got \" " + program_string + "\"")

def createParser(sourcecode):
    return parser.Parser(lexer.Lexer(sourcecode))

def translate(sourcecode):
    return createParser(sourcecode).compile()
