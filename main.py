import sys
import lexer
import parser
import evaluator
import repl

def main():
    arguments = sys.argv
    if len(arguments) == 1:
        return repl.main()
    if len(arguments) >= 2:
        with open(arguments[1]) as f:
            code = f.read()
            l = lexer.Lexer(code)
            p = parser.Parser(l)
            program = p.compile()
            evaluator.Eval().evaluate(program)
    else:
        print("Too many arguments\nrun without arguments to start the REPL or run with one file as argument to evaluate")

if __name__ == "__main__":
    main()
