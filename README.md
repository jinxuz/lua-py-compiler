# lua-py-compiler
A Lua compiler written in Python. It supports basic statements of Lua such as function call and tables.

## Files
analyser.py: Generate instructions from AST.
config.py: Configs and consts.
info.py: Class of function info.
lexer.py: Extract lexemes.
lua_stack.py: Class of Lua stack of virtual machine.
lua_table.py: Class of table in Lua langauge.
lua_utils.py: Utility functions.
main.py: The main entrance.
parser.py: Parse series of lexemes to generate AST.
tokens.py: Token types in Lua language.
vm.py: Lua virtual machine to execute instructions.

## Usage
Replace the Lua codes in *main.py* or use *run* function in *vm.py*.

## Notes
This compiler has not supported long strings, label and goto statements, tail recursion, meta methods and libraries yet.

## Reference
The structure of the compiler is from 《自己动手实现Lua》: https://github.com/zxh0/luago-book
