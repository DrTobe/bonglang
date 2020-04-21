# bonglang
A programming language that makes heavy use of pipes/bongs, or: a shell that offers a syntax familiar to software developers.

## Features / Examples
```
// Single-line comments
/* Multi-line
   comments */

// Directory navigation
cd                      // back to home directory
cd /usr/bin             // absolute paths
cd foo/bar              // relative paths
cd -                    // back to previous directory
cd ~/                   // home-directory expansion

// Program calls as fallback for unknown identifiers
ls
ls -la
cat foo.txt
grep bar foo.txt

// Basic pipelines
ls -la | grep foo
cat foo.txt | head | sort

// Advanced program calls and pipelines
let returnCode = grep foo bar.txt                    // store returncode of program call in variable
grep bar foo.txt | let stdout                        // store stdout in variable
cat foo.txt | let stdout, stderr                     // store stdout and stderr in variables
let returnCode = grep foo bar.txt | let matches      // everything at once

// Builtin functions
print("Hello, World!")    // print to stdout
len("Hello, World!")      // 13
len([1, 2, 3, 4])         // 4
get_argv()                // array of program arguments

// Builtin types, type hints are optional!
let a : int = 1
let b : float = 2.0
let c : str = "3"
let d : bool = true || false    // logical or: ||
let e : []int = [1, 2, 3]
let f : []float = []            // for empty arrays, type hints are required!

// Type definitions and instantiations (structs)
struct T {
    x : int,
    y : int }                 // a tiny bug requires us to close the braces here :)
let t = T { x : 3, y : 7 }    // Optionally: let t : T = ...

// Function definitions
func recursiveFaculty(n: int) : int {
    if n <= 1 {
        return 1
    }
    else {
        return n * faculty(n-1)
    }
}
func loopFaculty(n: int) : int {
    let result = 1
    while n > 1 {
        result = result * n
        n = n - 1
    }
    return result
}
recursiveFaculty(1)       // 1
recursiveFaculty(5)       // 120
loopFaculty(5)            // 120

// Module imports
import "module.bon" as mod
mod.faculty(5)                      // function call in module
let t = mod.T { x : 5 }             // type from module
```

Since `bong` is still in the development and specification process, everything can change at all times. Furthermore, some features may not be extremely stable and a lot of nice features are still missing (have a look at the issue page). Feel free to contribute :)

## Implementation
The current version is implemented in Python >= 3.8 (due to [assignment expressions](https://www.python.org/dev/peps/pep-0572/)). The main process of compilation/interpretation is the following:

1.  Input is either read from a script file or an interactive repl:
    *  `main.py` reads the input file if a filename is given as an argument, otherwise `repl.py` is started
    *  `repl.py` opens an interactive shell with basic shell features like tab-completion
1.  `lexer.py` accepts `bong`-code and transforms it into Tokens which are specified by `token_def.py`
2.  `parser.py` generates an abstract syntax tree whose contents are specified by `ast.py`, the root is an `ast.TranslationUnit`
3.  `typechecker.py` resolves imports and type-definitions (only structs supported currently) and ensures type-safety, the result is an `ast.Program` which contains a main `ast.TranslationUnit` and a dictionary of modules which are `ast.TranslationUnit`s
4.  `evaluator.py` runs the `ast.Program`

To facilitate mixing shell commands (and external program calls) and bong statements/expressions, all defined names (variables, function names, typenames, module names) are registered in the symbol table by the parser when they are encountered first. Whenever an identifier is found that is not registered in the symbol table, an external program call is parsed.

## Tests
There are tests for all the main components of bonglang. To run them all, type `tests_run` in the main directory. This script additionally runs `mypy`, if installed, to verify all type hints that are given in the implementation.

## Grammar
```
program -> top_level_stmt
top_level_stmt -> import | func_definition | stmt
import -> IMPORT STRING AS IDENTIFIER SEMICOLON?
func_definition -> FUNC IDENTIFIER LPAREN parameters RPAREN ( COLON type (COMMA type)\* )? block_stmt
stmt -> print_stmt | let_stmt | if_stmt | return_stmt | while_stmt | block_stmt | expr_stmt
parameters -> empty | parameter ( COMMA parameter )\*
parameter -> IDENTIFIER COLON type
type -> ( LBRACKET RBRACKET )\* IDENTIFIER
print_stmt -> PRINT expression SEMICOLON?
let_stmt -> let_lhs ASSIGN assignment SEMICOLON?
if_stmt -> IF expression block_stmt ( ELSE ( if_stmt | block_stmt ) )?
return_stmt -> RETURN commata_expressions? SEMICOLON? 
while_stmt -> WHILE expression block_stmt
block_stmt -> LBRACE stmt\* RBRACE
expr_stmt -> assignment SEMICOLON?
let_lhs -> LET let_variables
let_variables -> let_variable ( COMMA let_variable )\*
let_variable -> IDENTIFIER COLON type
assignment -> commata_expression ( ASSIGN assignment)?
expression -> or
or -> and ( OR and )\*
and -> not ( AND not )\*
not -> ( NEG not )\* compare
compare -> pipeline ( ( EQ | NEQ | GT | GE | LT | LE ) pipeline )\*
pipeline -> addition ( BONG ( let_lhs | commata_expression | addition ) )\* AMPERSAND?
addition -> multiplication ( ( ADD | SUB ) multiplication )\*
multiplication -> signed ( ( MULT | DIV | MOD ) signed )\*
signed -> ( SUB | ADD )? exponentiation
exponentiation -> index_access ( POW exponentiation )?
index_access -> primary ( LBRACKET expression RBRACKET )\*
primary -> INT_VALUE | FLOAT_VALUE | STRING | BOOL_VALUE | IDENTIFIER ( LPAREN arguments RPAREN )? | LPAREN expression RPAREN | LBRACKET commata_expression? RBRACKET | !!SYSCALL!!
arguments -> empty | commata_expressions
commata_expressions -> expression ( COMMA expression ) \*
empty -> ()
```
