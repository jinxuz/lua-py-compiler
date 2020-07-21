from lexer import Lexer, TOKEN


class Parser:

    def __init__(self, chunk):
        self.lexer = Lexer(chunk)
        self.cur_token = self.lexer.next_token()

    def error(self, s=""):
        print("Syntax Error: %s at line %d:%d %s" %
              (s, self.lexer.line + 1, self.lexer.col + 1, self.lexer.chunk[self.lexer.line]))

    def parse(self):
        block = self.block()
        if self.cur_token[0] is not TOKEN.EOF:
            print('unreachable code after line %d' % self.lexer.line + 1)
        return block

    def next_token(self, _type=None):
        if self.cur_token[0] != TOKEN.EOF:
            self.cur_token = self.lexer.next_token()
            if _type is not None and self.cur_token[0] != _type:
                self.error('illegal token %s' % self.cur_token[1])

    def block(self):
        block = {'stats': self.stats(), 'ret_exps': self.ret_exps(), 'line': self.lexer.line}
        return block

    def is_block_end(self):
        block_end_list = [TOKEN.RETURN, TOKEN.EOF, TOKEN.END, TOKEN.ELSE, TOKEN.ELSEIF, TOKEN.UNTIL]
        return self.cur_token[0] in block_end_list

    def stats(self):
        stats = []
        while not self.is_block_end():
            stat = self.stat()
            if stat is not None:
                stats.append(stat)
        return stats

    def ret_exps(self):
        if self.cur_token[0] is not TOKEN.RETURN:
            return None
        self.next_token()
        if self.cur_token[0] in [TOKEN.EOF, TOKEN.END, TOKEN.ELSE, TOKEN.ELSEIF, TOKEN.UNTIL]:
            return None
        if self.cur_token[0] is TOKEN.SEP_SEMI:
            self.next_token()
            return None
        exps = self.exps()
        if self.cur_token[0] is TOKEN.SEP_SEMI:
            self.next_token()
        return exps

    def exps(self):
        exps = [self.exp()]
        while self.cur_token[0] is TOKEN.SEP_COMMA:
            self.next_token()
            exps.append(self.exp())
        return exps

    def stat(self):
        if self.cur_token[0] is TOKEN.SEP_SEMI:
            self.next_token()
            return {'type': 'empty'}
        if self.cur_token[0] is TOKEN.BREAK:
            return self.break_stat()
        if self.cur_token[0] is TOKEN.SEP_LABEL:
            return self.label_stat()
        if self.cur_token[0] is TOKEN.GOTO:
            return self.goto_stat()
        if self.cur_token[0] is TOKEN.DO:
            return self.do_stat()
        if self.cur_token[0] is TOKEN.WHILE:
            return self.while_stat()
        if self.cur_token[0] is TOKEN.REPEAT:
            return self.repeat_stat()
        if self.cur_token[0] is TOKEN.IF:
            return self.if_stat()
        if self.cur_token[0] is TOKEN.FOR:
            return self.for_stat()
        if self.cur_token[0] is TOKEN.FUNCTION:
            return self.func_def_stat()
        if self.cur_token[0] is TOKEN.LOCAL:
            return self.local_stat()
        return self.assign_or_func_call_stat()

    def break_stat(self):
        stat = {'type': 'break', 'line': self.lexer.line}
        self.next_token()
        return stat

    def label_stat(self):
        self.next_token(TOKEN.IDENTIFIER)
        _, name = self.cur_token
        self.next_token(TOKEN.SEP_LABEL)
        self.next_token()
        return {'type': 'label', 'name': name}

    def goto_stat(self):
        self.next_token(TOKEN.IDENTIFIER)
        _, name = self.cur_token
        self.next_token()
        return {'type': 'goto', 'name': name}

    def do_stat(self):
        self.next_token()
        block = self.block()
        if self.cur_token[0] is not TOKEN.END:
            self.error('do statement parse error: end missing')
        self.next_token()
        return {'type': 'do', 'block': block}

    def while_stat(self):
        self.next_token()
        exp = self.exp()
        if self.cur_token[0] is not TOKEN.DO:
            self.error('while statement parse error: do missing')
        self.next_token()
        block = self.block()
        if self.cur_token[0] is not TOKEN.END:
            self.error('while statement parse error: end missing')
        self.next_token()
        return {'type': 'while', 'exp': exp, 'block': block}

    def repeat_stat(self):
        self.next_token()
        block = self.block()
        if self.cur_token[0] is not TOKEN.UNTIL:
            self.error('repeat statement parse error: until missing')
        self.next_token()
        exp = self.exp()
        return {'type': 'repeat', 'exp': exp, 'block': block}

    def if_stat(self):
        exps = []
        blocks = []
        self.next_token()
        exps.append(self.exp())
        if self.cur_token[0] is not TOKEN.THEN:
            self.error('if statement parse error: then missing')
        self.next_token()
        blocks.append(self.block())
        while self.cur_token[0] is TOKEN.ELSEIF:
            self.next_token()
            exps.append(self.exp())
            if self.cur_token[0] is not TOKEN.THEN:
                self.error('if statement parse error: then missing')
            self.next_token()
            blocks.append(self.block())
        if self.cur_token[0] is TOKEN.ELSE:
            self.next_token()
            exps.append({'exp_type': TOKEN.TRUE, 'line': self.lexer.line})
            blocks.append(self.block())
        if self.cur_token[0] is not TOKEN.END:
            self.error('if statement parse error: end missing')
        self.next_token()
        return {'type': 'if', 'exps': exps, 'blocks': blocks}

    def for_stat(self):
        self.next_token(TOKEN.IDENTIFIER)
        name = self.cur_token[1]
        self.next_token()
        if self.cur_token[0] is TOKEN.OP_ASSIGN:
            self.next_token()
            exps = self.exps()
            if not 2 <= len(exps) <= 3:
                self.error('for statement parse error: num for incorrect exp')
            if len(exps) == 2:
                exps.append({'exp_type': TOKEN.NUMBER, 'content': 1})
            if self.cur_token[0] is not TOKEN.DO:
                self.error('for statement parse error: do missing')
            self.next_token()
            block = self.block()
            if self.cur_token[0] is not TOKEN.END:
                self.error('for statement parse error: end missing')
            self.next_token()
            return {'type': 'for', 'name': name, 'num': True, 'exps': exps, 'block': block}
        else:
            names = [name]
            if self.cur_token[0] is TOKEN.SEP_COMMA:
                self.next_token()
                names = names + self.names()
            if self.cur_token[0] is not TOKEN.IN:
                self.error('for statement parse error: in missing')
            self.next_token()
            exps = self.exps()
            line = self.lexer.line
            if self.cur_token[0] is not TOKEN.DO:
                self.error('for statement parse error: do missing')
            self.next_token()
            block = self.block()
            if self.cur_token[0] is not TOKEN.END:
                self.error('for statement parse error: end missing')
            self.next_token()
            return {'type': 'for', 'num': False, 'names': names, 'exps': exps, 'block': block, 'line': line}
    
    def names(self):
        if self.cur_token[0] is not TOKEN.IDENTIFIER:
            self.error('names parse error')
        names = [self.cur_token[1]]
        self.next_token()
        while self.cur_token[0] is TOKEN.SEP_COMMA:
            self.next_token(TOKEN.IDENTIFIER)
            names.append(self.cur_token[1])
            self.next_token()
        return names
        
    def local_stat(self):
        self.next_token()
        if self.cur_token[0] is TOKEN.FUNCTION:
            return self.local_func_def_stat()
        elif self.cur_token[0] is TOKEN.IDENTIFIER:
            return self.local_var_stat()
        else:
            self.error('illegal local use')

    def local_func_def_stat(self):
        self.next_token(TOKEN.IDENTIFIER)
        name = self.cur_token[1]
        self.next_token()
        exp = self.func_def_exp()
        return {'type': 'func', 'local': True, 'name': name, 'exp': exp}

    def local_var_stat(self):
        names = self.names()
        exps = []
        if self.cur_token[0] is TOKEN.OP_ASSIGN:
            self.next_token()
            exps = self.exps()
        line = self.lexer.line
        return {'type': 'var', 'local': True, 'names': names, 'exps': exps, 'line': line}

    def func_def_stat(self):
        self.next_token()
        name = self.func_name()
        exp = self.func_def_exp()
        if type(name) is dict and name.get('colon', False):
            exp['params'] = ['self'] + exp['params']
        # return {'type': 'func', 'local': False, 'name': name, 'exp': exp}
        return {'op': 'assign', 'vars': [name], 'exps': [exp]}

    def func_name(self):
        if self.cur_token[0] is not TOKEN.IDENTIFIER:
            self.error('func def error: incorrect func name')
        name = self.cur_token[1]
        self.next_token()
        while self.cur_token[0] is TOKEN.SEP_DOT:
            line = self.lexer.line
            self.next_token()
            if self.cur_token[0] is not TOKEN.IDENTIFIER:
                self.error('func def error: incorrect func name')
            name = {'op': 'access', '1': name, '2': self.cur_token[1], 'line': line}
            self.next_token()
        if self.cur_token[0] is TOKEN.SEP_COLON:
            line = self.lexer.line
            self.next_token()
            if self.cur_token[0] is not TOKEN.IDENTIFIER:
                self.error('func def error: incorrect func name')
            name = {'op': 'access', 'colon': True, '1': name, '2': self.cur_token[1], 'line': line}
            self.next_token()
        return name

    def func_def_exp(self):
        if self.cur_token[0] is not TOKEN.SEP_LPAREN:
            self.error('func def error: left parenthesis missing')
        self.next_token()
        params = self.params()
        if self.cur_token[0] is not TOKEN.SEP_RPAREN:
            self.error('func def error: right parenthesis missing')
        self.next_token()
        block = self.block()
        if self.cur_token[0] is not TOKEN.END:
            self.error('func def error: end missing')
        self.next_token()
        return {'op': 'def', 'params': params, 'block': block}

    def params(self):
        if self.cur_token[0] is TOKEN.VARARG:
            self.next_token()
            return {'var': True, 'params': []}
        elif self.cur_token[0] is TOKEN.SEP_RPAREN:
            return {'var': False, 'params': []}
        elif self.cur_token[0] is TOKEN.IDENTIFIER:
            names = [self.cur_token[1]]
            var = False
            self.next_token()
            while self.cur_token[0] is TOKEN.SEP_COMMA:
                self.next_token()
                if self.cur_token[0] is TOKEN.IDENTIFIER:
                    names.append(self.cur_token[1])
                    self.next_token()
                elif self.cur_token[0] is TOKEN.VARARG:
                    var = True
                    self.next_token()
                    break
                else:
                    self.error('func def error: incorrect parameter definition')
            return {'var': var, 'params': names}
        else:
            self.error('func def error: incorrect parameter definition')

    def assign_or_func_call_stat(self):
        prefix_exp = self.prefix_exp()
        if type(prefix_exp) is dict and 'op' in prefix_exp and prefix_exp['op'] == 'call':
            return prefix_exp
        else:
            var = []
            while 1:
                if type(prefix_exp) is str or type(prefix_exp) is dict and 'op' in prefix_exp and prefix_exp['op'] == 'access':
                    pass
                else:
                    self.error('illegal var')
                var.append(prefix_exp)
                if self.cur_token[0] is not TOKEN.SEP_COMMA:
                    break
                self.next_token()
                prefix_exp = self.prefix_exp()
        if self.cur_token[0] is not TOKEN.OP_ASSIGN:
            self.error('illegal var')
        line = self.lexer.line
        self.next_token()
        exps = self.exps()
        return {'op': 'assign', 'vars': var, 'exps': exps, 'line': line}

    def exp(self):
        return self.exp_or()

    def exp_or(self):
        exp1 = self.exp_and()
        while self.cur_token[0] is TOKEN.OP_OR:
            line = self.lexer.line
            self.next_token()
            exp2 = self.exp_and()
            exp1 = {'op': TOKEN.OP_OR, '1': exp1, '2': exp2, 'line': line}
        return exp1

    def exp_and(self):
        exp1 = self.exp_cmp()
        while self.cur_token[0] is TOKEN.OP_AND:
            line = self.lexer.line
            self.next_token()
            exp2 = self.exp_cmp()
            exp1 = {'op': TOKEN.OP_AND, '1': exp1, '2': exp2, 'line': line}
        return exp1

    def exp_cmp(self):
        exp1 = self.exp_bor()
        cmp_list = [TOKEN.OP_LT, TOKEN.OP_LE, TOKEN.OP_GT, TOKEN.OP_GE, TOKEN.OP_EQ, TOKEN.OP_NE]
        while self.cur_token[0] in cmp_list:
            op = self.cur_token[0]
            line = self.lexer.line
            self.next_token()
            exp2 = self.exp_bor()
            exp1 = {'op': op, '1': exp1, '2': exp2, 'line': line}
        return exp1

    def exp_bor(self):
        exp1 = self.exp_bnot()
        while self.cur_token[0] is TOKEN.OP_BOR:
            line = self.lexer.line
            self.next_token()
            exp2 = self.exp_bnot()
            exp1 = {'op': TOKEN.OP_BOR, '1': exp1, '2': exp2, 'line': line}
        return exp1

    def exp_bnot(self):
        exp1 = self.exp_band()
        while self.cur_token[0] is TOKEN.OP_BNOT:
            line = self.lexer.line
            self.next_token()
            exp2 = self.exp_band()
            exp1 = {'op': TOKEN.OP_BNOT, '1': exp1, '2': exp2, 'line': line}
        return exp1

    def exp_band(self):
        exp1 = self.exp_shift()
        while self.cur_token[0] is TOKEN.OP_BAND:
            line = self.lexer.line
            self.next_token()
            exp2 = self.exp_shift()
            exp1 = {'op': TOKEN.OP_BAND, '1': exp1, '2': exp2, 'line': line}
        return exp1

    def exp_shift(self):
        exp1 = self.exp_concat()
        while self.cur_token[0] in [TOKEN.OP_SHR, TOKEN.OP_SHL]:
            op = self.cur_token[0]
            line = self.lexer.line
            self.next_token()
            exp2 = self.exp_concat()
            exp1 = {'op': op, '1': exp1, '2': exp2, 'line': line}
        return exp1

    def exp_concat(self):
        exps = [self.exp_plus()]
        if self.cur_token[0] is TOKEN.OP_CONCAT:
            line = self.lexer.line
            while self.cur_token[0] == TOKEN.OP_CONCAT:
                self.next_token()
                exps.append(self.exp_plus())
            return {'op': TOKEN.OP_CONCAT, '1': exps, 'line': line}
        return exps[0]

    def exp_plus(self):
        exp1 = self.exp_mul()
        while self.cur_token[0] in [TOKEN.OP_ADD, TOKEN.OP_MINUS]:
            op = self.cur_token[0]
            line = self.lexer.line
            self.next_token()
            exp2 = self.exp_mul()
            exp1 = {'op': op, '1': exp1, '2': exp2, 'line': line}
        return exp1

    def exp_mul(self):
        exp1 = self.exp_unary()
        while self.cur_token[0] in [TOKEN.OP_MUL, TOKEN.OP_DIV, TOKEN.OP_IDIV, TOKEN.OP_MOD]:
            op = self.cur_token[0]
            line = self.lexer.line
            self.next_token()
            exp2 = self.exp_unary()
            exp1 = {'op': op, '1': exp1, '2': exp2, 'line': line}
        return exp1

    def exp_unary(self):
        if self.cur_token[0] in [TOKEN.OP_NOT, TOKEN.OP_LEN, TOKEN.OP_MINUS, TOKEN.OP_WAVE]:
            op = self.cur_token[0]
            line = self.lexer.line
            self.next_token()
            exp1 = self.exp_unary()
            exp1 = {'op': op, '1': exp1, 'line': line}
        else:
            exp1 = self.exp_pow()
        return exp1

    def exp_pow(self):
        exp1 = self.exp0()
        if self.cur_token[0] is TOKEN.OP_POW:
            line = self.lexer.line
            self.next_token()
            exp2 = self.exp_unary()
            exp1 = {'op': TOKEN.OP_POW, '1': exp1, '2': exp2, 'line': line}
        return exp1

    def exp0(self):
        line = self.lexer.line
        if self.cur_token[0] in [TOKEN.VARARG, TOKEN.NIL, TOKEN.TRUE, TOKEN.FALSE]:
            res = {'exp_type': self.cur_token[0], 'line': line}
            self.next_token()
            return res
        if self.cur_token[0] is TOKEN.STRING:
            res = {'exp_type': TOKEN.STRING, 'content': self.cur_token[1]}
            self.next_token()
            return res
        if self.cur_token[0] is TOKEN.NUMBER:
            res = {'exp_type': TOKEN.NUMBER, 'content': self.number()}
            self.next_token()
            return res
        if self.cur_token[0] is TOKEN.SEP_LCURLY:
            return self.table()
        if self.cur_token[0] is TOKEN.FUNCTION:
            self.next_token()
            return self.func_def_exp()
        return self.prefix_exp()

    def number(self):
        n = self.cur_token[1]
        n = self._number(n)
        return n

    @staticmethod
    def _number(n):
        n = n.lower()
        if 'x' in n:
            n = n[2:]
            if 'p' in n:
                n, p = n.split('p')
                p = 2 ** int(p)
            else:
                p = 1
            if '.' in n:
                n = n.split('.')
                if len(n[0]) == 0:
                    n[0] = 0
                else:
                    n[0] = int(n[0], 16)
                if len(n[1]) == 0:
                    n[1] = 0
                else:
                    n[1] = int(n[1], 16) / 16 ** len(n[1])
                return float(n[0] + n[1]) * p
            else:
                return int(n, 16) * p
        else:
            if 'e' in n:
                n, p = n.split('e')
                p = 10 ** int(p)
            else:
                p = 1
            if '.' in n:
                n = float(n)
            else:
                n = int(n)
            return n * p

    def table(self):
        self.next_token()
        fields = self.fields()
        if len(fields) > 0:
            keys, values = list(zip(*fields))
        else:
            keys = []
            values = []
        if self.cur_token[0] is not TOKEN.SEP_RCURLY:
            self.error('illegal table construction: right curly bracket missing')
        self.next_token()
        return {'op': 'table', 'keys': keys, 'values': values}

    def fields(self):
        fields = []
        while 1:
            if self.cur_token[0] is TOKEN.SEP_RCURLY:
                return fields
            if self.cur_token[0] is TOKEN.SEP_LBRACK:
                self.next_token()
                k = self.exp()
                if self.cur_token[0] is not TOKEN.SEP_RBRACK:
                    self.error('illegal table key construction: right bracket missing')
                self.next_token(TOKEN.OP_ASSIGN)
                self.next_token()
                v = self.exp()
                fields.append((k, v))
            else:
                exp1 = self.exp()
                if type(exp1) is str:
                    exp1 = {'exp_type': TOKEN.STRING, 'content': exp1}
                if self.cur_token[0] is TOKEN.OP_ASSIGN:
                    self.next_token()
                    exp2 = self.exp()
                    fields.append((exp1, exp2))
                else:
                    fields.append((None, exp1))
            if self.cur_token[0] is TOKEN.SEP_RCURLY:
                return fields
            elif self.cur_token[0] in [TOKEN.SEP_COMMA, TOKEN.SEP_SEMI]:
                self.next_token()
            else:
                self.error('illegal table construction')

    def prefix_exp(self):
        if self.cur_token[0] is TOKEN.IDENTIFIER:
            exp = self.cur_token[1]
            self.next_token()
        elif self.cur_token[0] is TOKEN.SEP_LPAREN:
            exp = self.paren_exp()
        else:
            exp = None
            self.error('illegal statement')

        while 1:
            if self.cur_token[0] is TOKEN.SEP_LBRACK:
                line = self.lexer.line
                self.next_token()
                key = self.exp()
                if self.cur_token[0] is not TOKEN.SEP_RBRACK:
                    self.error('illegal expression: right bracket missing')
                self.next_token()
                exp = {'op': 'access', '1': exp, '2': key, 'line': line}
            elif self.cur_token[0] is TOKEN.SEP_DOT:
                line = self.lexer.line
                self.next_token()
                if self.cur_token[0] is not TOKEN.IDENTIFIER:
                    self.error('illegal expression: identifier expected')
                name = self.cur_token[1]
                self.next_token()
                exp = {'op': 'access', '1': exp, '2': name, 'line': line}

            # function call
            elif self.cur_token[0] in [TOKEN.SEP_COLON, TOKEN.SEP_LPAREN, TOKEN.SEP_LCURLY, TOKEN.STRING]:
                if self.cur_token[0] is TOKEN.SEP_COLON:
                    self.next_token(TOKEN.IDENTIFIER)
                    name = self.cur_token[1]
                    self.next_token()
                else:
                    name = None
                if self.cur_token[0] is TOKEN.SEP_LPAREN:
                    self.next_token()
                    if self.cur_token[0] is not TOKEN.SEP_RPAREN:
                        args = self.exps()
                    else:
                        args = []
                    if self.cur_token[0] is not TOKEN.SEP_RPAREN:
                        self.error('func args error: right parenthesis missing')
                    self.next_token()
                elif self.cur_token[0] is TOKEN.SEP_RCURLY:
                    args = [self.table()]
                elif self.cur_token[0] is TOKEN.STRING:
                    args = [{'exp_type': TOKEN.STRING, 'content': self.cur_token[1]}]
                    self.next_token()
                else:
                    args = []
                    self.error('illegal function call')
                exp = {'op': 'call', 'name': name, 'args': args, 'exp': exp}

            else:
                return exp

    def paren_exp(self):
        self.next_token()
        line = self.lexer.line
        exp = self.exp()
        if self.cur_token[0] is not TOKEN.SEP_RPAREN:
            self.error('illegal statement: right parenthesis missing')
        self.next_token()
        return {'op': 'parenthesis', '1': exp, 'line': line}

