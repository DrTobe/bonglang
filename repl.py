from parser import Parser
from lexer import Lexer
from evaluator import Eval
import traceback
from symbol_table import SymbolTable

import subprocess # now, we're going shell

# it's a pity, I have to define this function, but bong is not yet
# available :(
def run(cmd):
    res = subprocess.run(cmd, stdout=subprocess.PIPE, encoding="utf-8")
    return res.stdout[:-1] # omit \n at the end

def main():
    evaluator = Eval()
    symtable = SymbolTable()
    while True:
        try:
            # towards a nicer repl-experience
            username = run("whoami")
            hostname = run("hostname")
            directory = run("pwd").split("/")[-1]
            char = ">" if username!="root" else "#>"
            repl_line = "[{}@{} {}]{} ".format(username, hostname, directory, char)
            code = input(repl_line)
            if code == "q":
                break
            code += "\n"
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
