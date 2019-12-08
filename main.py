#!/usr/bin/python

import token_def as token
from lexer import Lexer
from parser import Parser
from evaluator import Evaluator

def run(code):
    l = Lexer(code)
    p = Parser(l)
    e = Eval()
    program = p.compile()
    e.evaluate(program)

def test(code, expect):
    print("Code: " + code)
    try:
        run(code)
    except Exception as e:
        print("CRASHED: " + str(e))
    print(str(expect) + " expected")
    print()

def main():
    test("print 2 + 4 - 2", 4)
    test("print 4^2", 16)
    test("print 2^2 + 2^3", 12)
    test("print 2*3 - 12", -6)
    test("print 12 - 2^3" , 4)
    test("print (1+2)*3", 9)
    test("print 1 +2 *3", 7)
    test("print (1+2)^(1+2)", 27)
    test("print 27%5", 2)
    test("print (27%5)^2", 4)

if __name__ == "__main__":
    main()
