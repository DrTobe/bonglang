from parser import Parser
from lexer import Lexer
from evaluator import Eval
import traceback
from symbol_table import SymbolTable

def main():
    evaluator = Eval()
    symtable = SymbolTable()
    while True:
        try:
            code = input(">")
            if code == "q":
                break
            l = Lexer(code)
            p = Parser(l, symtable)
            program = p.compile()
            evaluator.evaluate(program)
        except Exception as e:
            print("you fucked up: " + str(e)) 
            print(traceback.format_exc())
            p = Parser(l, symtable)

if __name__ == "__main__":
    main()
