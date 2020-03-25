# bonglang
Programming language that makes heavy use of pipes/bongs.

## tests
Currently, there are only tests for the lexer. To run them, type: `python -m unittest test_lexer.py`

## grammar
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
primary -> INT_VALUE | FLOAT_VALUE | STRING | BOOL_VALUE | IDENTIFIER ( LPAREN arguments RPAREN )? | LBAREN expression RPAREN | LBRACKET commata_expression? RBRACKET | !!SYSCALL!!
arguments -> empty | commata_expressions
commata_expressions -> expression ( COMMA expression ) \*
empty -> ()
