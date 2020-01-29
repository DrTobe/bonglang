from parser import Parser, UnexpectedEof
from lexer import Lexer
from evaluator import Eval
from symbol_table import SymbolTable
import objects

import sys
import traceback

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
        # TODO (The following is not implemented at all yet, furthermore, it
        # needs more thinking because the syntax is a little bit more
        # complicated)
        # New approach for tab-completion: Forward the ugly work to
        # the bash-complete bash script.
        # In a shell-oriented approach, we could do the following (but for more
        # general bong syntax completion, we maybe use the bong-parser itself?):
        # 1. Split the current line into separate commands (e.g. by ; and |, have
        # a look at $COMP_WORDBREAKS) and each command into separate words
        # (by ' '), determine in which word the caret is currently.
        # 2. If the caret is in the first word, we are completing a) bong-symbols,
        # b) paths (absolute, relative) that should finally expand to a
        # command-name or c) global command-names. For a), we just refer to the
        # current symbol table while for b) and c), we can pass that work to
        # the bash-complete bash script. TODO This, by-the-way, has to be 
        # amended by the possibility to run compgen -d, -c and -f to complete
        # directories, commands and files. The result will be a little bit too
        # bash-centric (e.g. it will complete bash-only commands) but
        # nevertheless, this would spare us a lot of work :)
        # 3. If the caret is not in the first word, we are completing the
        # arguments to whatever is the first word (could be a) a command or b) a
        # bong function). Then, we have to go back to the first word and
        # extract the command-name / function-name. For a), we will forward the
        # ugly work to the bash-complete bash script. For b), we can match the
        # current symbol table against the required type.
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
    # For a stricter mode, uncomment the following two lines. Currently, this
    # is disabled because it generates warnings when piped subprocesses are
    # spawned.
    #import warnings
    #warnings.simplefilter("always")
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
            # Distinguish between quit and exit (different returncode). Like
            # this, you can start repl from bash (autostart from .bashrc) and 
            # quit the whole shell in one case while leaving it open in the
            # other.
            if inp == "quit" or inp == "q":
                return 1
            elif inp == "exit":
                return 0
            code += inp + "\n"
            l = Lexer(code)
            # TODO I think we need to return the current symtable / scope from
            # p.compile() or evakuator.evakuate() in the future so that we
            # use the correct one after having opened a new scope. And for
            # tab-completion as well, of course.
            # Okay, scopes/blocks have to be parsed/evaluated as a whole anyways
            # so after Parser.compile() the result will always be the top level
            # symbol table / environment.
            # For tab-completion, do we want to support local/scoped variables?
            p = Parser(l, symtable)
            try:
                program = p.compile()
                evaluated = evaluator.evaluate(program)
                code = ""
                if evaluated != None:
                    print(str(evaluated))
                    if isinstance(evaluated, objects.ReturnValue):
                        exitcode = 0
                        if evaluated.value != None:
                            exitcode = evaluated.value
                        sys.exit(exitcode)
                # Debugging output
                #print(str(symtable))
                #print(str(evaluator.environment))
            except UnexpectedEof as e:
                pass
        except Exception as e:
            print("you fucked up: " + str(e)) 
            print(traceback.format_exc())
            code = ""

if __name__ == "__main__":
    exit(main())
