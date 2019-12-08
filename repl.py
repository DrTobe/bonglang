from parser import Parser
from lexer import Lexer
from evaluator import Eval
import traceback

def main():
    evaluator = Eval()
    while True:
        try:
            code = input(">")
            if code == "q":
                break
            l = Lexer(code)
            p = Parser(l)
            program = p.compile()
            evaluator.evaluate(program)
        except Exception as e:
            print("you fucked up: " + str(e)) 
            print(traceback.format_exc())

if __name__ == "__main__":
    main()
