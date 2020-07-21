from config import REG_LIMIT


class LocalVarInfo:

    def __init__(self, prev, name, scope_level, slot, captured=False):
        self.prev = prev
        self.name = name
        self.scope_level = scope_level
        self.slot = slot
        self.captured = captured


class UpValueInfo:

    def __init__(self, local_var_slot, up_value_idx, idx):
        self.local_var_slot = local_var_slot
        self.up_value_idx = up_value_idx
        self.idx = idx


class FuncInfo:

    def __init__(self):
        self.constants = {}
        self.used_regs = 0
        self.max_regs = 0
        self.scope_level = 0
        # self.local_vars = []
        self.local_names = {}
        self.breaks = []
        self.parent = None
        self.up_values = {}

        self.sub_funcs = []
        self.param_num = 0
        self.is_vararg = False

        self.ins = []

    @staticmethod
    def error(s=""):
        print(s)

    def index_of_constant(self, c):
        if c in self.constants:
            return self.constants[c]
        else:
            self.constants[c] = len(self.constants)
            return self.constants[c]

    def alloc_reg(self):
        self.used_regs += 1
        if self.used_regs >= REG_LIMIT:
            self.error('register number exceeds limit %d' % REG_LIMIT)
        self.max_regs = max(self.max_regs, self.used_regs)
        return self.used_regs - 1

    def free_reg(self):
        self.used_regs -= 1

    def alloc_regs(self, n):
        for _ in range(n):
            self.alloc_reg()
        return self.used_regs - n

    def free_regs(self, n):
        for _ in range(n):
            self.free_reg()

    def add_local_var(self, name):
        new_var = LocalVarInfo(name=name, prev=self.local_names.get(name, None),
                               scope_level=self.scope_level, slot=self.alloc_reg())
        # self.local_vars.append(new_var)
        self.local_names[name] = new_var
        return new_var.slot

    def slot_of_local_var(self, name):
        if name in self.local_names:
            return self.local_names[name].slot
        return -1

    def enter_scope(self, breakable):
        self.scope_level += 1
        if breakable:
            self.breaks.append([])
        else:
            self.breaks.append(None)

    def exit_scope(self):
        break_jumps = self.breaks[-1]
        self.breaks.pop()
        if break_jumps is not None:
            a = self.get_jump_arg()
            for pc in break_jumps:
                self.fix_a(pc, a)
                self.fix_b(pc, self.pc() - pc)
        self.scope_level -= 1
        values = list(self.local_names.values())
        for v in values:
            if v.scope_level > self.scope_level:
                self.remove_local_var(v)

    def remove_local_var(self, v: LocalVarInfo):
        self.free_reg()
        if v.prev is None:
            self.local_names.pop(v.name)
        elif v.prev.scope_level == v.scope_level:
            self.remove_local_var(v.prev)
        else:
            self.local_names[v.name] = v.prev

    def add_break_jump(self, pc):
        for i in range(self.scope_level, -1, -1):
            if self.breaks[i] is not None:
                self.breaks[i].append(pc)
                return
        self.error('break not inside a loop')

    def get_jump_arg(self):
        has_captured = False
        min_slot = self.max_regs
        for var in self.local_names.values():
            if var.scope_level == self.scope_level:
                v = var
                while v is not None and v.scope_level == self.scope_level:
                    if v.captured:
                        has_captured = True
                    if v.slot < min_slot and v.name[0] is not '(':
                        min_slot = v.slot
                    v = v.prev
        if has_captured:
            return min_slot + 1
        return 0

    def index_of_up_value(self, name):
        if name in self.up_values:
            return self.up_values[name].idx
        if self.parent is not None:
            if name in self.parent.local_names:
                local_var = self.parent.local_names[name]
                idx = len(self.up_values)
                self.up_values[name] = UpValueInfo(local_var.slot, -1, idx)
                local_var.captured = True
                return idx
            uv_idx = self.parent.index_of_up_value(name)
            if uv_idx < 0:
                return uv_idx
            idx = len(self.up_values)
            self.up_values[name] = UpValueInfo(-1, uv_idx, idx)
            return idx
        return -1

    def close_open_up_values(self):
        a = self.get_jump_arg()
        if a > 0:
            self.emit('jump', a, 0)

    def pc(self):
        return len(self.ins) - 1

    def emit(self, inst, a, b, c=None):
        if inst == 'load_k':
            b = self.index_of_constant(b)
        if c is None:
            self.ins.append([inst, a, b])
        else:
            self.ins.append([inst, a, b, c])
        return self.pc()

    def fix_b(self, pc, b):
        self.ins[pc][2] = b

    def fix_a(self, pc, a):
        self.ins[pc][1] = a
