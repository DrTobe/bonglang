#!/usr/bin/python

# Exception that tells us that EOF was found in a situation where we did
# not expect it. This is used advantageous for multi-line statements
# in the REPL.
class UnexpectedEof(Exception):
    pass
