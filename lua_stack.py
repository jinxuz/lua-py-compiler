from tokens import TOKEN
from lua_utils import *
from lua_table import Table
from config import *


def type_of(v):
    if type(v) in [type(None), int, float, str, bool, Table, Closure]:
        return type(v)
    else:
        return None


class UpVal:

    def __init__(self, v):
        self.val = v


class Closure:

    def __init__(self, prototype, py_func=None, up_len=0):
        self.prototype = prototype
        self.py_func = py_func
        if prototype is not None:
            up_len = len(prototype.up_values)
        self.up_values = [None] * up_len


class Stack:

    def __init__(self, closure=None, prev=None, state=None):
        self.slots = []
        self.prev = prev
        self.state = state
        self.closure = closure
        self.varargs = []
        self.pc = 0
        self.open_uvs = {}

    def error(self, s=""):
        print('Lua Core error: %s' % s)
        print('current stack:')
        print(self.slots)

    def push(self, v):
        self.slots.append(v)
        if len(self) > MAX_STACK:
            self.error('lua stack overflow')

    def push_n(self, args, n):
        if n < 0:
            n = len(args)
        for i in range(n):
            if i >= len(args):
                self.push(None)
            else:
                self.push(args[i])

    def pop(self, n=1):
        if len(self.slots) < n:
            self.error('illegal pop: empty stack')
            return None
        else:
            res = None
            for _ in range(n):
                res = self.slots.pop()
            return res

    def pop_n(self, n):
        res = []
        for _ in range(n):
            res.append(self.slots.pop())
        res.reverse()
        return res

    def is_valid(self, idx):
        if idx < REGISTRY_INDEX:
            idx = REGISTRY_INDEX - idx - 1
            return self.closure is not None and idx < len(self.closure.up_values)
        if idx == REGISTRY_INDEX:
            return True
        idx = self.abs_index(idx)
        return 0 <= idx - 1 < len(self.slots)

    def get(self, idx):
        if idx < REGISTRY_INDEX:
            idx = REGISTRY_INDEX - idx - 1
            if self.closure is not None and idx < len(self.closure.up_values):
                return self.closure.up_values[idx].val
            else:
                return None
        if idx == REGISTRY_INDEX:
            return self.state.registry
        idx = self.abs_index(idx)
        if self.is_valid(idx):
            return self.slots[idx - 1]
        return None

    def set(self, idx, val):
        if idx < REGISTRY_INDEX:
            idx = REGISTRY_INDEX - idx - 1
            if self.closure is not None and idx < len(self.closure.up_values):
                self.closure.up_values[idx] = UpVal(val)
            return
        if idx == REGISTRY_INDEX:
            self.state.registry = val
            return
        idx = self.abs_index(idx)
        if idx > MAX_STACK:
            self.error('lua stack overflow')
        if self.is_valid(idx):
            self.slots[idx - 1] = val
        elif idx > len(self.slots):
            while idx > len(self.slots):
                self.slots.append(None)
            self.slots[idx - 1] = val

    def get_top(self):
        return self.slots[-1]

    def copy(self, from_idx, to_idx):
        self.set(to_idx, self.get(from_idx))

    def push_value(self, idx):
        self.push(self.get(idx))

    def replace(self, idx):
        self.set(idx, self.pop())

    def insert(self, idx):
        self.rotate(idx, 1)

    def remove(self, idx):
        self.rotate(idx, -1)
        self.pop(1)

    def abs_index(self, idx):
        if idx >= 0 or idx <= REGISTRY_INDEX:
            return idx
        else:
            return len(self.slots) + idx + 1

    def rotate(self, idx, step):
        t = len(self.slots) - 1
        p = self.abs_index(idx) - 1
        if t - p + 1 == 0:
            return
        step = (-step) % (t - p + 1)
        self.slots = self.slots[:p] + self.slots[p + step:] + self.slots[p: p + step]

    def set_top(self, idx):
        idx = self.abs_index(idx)
        if idx < 0:
            self.error('stack underflow')
        while len(self.slots) > idx:
            self.pop()
        while len(self.slots) < idx:
            self.push(None)

    def type(self, idx):
        if not self.is_valid(idx):
            return None
        v = self.get(idx)
        return type_of(v)

    def is_none(self, idx):
        return self.type(idx) is None

    def is_nil(self, idx):
        return self.type(idx) is type(None)

    def is_none_or_nil(self, idx):
        return self.is_none(idx) or self.is_nil(idx)

    def is_boolean(self, idx):
        return self.type(idx) is bool

    def is_string(self, idx):
        return self.type(idx) in [str, int, float]

    def is_number(self, idx):
        return self.to_number_x(idx)[1]

    def is_integer(self, idx):
        try:
            int(self.get(idx))
            return True
        except TypeError:
            return False
        # return self.to_integer_x(idx)[1]

    def to_number(self, idx):
        return self.to_number_x(idx)[0]

    def to_number_x(self, idx):
        v = self.get(idx)
        try:
            v = float(v)
            return v, True
        except TypeError:
            return 0, False

    def to_boolean(self, idx):
        v = self.get(idx)
        return self.to_boolean_v(v)

    @staticmethod
    def to_boolean_v(v):
        return convert_to_boolean(v)

    def to_integer(self, idx):
        return self.to_integer_x(idx)[0]

    def to_integer_x(self, idx):
        v = self.get(idx)
        return self.convert_to_integer(v)

    @staticmethod
    def convert_to_integer(v):
        return convert_to_integer(v)

    @staticmethod
    def convert_to_float(v):
        return convert_to_float(v)

    def to_string(self, idx):
        return self.to_string_x(idx)[0]

    def to_string_x(self, idx):
        v = self.get(idx)
        if type(v) is str:
            return v, True
        if type(v) in [int, float]:
            s = str(v)
            self.set(idx, s)
            return s, True
        return "", False

    def __repr__(self):
        return self.slots.__repr__()

    def __len__(self):
        return len(self.slots)

    def arith(self, op, uni_op=False):
        b = self.pop()
        if uni_op:
            a = b
        else:
            a = self.pop()
        if op in [TOKEN.OP_BAND, TOKEN.OP_BOR, TOKEN.OP_BXOR, TOKEN.OP_SHL, TOKEN.OP_SHR]:
            b, bf = self.convert_to_integer(b)
            a, af = self.convert_to_integer(a)
            if af and bf:
                if op == TOKEN.OP_BAND:
                    self.push(a & b)
                elif op == TOKEN.OP_BOR:
                    self.push(a | b)
                elif op == TOKEN.OP_BXOR:
                    if uni_op:
                        self.push(~b)
                    else:
                        self.push(a ^ b)
                elif op == TOKEN.OP_SHL:
                    if b >= 0:
                        self.push(a << b)
                    else:
                        self.push(a >> (-b))
                elif op == TOKEN.OP_SHR:
                    if b >= 0:
                        self.push(a >> b)
                    else:
                        self.push(a << -b)
            else:
                self.error('illegal bitwise computation ' + op)
        elif op in [TOKEN.OP_DIV, TOKEN.OP_POW]:
            b, bf = self.convert_to_float(b)
            a, af = self.convert_to_float(a)
            if af and bf:
                if op == TOKEN.OP_DIV:
                    self.push(a / b)
                elif op == TOKEN.OP_POW:
                    self.push(a ** b)
            else:
                self.error('illegal computation ' + op)
        else:
            bb, bf = self.convert_to_integer(b)
            aa, af = self.convert_to_integer(a)
            if bf and af:
                b = bb
                a = aa
            else:
                b, bf = self.convert_to_float(b)
                a, af = self.convert_to_float(a)
            if bf and af:
                if op == TOKEN.OP_ADD:
                    self.push(a + b)
                elif op == TOKEN.OP_MINUS:
                    if uni_op:
                        self.push(-b)
                    else:
                        self.push(a - b)
                elif op == TOKEN.OP_MUL:
                    self.push(a * b)
                elif op == TOKEN.OP_IDIV:
                    self.push(a // b)
                elif op == TOKEN.OP_MOD:
                    self.push(a % b)
                else:
                    self.error(op + 'not support')
            else:
                self.error('illegal computation ' + op)

    def length(self, idx):
        v = self.get(idx)
        if type(v) in [str, Table]:
            self.push(len(v))
        else:
            self.error('length error')

    def concat(self, n):
        if n == 0:
            self.push("")
            return
        for _ in range(n - 1):
            if self.is_string(-1) and self.is_string(-2):
                s2 = self.to_string(-1)
                s1 = self.to_string(-2)
                self.pop(2)
                self.push(s1 + s2)

    def _eq(self, a, b):
        if a is None:
            return b is None
        if type(a) is bool:
            return self.to_boolean_v(b) == a
        if type(a) is str:
            return type(b) is str and a == b
        if type(a) in [int, float]:
            return type(b) in [int, float] and a == b
        return a == b

    def _lt(self, a, b):
        if type(a) is str:
            return type(b) is str and a < b
        if type(a) in [int, float]:
            return type(b) in [int, float] and a < b
        self.error('illegal comparison')

    def _le(self, a, b):
        if type(a) is str:
            return type(b) is str and a <= b
        if type(a) in [int, float]:
            return type(b) in [int, float] and a <= b
        self.error('illegal comparison')

    def compare(self, idx1, idx2, op):
        if op == TOKEN.OP_GT:
            return self.compare(idx2, idx1, TOKEN.OP_LT)
        if op == TOKEN.OP_GE:
            return self.compare(idx2, idx1, TOKEN.OP_LE)
        if op == TOKEN.OP_NE:
            return not self.compare(idx1, idx2, TOKEN.OP_EQ)
        a = self.get(idx1)
        b = self.get(idx2)
        if op == TOKEN.OP_EQ:
            return self._eq(a, b)
        if op == TOKEN.OP_LT:
            return self._lt(a, b)
        if op == TOKEN.OP_LE:
            return self._le(a, b)
        self.error('invalid compare op ' + str(op))

    def create_table(self):
        self.push(Table())

    def get_table(self, idx):
        t = self.get(idx)
        k = self.pop()
        self._get_table(t, k)

    def _get_table(self, t, k):
        if type(t) is Table:
            v = t.get(k)
            self.push(v)
            return type_of(v)
        else:
            self.error(repr(t) + ' not a table')

    def get_field(self, idx, k):
        t = self.get(idx)
        return self._get_table(t, k)

    def set_table(self, idx):
        t = self.get(idx)
        v = self.pop()
        k = self.pop()
        self._set_table(t, k, v)

    def _set_table(self, t, k, v):
        if type(t) is Table:
            t.put(k, v)
        else:
            self.error(repr(t) + ' not a table')

    def set_field(self, idx, k):
        t = self.get(idx)
        v = self.pop()
        self._set_table(t, k, v)

    def table_next(self, idx):
        t = self.get(idx)
        assert type(t) is Table
        key = self.pop()
        next_key = t.next_key(key)
        if next_key is None:
            return False
        self.push(next_key)
        self.push(t.get(next_key))
        return True

