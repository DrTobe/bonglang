from parser import Parser, UnexpectedEof
from lexer import Lexer
from evaluator import Eval
import traceback
from symbol_table import SymbolTable

# now, we're going shell
import subprocess
import readline # just this line enables command-history :)
import os

# it's a pity, I have to define this function, but bong is not yet
# available :(
def run(cmd):
    res = subprocess.run(cmd, stdout=subprocess.PIPE, encoding="utf-8")
    return res.stdout[:-1] # omit \n at the end

symtable = SymbolTable() # has to be global now to be accessed by tab_completer()

tab_completer_text = None # 'static' var for tab_completer() in python :(
tab_completer_list = []
def tab_completer(text, i): # i = it is called several times
    global tab_completer_text
    global tab_completer_list
    if text != tab_completer_text:
        # TODO Improvement possibility: When implementing this tab-completion
        # feature, I realized that this could be made arbitrarily complex. For
        # example, the following could be added, too (but we have to consider
        # the trade-off between complexity / code readability and benefit):
        # a) after 'cd', show only local directories
        # b) after 'cd' starting with an absolute path, try to make meaningful
        # suggestions from that path (that seems to be a rather important
        # feature)
        # c) after command names, show possible arguments (ouch! that's hard!)
        # d) ... please continue list :)
        # Finally, we should have a look if there are pre-built autocompletion
        # packages around. For archlinux, for example, I remember installing
        # 'bash-completion' enables completion for pacman commands. Maybe, we
        # have to find out how these packages (for bash) work so that we can
        # automatically transform those for bong.
        tab_completer_text = text
        tab_completer_list = []
        only_local_executables = readline.get_line_buffer().startswith('./') # special case
        # 1. local variables
        if not only_local_executables:
            global symtable
            for name in symtable.names.keys():
                if name.startswith(text):
                    tab_completer_list.append(name)
        # 2. files/directories
        allfilesdirs = os.listdir()
        for filedir in allfilesdirs:
            if filedir.startswith(text):
                if only_local_executables:
                    if os.path.isfile(filedir) and os.access(filedir, os.X_OK):
                        tab_completer_list.append(filedir)
                else:
                    tab_completer_list.append(filedir)
        # 3. programs on path
        if not only_local_executables:
            for pathdir in os.environ['PATH'].split(':'):
                try: # all kinds of directory accesses could fail
                    for filedir in os.listdir(pathdir):
                        if filedir.startswith(text):
                            if os.path.isfile(pathdir+'/'+filedir) and os.access(pathdir+'/'+filedir, os.X_OK):
                                tab_completer_list.append(filedir)
                except Exception as e:
                    pass
    return tab_completer_list[i] if i < len(tab_completer_list) else None

# Debugging tab_completer (you don't see its output when normally run, so
# call it manually):
#tab_completer("test", 0)

def main():
    global symtable
    evaluator = Eval()
    readline.set_completer(tab_completer)
    readline.parse_and_bind("tab: complete")
    code = ""
    while True:
        try:
            # towards a nicer repl-experience
            username = run("whoami")
            hostname = run("hostname")
            directory = run("pwd").split("/")[-1]
            char = ">" if code == "" else "."
            prompt = 2*char if username!="root" else "#"+char
            repl_line = "[{}@{} {}]{} ".format(username, hostname, directory, prompt)
            inp = input(repl_line)
            if inp == "q":
                break
            code += inp + "\n"
            l = Lexer(code)
            # TODO I think we need to return the current symtable / scope from
            # p.compile() or evakuator.evakuate() in the future so that we
            # use the correct one after having opened a new scope. And for
            # tab-completion as well, of course.
            p = Parser(l, symtable)
            try:
                program = p.compile()
                evaluated = evaluator.evaluate(program)
                code = ""
                if evaluated != None:
                    print(str(evaluated))
            except UnexpectedEof as e:
                pass
        except Exception as e:
            print("you fucked up: " + str(e)) 
            print(traceback.format_exc())
            code = ""

if __name__ == "__main__":
    main()
