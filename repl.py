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
    try:
        res = subprocess.run(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
    except Exception as e:
        print("Command '{}' not found!".format(cmd.split(" ")[0]))
        return ""
    if res.returncode != 0:
        print("Command '{}' failed!".format(cmd.split(" ")[0]))
    return res.stdout[:-1] # omit \n at the end

symtable = SymbolTable() # has to be global now to be accessed by tab_completer()

tab_completer_list = [] # 'static' var for tab_completer() in python :(
def tab_completer(text, i): # i = it is called several times
    global tab_completer_list
    if i == 0:
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
        # the bash-complete bash script.
        # 3. If the caret is not in the first word, we are completing the
        # arguments to whatever is the first word (could be a) a bong function
        # or b) a command). Then, we have to go back to the first word and
        # extract the command-name / function-name. For a), we can match the
        # current symbol table against the required type. For b), we will forward the
        # ugly work to the bash-complete bash script.
        tab_completer_list = []
        bash_complete = os.path.dirname(os.path.realpath(__file__))+"/bash-complete"
        line_buffer = readline.get_line_buffer()
        line_words = line_buffer.split(" ")
        # TODO Step 1 (splitting the command line input) omitted currently
        # Step 2: First-word completion (bong-symbols and bash-complete)
        # TODO Currently, we do not know how to determine the current cursor
        # position. So instead of checking if we are in the first word, we just
        # count words :( -> https://stackoverflow.com/questions/60018367/how-to-get-the-current-cursor-position-in-python-readline
        if len(line_words) == 1:
            # a) bong-symbols (functions and variables)
            # TODO Add bong-builtins?
            global symtable
            for name in symtable.names.keys():
                if name.startswith(text):
                    tab_completer_list.append(name)
            # b/c) bash-complete
            res = run(bash_complete + " 0 " + line_words[0])
            tab_completer_list.extend(res.split(" "))
        else:
            # TODO Distinguishing a) bong-function and b) command not done currently
            # ... only completing system commands
            res = run("{} {} {}".format(bash_complete, len(line_words)-1, line_buffer))
            # Now, tab_completer_list.extend(res.split(" ")) like above does
            # not work because we have disabled the word-splitting be readline
            # (for readline, the whole command-line is a single "word"). Thus,
            # if returning a valid parameter, readline will replace the whole
            # current input by that single parameter (effectively deleting the
            # command name). To prevent, we just build up the whole input line
            # here: Join all words except the last with " " and append the
            # completion result.
            if res: # Prevent "no result" from being interpreted as empty result
                for compl in res.split(" "):
                    # Special case: Append / to all results generated by completing
                    # cd command. TODO Maybe this can be omitted if cd is handled
                    # differently as a bong builtin later?
                    suffix = "/" if line_words[0]=="cd" else ""
                    tab_completer_list.append(" ".join(line_words[:-1])+" "+compl+suffix)
    return tab_completer_list[i] if i < len(tab_completer_list) else None

# Debugging tab_completer (you don't see its output when normally run, so
# call it manually):
#readline.insert_text("cd dev")
#tab_completer("cd dev", 0)

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
    # Unset all completer_delimiters (defaults to `~!@#$%^&*()-=+[{]}\|;:'",<>/? ).
    # This is necessary because, if omitted, the following happens:
    # 1. ./comma <tab>
    # 2. completion function returns "./command"
    # 3. ././command
    # It seems to be simpler just to do the line splitting all by ourselves.
    readline.set_completer_delims("")
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
