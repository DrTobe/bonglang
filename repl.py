from parser import Parser
from lexer import Lexer
from evaluator import Eval
import traceback
from symbol_table import SymbolTable

# now, we're going shell
import subprocess
import readline # just this line enables command-history :)

# it's a pity, I have to define this function, but bong is not yet
# available :(
def run(cmd):
    res = subprocess.run(cmd, stdout=subprocess.PIPE, encoding="utf-8")
    return res.stdout[:-1] # omit \n at the end

def tab_completer(text, i): # i = it is called several times
    return 'bong' if i < 1 else None

def main():
    evaluator = Eval()
    symtable = SymbolTable()
    readline.set_completer(tab_completer)
    readline.parse_and_bind("tab: complete")
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
