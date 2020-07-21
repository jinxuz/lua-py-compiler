import re
from tokens import *


class Lexer:

    number_pattern = re.compile(r"^0[xX]([0-9a-fA-F]+(\.)?[0-9a-fA-F]*|\.[0-9a-fA-F]+)([pP][+\-]?[0-9]+)?|"
                                r"^([0-9]+(\.)?[0-9]*|\.[0-9]+)([eE][+\-]?[0-9]+)?")
    var_pattern = re.compile(r"[_a-zA-z][\w]*")

    def __init__(self, chunk, chunk_name="", line=0, col=0):
        self.chunk = [line.strip() for line in chunk.splitlines()]
        self.chunk_name = chunk_name
        self.line = line
        self.col = col

    def error(self, s=""):
        print("Lexer Error: %s at line %d:%d %s" % (s, self.line + 1, self.col + 1, self.chunk[self.line]))

    def next_token(self):
        self.skip_whitespace()
        if self.line == len(self.chunk):
            return TOKEN.EOF, "EOF"
        if self.peek() in token_map:
            token = self.peek()
            self.next_char(len(token))
            return token_map[token], token
        elif self.cur_char() in token_map:
            token = self.cur_char()
            self.next_char()
            return token_map[token], token
        elif self.cur_char() == '.' and \
                (self.col == len(self.chunk[self.line]) - 1 or not self.chunk[self.line][self.col + 1].isdigit()):
            if self.test('...'):
                self.next_char(3)
                return TOKEN.VARARG, '...'
            if self.test('..'):
                self.next_char(2)
                return TOKEN.OP_CONCAT, '..'
            self.next_char()
            return TOKEN.SEP_DOT, '.'
        elif self.cur_char() == '[':
            if self.test('[[') or self.test('[='):
                return TOKEN.STRING, self.scan_long_string()
            else:
                self.next_char()
                return TOKEN.SEP_LBRACK, '['
        elif self.cur_char() == "'" or self.cur_char() == '"':
            return TOKEN.STRING, self.scan_short_string()
        elif self.cur_char() in '.1234567890':
            match = re.match(self.number_pattern, self.chunk[self.line][self.col:])
            if match is None:
                self.error('incorrect number representation')
            res = match.string[:match.span()[1]]
            self.next_char(len(res))
            return TOKEN.NUMBER, res
        elif self.cur_char() is '_' or self.cur_char().isalpha():
            match = re.match(self.var_pattern, self.chunk[self.line][self.col:])
            res = match.string[:match.span()[1]]
            self.next_char(len(res))
            if res in keywords:
                return keywords[res], res
            else:
                return TOKEN.IDENTIFIER, res
        else:
            self.error("illegal character %s" % self.cur_char())

    def gen_next_token(self):
        yield self.next_token()

    def skip_whitespace(self):
        while self.line < len(self.chunk):
            if self.col == len(self.chunk[self.line]):
                self.next_line()
            elif self.test('--'):
                self.skip_comment()
            elif self.cur_char() in ['\t', '\r', '\v', '\f', ' ']:
                self.next_char()
            else:
                break

    def cur_char(self):
        if self.col < len(self.chunk[self.line]):
            return self.chunk[self.line][self.col]
        else:
            return '\n'

    def peek(self, n=1):
        return self.chunk[self.line][self.col: self.col + n + 1]

    def test(self, s):
        return self.chunk[self.line][self.col:].startswith(s)

    def next_line(self):
        self.line += 1
        self.col = 0

    def next_char(self, n=1):
        self.col += n

    def skip_comment(self):
        self.next_char(2)
        if self.cur_char == '[':
            self.scan_long_string()
        else:
            self.next_line()

    def scan_long_string(self):  # TODO: extract long strings P268
        self.error('not support long string')

    def scan_short_string(self):
        sep = self.cur_char()
        end = self.chunk[self.line][self.col+1:].find(sep)
        if end == -1:
            self.error('string without an end')
        s = self.chunk[self.line][self.col + 1: self.col + 1 + end]
        res = self.process_string(s)
        self.next_char(len(s) + 2)
        return res

    def process_string(self, s):  # TODO: support numeral escape
        res = ""
        i = 0
        while i < len(s):
            if s[i] == '\\':
                if i + 1 == len(s):
                    self.error("incorrect escape")
                if s[i + 1] == 'a':
                    res += '\a'
                elif s[i + 1] == 'b':
                    res += '\b'
                elif s[i + 1] == 'f':
                    res += '\f'
                elif s[i + 1] == 'n':
                    res += '\n'
                elif s[i + 1] == 'r':
                    res += '\r'
                elif s[i + 1] == 't':
                    res += '\v'
                elif s[i + 1] == 'v':
                    res += '\v'
                elif s[i + 1] == '"':
                    res += '"'
                elif s[i + 1] == "'":
                    res += "'"
                elif s[i + 1] == '\\':
                    res += '\\'
                elif s[i + 1] == '[':
                    res += '['
                elif s[i + 1] == ']':
                    res += ']'
                elif s[i + 1] in '1234567890xuz':
                    self.error("not support escape \\%s" % s[i + 1])
                else:
                    self.error("incorrect escape \\%s" % s[i + 1])
                i += 2
            else:
                res += s[i]
                i += 1
        return res

