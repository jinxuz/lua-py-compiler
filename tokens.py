from enum import IntEnum


class TOKEN(IntEnum):
    EOF = 0
    VARARG = 1
    SEP_SEMI = 2
    SEP_COMMA = 3
    SEP_DOT = 4
    SEP_COLON = 5
    SEP_LABEL = 6
    SEP_LPAREN = 7
    SEP_RPAREN = 8
    SEP_LBRACK = 9
    SEP_RBRACK = 10
    SEP_LCURLY = 11
    SEP_RCURLY = 12
    OP_ASSIGN = 13
    OP_MINUS = 14
    OP_WAVE = 15
    OP_ADD = 16
    OP_MUL = 17
    OP_DIV = 18
    OP_IDIV = 19
    OP_POW = 20
    OP_MOD = 21
    OP_BAND = 22
    OP_BOR = 23
    OP_SHR = 24
    OP_SHL = 25
    OP_CONCAT = 26
    OP_LT = 27
    OP_LE = 28
    OP_GT = 29
    OP_GE = 30
    OP_EQ = 31
    OP_NE = 32
    OP_LEN = 33
    OP_AND = 34
    OP_OR = 35
    OP_NOT = 36
    BREAK = 37
    DO = 38
    ELSE = 39
    ELSEIF = 40
    END = 41
    FALSE = 42
    FOR = 43
    FUNCTION = 44
    GOTO = 45
    IF = 46
    IN = 47
    LOCAL = 48
    NIL = 49
    REPEAT = 50
    RETURN = 51
    THEN = 52
    TRUE = 53
    UNTIL = 54
    WHILE = 55
    IDENTIFIER = 56
    NUMBER = 57
    STRING = 58
    OP_UNM = OP_SUB = OP_MINUS
    OP_BNOT = OP_BXOR = OP_WAVE


keywords = {
    "and": TOKEN.OP_AND,
    "break": TOKEN.BREAK,
    "do": TOKEN.DO,
    "else": TOKEN.ELSE,
    "elseif": TOKEN.ELSEIF,
    "end": TOKEN.END,
    "false": TOKEN.FALSE,
    "for": TOKEN.FOR,
    "function": TOKEN.FUNCTION,
    "goto": TOKEN.GOTO,
    "if": TOKEN.IF,
    "in": TOKEN.IN,
    "local": TOKEN.LOCAL,
    "nil": TOKEN.NIL,
    "not": TOKEN.OP_NOT,
    "or": TOKEN.OP_OR,
    "repeat": TOKEN.REPEAT,
    "return": TOKEN.RETURN,
    "then": TOKEN.THEN,
    "true": TOKEN.TRUE,
    "until": TOKEN.UNTIL,
    "while": TOKEN.WHILE,
}

token_map = {
    ';': TOKEN.SEP_SEMI,
    ',': TOKEN.SEP_COMMA,
    '(': TOKEN.SEP_LPAREN,
    ')': TOKEN.SEP_RPAREN,
    ']': TOKEN.SEP_RBRACK,
    '{': TOKEN.SEP_LCURLY,
    '}': TOKEN.SEP_RCURLY,
    '+': TOKEN.OP_ADD,
    '-': TOKEN.OP_MINUS,
    '*': TOKEN.OP_MUL,
    '^': TOKEN.OP_POW,
    '%': TOKEN.OP_MOD,
    '&': TOKEN.OP_BAND,
    '|': TOKEN.OP_BOR,
    '#': TOKEN.OP_LEN,

    ':': TOKEN.SEP_COLON,
    '::': TOKEN.SEP_LABEL,
    '/': TOKEN.OP_DIV,
    '//': TOKEN.OP_IDIV,
    '~': TOKEN.OP_WAVE,
    '~=': TOKEN.OP_NE,
    '=': TOKEN.OP_ASSIGN,
    '==': TOKEN.OP_EQ,
    '<': TOKEN.OP_LT,
    '<=': TOKEN.OP_LE,
    '<<': TOKEN.OP_SHL,
    '>': TOKEN.OP_GT,
    '>=': TOKEN.OP_GE,
    '>>': TOKEN.OP_SHR,
}
