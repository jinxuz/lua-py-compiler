from info import FuncInfo
from analyzer import intermediate
from lua_stack import Stack, Closure, UpVal
from lua_table import Table
from tokens import TOKEN
from config import *


class ProtoUpValue:

    def __init__(self, in_stack, idx):
        self.in_stack = in_stack
        self.idx = idx


class Prototype:

    def __init__(self, info: FuncInfo):
        self.info = info
        self.num_params = info.param_num
        self.max_stack = info.max_regs
        self.is_vararg = self.info.is_vararg
        self.code = info.ins

        self.constants = [None] * len(info.constants)
        for k, v in info.constants.items():
            self.constants[v] = k
        # up value is composed of a bool (1 for in stack) and an integer (index)
        self.up_values = [None] * len(info.up_values)
        for v in info.up_values.values():
            if v.local_var_slot >= 0:
                self.up_values[v.idx] = ProtoUpValue(1, v.local_var_slot)
            else:
                self.up_values[v.idx] = ProtoUpValue(0, v.up_value_idx)

        self.prototypes = [Prototype(sub) for sub in info.sub_funcs]


class VM:

    def __init__(self):
        self.stack = Stack(state=self)
        self.registry = Table()
        self.registry.put(LUA_GLOBALS, Table())

    def error(self, s=""):
        print('vm compile error:', s)
        print('current stack:')
        print(self.stack.slots)

    def load(self, prototype):
        c = Closure(prototype)
        self.stack.push(c)
        if len(prototype.up_values) > 0:
            env = self.registry.get(LUA_GLOBALS)
            c.up_values[0] = UpVal(env)
        return 0

    def load_vararg(self, n):
        if n < 0:
            n = len(self.stack.varargs)
        self.stack.push_n(self.stack.varargs, n)

    def load_proto(self, idx):
        prototype = self.stack.closure.prototype.prototypes[idx]
        c = Closure(prototype)
        self.stack.push(c)
        for i in range(len(prototype.up_values)):
            # see the initialization of Prototype
            uv = prototype.up_values[i]
            if uv.in_stack == 1:
                if uv.idx in self.stack.open_uvs:
                    c.up_values[i] = self.stack.open_uvs[uv.idx]
                else:
                    c.up_values[i] = UpVal(self.stack.get(uv.idx + 1))
                    self.stack.open_uvs[uv.idx] = c.up_values[i]
            else:
                c.up_values[i] = self.stack.closure.up_values[uv.idx]

    def call(self, n_args, n_results):
        val = self.stack.get(-n_args - 1)
        if type(val) is not Closure:
            self.error(repr(val) + ' is not a function')
        if val.prototype is None:
            self.call_py_closure(n_args, n_results, val)
        else:
            self.call_closure(n_args, n_results, val)

    def call_closure(self, n_args, n_results, c):
        n_regs = c.prototype.max_stack
        n_params = c.prototype.num_params
        is_vararg = c.prototype.is_vararg
        stack = Stack(closure=c, state=self)
        func_and_args = self.stack.pop_n(n=n_args + 1)
        stack.push_n(func_and_args[1:], n_params)
        if n_args > n_params and is_vararg:
            stack.varargs = func_and_args[n_params + 1:]
        self.push_stack(stack)
        self.stack.set_top(n_regs)
        self.run_closure()
        self.pop_stack()
        if n_results != 0:
            results = stack.pop_n(n=len(stack) - n_regs)
            self.stack.push_n(results, n_results)

    def call_py_closure(self, n_args, n_results, c):
        stack = Stack(closure=c, state=self)
        args = self.stack.pop_n(n=n_args)
        stack.push_n(args, n_args)
        self.stack.pop()
        self.push_stack(stack)
        r = c.py_func(self)
        self.pop_stack()
        if n_results != 0:
            results = stack.pop_n(r)
            self.stack.push_n(results, n_results)

    def run_closure(self):
        while 1:
            inst = self.fetch()
            self.execute(inst)
            if inst[0] == 'return':
                break

    def push_func_and_args(self, a, b):
        if b >= 1:
            for i in range(a, a + b):
                self.stack.push_value(i)
            return b - 1
        else:
            self.fix_stack(a)
            return len(self.stack) - self.register_count() - 1

    def pop_results(self, a, c):
        if c > 1:
            for i in range(a + c - 2, a - 1, -1):
                self.stack.replace(i)
        elif c == 0:
            self.stack.push(a)

    def register_count(self):
        return self.stack.closure.prototype.max_stack

    def g1et_pc(self):
        return self.stack.pc

    def add_pc(self, n):
        self.stack.pc += n

    def fetch(self):
        inst = self.stack.closure.prototype.code[self.stack.pc]
        self.stack.pc += 1
        return inst

    def push_stack(self, stack):
        stack.prev = self.stack
        self.stack = stack

    def pop_stack(self):
        stack = self.stack
        self.stack = stack.prev
        stack.prev = None

    def fix_stack(self, a):
        x = self.stack.to_integer(-1)
        self.stack.pop()
        for i in range(a, x):
            self.stack.push_value(i)
        self.stack.rotate(self.register_count() + 1, x - a)

    def push_global_table(self):
        global_table = self.registry.get(LUA_GLOBALS)
        self.stack.push(global_table)

    def get_global(self, k):
        t = self.registry.get(LUA_GLOBALS)
        return t.get(k)

    def set_global(self, k):
        t = self.registry.get(LUA_GLOBALS)
        v = self.stack.pop()
        t.put(k, v)

    def register(self, name, f):
        self.push_py_func(f)
        self.set_global(name)

    def push_py_func(self, f):
        self.stack.push(Closure(None, py_func=f))

    def push_py_closure(self, f, n):
        c = Closure(None, py_func=f, up_len=n)
        for i in range(n, 0, -1):
            v = self.stack.pop()
            c.up_values[i - 1] = UpVal(v)
        self.stack.push(c)

    def is_py_func(self, idx):
        val = self.stack.get(idx)
        return type(val) is Closure and val.py_func is not None

    def to_py_func(self, idx):
        if self.is_py_func(idx):
            return self.stack.get(idx).py_func
        else:
            return None

    @staticmethod
    def up_value_index(idx):
        return REGISTRY_INDEX - idx

    def get_const(self, idx):
        c = self.stack.closure.prototype.constants[idx]
        self.stack.push(c)
        return c

    def get_rk(self, rk):
        if rk > 0xff:
            self.get_const(rk & 0xff)
        else:
            self.stack.push_value(rk + 1)

    def move(self, a, b):
        a += 1
        b += 1
        self.stack.copy(b, a)

    def _close_up_values(self, a):
        pass

    def jump(self, a, b):
        self.add_pc(b)
        if a != 0:
            self._close_up_values(a)

    def load_nil(self, a, b):
        a += 1
        for i in range(a, a + b + 1):
            self.stack.set(i, None)

    def load_bool(self, a, b, c):
        a += 1
        self.stack.set(a, bool(b))
        if self.stack.get(c):
            self.stack.pc += 1

    def load_k(self, a, b):
        a += 1
        self.get_const(b)
        self.stack.replace(a)

    def _not(self, a, b):
        a += 1
        b += 1
        self.stack.push(not self.stack.to_boolean(b))
        self.stack.replace(a)

    def _test_set(self, a, b, c):
        a += 1
        b += 1
        if self.stack.to_boolean(b) == bool(c):
            self.stack.copy(b, a)
        else:
            self.stack.pc += 1

    def _test(self, a, c):
        if self.stack.to_boolean(a + 1) != bool(c):
            self.stack.pc += 1

    def for_prep(self, a, b):
        a += 1
        self.stack.set(a, self.stack.get(a) - self.stack.get(a + 2))
        self.stack.pc += b

    def for_loop(self, a, b):
        a += 1
        self.stack.set(a, self.stack.get(a) + self.stack.get(a + 2))
        positive = self.stack.to_number(a + 2) >= 0
        if positive and self.stack.compare(a, a + 1, TOKEN.OP_LE) or \
                not positive and self.stack.compare(a, a + 1, TOKEN.OP_GE):
            self.stack.pc += b
            self.stack.copy(a, a + 3)

    def t_for_call(self, a, b):
        a += 1
        self.push_func_and_args(a, 3)
        self.call(2, b)
        self.pop_results(a + 3, b + 1)

    def t_for_loop(self, a, b):
        a += 1
        if not self.stack.is_nil(a + 1):
            self.stack.copy(a + 1, a)
            self.add_pc(b)

    def new_table(self, a):
        self.stack.create_table()
        self.stack.replace(a + 1)

    def get_table(self, a, b, c):
        self.get_rk(c)
        self.stack.get_table(b + 1)
        self.stack.replace(a + 1)

    def set_table(self, a, b, c):
        self.get_rk(b)
        self.get_rk(c)
        self.stack.set_table(a + 1)

    def set_list(self, a, b, c):
        a += 1
        c -= 1
        idx = c * FIELDS_PER_FLUSH
        b_zero = b == 0
        if b_zero:
            b = self.stack.to_integer(-1) - a - 1
            self.stack.pop()
        for i in range(1, b + 1):
            idx += 1
            self.stack.push_value(a + i)
            self.stack.set_field(a, idx)
        if b_zero:
            for j in range(self.register_count() + 1, len(self.stack) + 1):
                idx += 1
                self.stack.push_value(j)
                self.stack.set_field(a, idx)
            self.stack.set_top(self.register_count())

    def _closure(self, a, b):
        self.load_proto(b)
        self.stack.replace(a + 1)

    def _call(self, a, b, c):
        a += 1
        n_args = self.push_func_and_args(a, b)
        self.call(n_args, c - 1)
        self.pop_results(a, c)

    def _return(self, a, b):
        a += 1
        if b > 1:
            for i in range(a, a + b - 1):
                self.stack.push_value(i)
        elif b == 0:
            self.fix_stack(a)

    def _vararg(self, a, b):
        a += 1
        if b != 1:
            self.load_vararg(b - 1)
            self.pop_results(a, b)

    def _self(self, a, b, c):
        a += 1
        b += 1
        c += 1
        self.stack.copy(b, a + 1)
        self.get_rk(c)
        self.stack.get_table(b)
        self.stack.replace(a)

    def get_up_val(self, a, b):
        self.stack.copy(self.up_value_index(b + 1), a + 1)

    def set_up_val(self, a, b):
        self.stack.copy(a + 1, self.up_value_index(b + 1))

    def get_tab_up(self, a, b, c):
        self.get_rk(c)
        self.stack.get_table(self.up_value_index(b + 1))
        self.stack.replace(a + 1)

    def set_tab_up(self, a, b, c):
        self.get_rk(b)
        self.get_rk(c)
        self.stack.set_table(self.up_value_index(a + 1))

    def execute(self, inst):
        # print(inst)
        op = inst[0]
        params = inst[1:]
        if op == 'move':
            self.move(*params)
        elif op == 'jump':
            self.jump(*params)
        elif op == 'load_nil':
            self.load_nil(*(params[:2]))
        elif op == 'load_bool':
            self.load_bool(*params)
        elif op == 'load_k':
            self.load_k(*params)
        elif op in [TOKEN.OP_ADD, TOKEN.OP_MINUS, TOKEN.OP_MUL, TOKEN.OP_MOD, TOKEN.OP_POW, TOKEN.OP_DIV,
                    TOKEN.OP_IDIV, TOKEN.OP_BAND, TOKEN.OP_BOR, TOKEN.OP_BXOR, TOKEN.OP_SHL, TOKEN.OP_SHR]:
            uni_op = len(params) == 2
            if uni_op:
                self.get_rk(params[-1])
            else:
                self.get_rk(params[-2])
                self.get_rk(params[-1])
            self.stack.arith(op, uni_op)
            self.stack.replace(params[0] + 1)
        elif op == TOKEN.OP_LEN:
            a, b = params
            self.stack.length(b + 1)
            self.stack.replace(a + 1)
        elif op == TOKEN.OP_CONCAT:
            a, b, c = params
            a += 1
            b += 1
            c += 1
            for i in range(b, c + 1):
                self.stack.push_value(i)
            self.stack.concat(c - b + 1)
            self.stack.replace(a)
        elif op in [TOKEN.OP_LT, TOKEN.OP_GT, TOKEN.OP_EQ, TOKEN.OP_NE, TOKEN.OP_LE, TOKEN.OP_GE]:
            a, b, c = params
            self.stack.set(a + 1, self.stack.compare(b + 1, c + 1, op))
        elif op == TOKEN.OP_NOT:
            self._not(*params)
        elif op == 'test_set':
            self._test_set(*params)
        elif op == 'test':
            self._test(*params)
        elif op == 'for_prep':
            self.for_prep(*params)
        elif op == 'for_loop':
            self.for_loop(*params)
        elif op == 't_for_call':
            self.t_for_call(*params)
        elif op == 't_for_loop':
            self.t_for_loop(*params)
        elif op == 'new_table':
            self.new_table(params[0])
        elif op == 'set_table':
            self.set_table(*params)
        elif op == 'get_table':
            self.get_table(*params)
        elif op == 'set_list':
            self.set_list(*params)
        elif op == 'closure':
            self._closure(*params)
        elif op == 'call':
            a, b, c = params
            b += 1
            c += 1
            self._call(a, b, c)
        elif op == 'return':
            a, b = params
            b += 1
            self._return(a, b)
        elif op == 'vararg':
            a, b = params
            b += 1
            self._vararg(a, b)
        elif op == 'self':
            self._self(*params)
        elif op == 'get_up_val':
            self.get_up_val(*params)
        elif op == 'set_up_val':
            self.set_up_val(*params)
        elif op == 'get_tab_up':
            self.get_tab_up(*params)
        elif op == 'set_tab_up':
            self.set_tab_up(*params)
        else:
            print(self.stack)
            self.error('%s not support' % str(op))

    def compile(self):
        while self.stack.pc < len(self.stack.closure.prototype.prototypes[0].code):
            inst = self.stack.closure.prototype.prototypes[0].code[self.stack.pc]
            self.execute(inst)
            self.stack.pc += 1


# py functions in Lua language
def lua_print(state: VM):
    print(*state.stack.slots)


def lua_next(state: VM):
    state.stack.set_top(2)
    if state.stack.table_next(1):
        return 2
    else:
        state.stack.push(None)
        return 1


def pairs(state: VM):
    state.push_py_func(lua_next)
    state.stack.push_value(1)
    state.stack.push(None)
    return 3


def i_pairs(state: VM):

    def f(ls: VM):
        i = ls.stack.to_integer(2) + 1
        ls.stack.push(i)
        if ls.stack.get_field(1, i) == type(None):
            return 1
        else:
            return 2

    state.push_py_func(f)
    state.stack.push_value(1)
    state.stack.push(0)
    return 3


def run(code, file=False):
    if file:
        with open(code, 'r') as f:
            code = ' '.join(f.readlines())
    vm = VM()
    vm.register('print', lua_print)
    vm.register('next', lua_next)
    vm.register('pairs', pairs)
    vm.register('ipairs', i_pairs)
    proto = Prototype(intermediate(code)).prototypes[0]
    # print(proto.code)
    vm.load(proto)
    vm.call(0, 0)

