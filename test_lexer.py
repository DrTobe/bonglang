import unittest
import lexer
from token_def import *

class TestLexer(unittest.TestCase):
    def test_bong(self):
        sourcecode = "|"
        expectedTypes = [BONG]
        test_token_types(self, sourcecode, expectedTypes)

    def test_singleline_comments(self):
        sourcecode = "print + // Hello World */ 2"
        expectedTypes = [PRINT, OP_ADD]
        test_token_types(self, sourcecode, expectedTypes)
        sourcecode = "// This is a comment that starts at the begi ..."
        expectedTypes = []
        test_token_types(self, sourcecode, expectedTypes)

    def test_multiline_comments(self):
        sourcecode = "print + /* Here, we have \n specified a multiline ...*/"
        expectedTypes = [PRINT, OP_ADD]
        test_token_types(self, sourcecode, expectedTypes)
        sourcecode = "*/ + + /* btw, what happens when we start with */ //?"
        expectedTypes = [OP_MULT, OP_DIV, OP_ADD, OP_ADD]
        test_token_types(self, sourcecode, expectedTypes)
        sourcecode = "    +    /* can we let a comment unclosed?"
        expectedTypes = [OP_ADD]
        test_token_types(self, sourcecode, expectedTypes)

    def test_nested_comments(self):
        sourcecode = "print /* we want /* to have */ two prints */ print"
        expectedTypes = [PRINT, PRINT]
        test_token_types(self, sourcecode, expectedTypes)
        sourcecode = "  ^  /* check for special soeren's bug :) **/   ^^  "
        expectedTypes = [OP_POW, OP_POW, OP_POW]
        test_token_types(self, sourcecode, expectedTypes)

    def test_arithmetic_operators(self):
        sourcecode = "+ - * / % ^"
        expectedTypes = [OP_ADD, OP_SUB, OP_MULT, OP_DIV, OP_MOD, OP_POW]
        test_token_types(self, sourcecode, expectedTypes)

    def test_logical_operators(self):
        sourcecode = "&& ||"
        expectedTypes = [OP_AND, OP_OR]
        test_token_types(self, sourcecode, expectedTypes)

    def test_comparison_operators(self):
        sourcecode = "< > <= >="
        expectedTypes = [OP_LT, OP_GT, OP_LE, OP_GE]
        test_token_types(self, sourcecode, expectedTypes)

    def test_comparison_operators(self):
        sourcecode = "< > <= >="
        expectedTypes = [OP_LT, OP_GT, OP_LE, OP_GE]
        test_token_types(self, sourcecode, expectedTypes)

    def test_equality_operators(self):
        sourcecode = " == !="
        expectedTypes = [OP_EQ, OP_NEQ]
        test_token_types(self, sourcecode, expectedTypes)

    def test_unary_operators(self):
        sourcecode = "- !"
        expectedTypes = [OP_SUB, OP_NEG]
        test_token_types(self, sourcecode, expectedTypes)

    def test_parens(self):
        sourcecode = "( ) ()())"
        expectedTypes = [LPAREN, RPAREN, LPAREN, RPAREN, LPAREN, RPAREN, RPAREN]
        test_token_types(self, sourcecode, expectedTypes)

    def test_integer_literals(self):
        sourcecode = " 1 2 3 123 1337 42 "
        expectedValues = [1, 2, 3, 123, 1337, 42]
        expectedTypes = [INT_VALUE]*len(expectedValues)
        test_token_types(self, sourcecode, expectedTypes)
        test_lexemes(self, sourcecode, expectedValues)

    def test_bool_literals(self):
        sourcecode = "true false true true false"
        expectedValues = ["true", "false", "true", "true", "false"]
        expectedTypes = [BOOL_VALUE]*len(expectedValues)
        test_token_types(self, sourcecode, expectedTypes)
        test_lexemes(self, sourcecode, expectedValues)

    def test_identifiers(self):
        sourcecode = "a b c abc xyz"
        expectedValues = ["a", "b", "c", "abc", "xyz"]
        expectedTypes = [IDENTIFIER]*len(expectedValues)
        test_token_types(self, sourcecode, expectedTypes)
        test_lexemes(self, sourcecode, expectedValues)

    def test_keywords(self):
        sourcecode = "let print let if else while func"
        expectedTypes = [LET, PRINT, LET, IF, ELSE, WHILE, FUNC]
        test_token_types(self, sourcecode, expectedTypes)

def test_token_types(test_class, sourcecode, expectedTypes):
    l = createLexer(sourcecode)
    for t in expectedTypes:
        tok = l.get_token()
        test_class.assertIsInstance(tok, Token, "expected result to be of type token_def.Token, but got " + str(type(tok)))
        test_class.assertEqual(t, tok.type, "expected " + str(t) + " token,  but got: " + str(tok))

    eof_token = l.get_token()
    test_class.assertIsInstance(eof_token, Token, "expected result to be of type token_def.Token, but got " + str(type(eof_token)))
    test_class.assertEqual(eof_token.type, EOF, "expected EOF token, but got: " + str(eof_token))

def test_lexemes(test_class, sourcecode, expectedValues):
    l = createLexer(sourcecode)
    for v in expectedValues:
        tok = l.get_token()
        expectedValue = str(v)
        test_class.assertEqual(expectedValue, tok.lexeme, "expected \"" + expectedValue + "\",  but got: \"" + str(tok.lexeme) + "\"")

def createLexer(sourcecode):
    return lexer.Lexer(sourcecode)

def run():
    unittest.main()

if __name__ == "__main__":
    run()
