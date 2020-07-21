from tokens import TOKEN
from info import *
from parse import Parser
from config import *


def cg_block(f, block):
    for stat in block['stats']:
        cg_stat(f, stat)
    if block['ret_exps'] is not None:
        cg_ret_exps(f, block['ret_exps'])


def is_vararg_or_call(exp):
    return type(exp) is dict and (exp.get('exp_type', None) == TOKEN.VARARG or exp.get('op', None) == 'call')


def cg_ret_exps(f, ret_exps):
    n = len(ret_exps)
    if n == 0:
        f.emit('return', 0, 0)
    flag = is_vararg_or_call(ret_exps[-1])
    for i in range(n):
        r = f.alloc_reg()
        if i == n - 1 and flag:
            cg_exp(f, ret_exps[i], r, -1)
        else:
            cg_exp(f, ret_exps[i], r, 1)
    f.free_regs(n)
    a = f.used_regs
    if flag:
        f.emit('return', a, -1)
    else:
        f.emit('return', a, n)


def cg_stat(f, stat):
    t = stat.get('type', stat.get('op'))
    if t == 'call':
        cg_func_call_stat(f, stat)
    elif t == 'break':
        cg_break_stat(f, stat)
    elif t == 'do':
        cg_do_stat(f, stat)
    elif t == 'repeat':
        cg_repeat_stat(f, stat)
    elif t == 'while':
        cg_while_stat(f, stat)
    elif t == 'if':
        cg_if_stat(f, stat)
    elif t == 'for':
        if stat['num']:
            cg_for_num_stat(f, stat)
        else:
            cg_for_in_stat(f, stat)
    elif t == 'assign':
        cg_assign_stat(f, stat)
    elif t == 'func':
        if stat.get('local', False):
            cg_local_func_def_stat(f, stat)
    elif t == 'var':
        if stat.get('local', False):
            cg_local_var_stat(f, stat)
    elif t == 'empty':
        pass
    # TODO: support goto label
    else:
        print('not support stat %s' % t)
        

def cg_local_func_def_stat(f, stat):
    r = f.add_local_var(stat['name'])
    cg_func_def_exp(f, stat['exp'], r)


def cg_func_call_stat(f, stat):
    r = f.alloc_reg()
    cg_func_call_exp(f, stat, r, 0)
    f.free_reg()


def cg_break_stat(f, stat):
    if stat is not None:
        pc = f.emit('jump', 0, 0)
        f.add_break_jump(pc)


def cg_do_stat(f, stat):
    f.enter_scope(False)
    cg_block(f, stat['block'])
    f.close_open_up_values()
    f.exit_scope()


def cg_while_stat(f, stat):
    pc_before = f.pc()
    r = f.alloc_reg()
    cg_exp(f, stat['exp'], r, 1)
    f.free_reg()
    f.emit('test', r, 0)
    pc_jump_to_end = f.emit('jump', 0, 0)
    f.enter_scope(True)
    cg_block(f, stat['block'])
    f.close_open_up_values()
    f.emit('jump', 0, pc_before - f.pc() - 1)
    f.exit_scope()
    f.fix_b(pc_jump_to_end, f.pc() - pc_jump_to_end)


def cg_repeat_stat(f, stat):
    f.enter_scope(True)
    pc_before = f.pc()
    cg_block(f, stat['block'])
    r = f.alloc_reg()
    cg_exp(f, stat['exp'], r, 1)
    f.free_reg()
    f.emit('test', r, 0)
    f.emit('jump', f.get_jump_arg(), pc_before - f.pc() - 1)
    f.exit_scope()


def cg_if_stat(f, stat):
    pc_jumps_to_ends = []
    pc_jump_to_next = -1
    for i in range(len(stat['exps'])):
        exp = stat['exps'][i]
        if pc_jump_to_next >= 0:
            f.fix_b(pc_jump_to_next, f.pc() - pc_jump_to_next)
        r = f.alloc_reg()
        cg_exp(f, exp, r, 1)
        f.free_reg()
        f.emit('test', r, 0)
        pc_jump_to_next = f.emit('jump', 0, 0)
        f.enter_scope(False)
        cg_block(f, stat['blocks'][i])
        f.close_open_up_values()
        f.exit_scope()
        if i < len(stat['exps']) - 1:
            pc_jumps_to_ends.append(f.emit('jump', 0, 0))
        else:
            pc_jumps_to_ends.append(pc_jump_to_next)
    for pc in pc_jumps_to_ends:
        f.fix_b(pc, f.pc() - pc)


def cg_for_num_stat(f, stat):
    f.enter_scope(True)
    cg_local_var_stat(f, {'names': ['(for idx)', '(for limit)', '(for step)'], 'exps': stat['exps']})
    f.add_local_var(stat['name'])
    a = f.used_regs - 4
    pc_for_prep = f.emit('for_prep', a, 0)
    cg_block(f, stat['block'])
    f.close_open_up_values()
    pc_for_loop = f.emit('for_loop', a, 0)
    f.fix_b(pc_for_prep, pc_for_loop - pc_for_prep - 1)
    f.fix_b(pc_for_loop, pc_for_prep - pc_for_loop)
    f.exit_scope()


def cg_for_in_stat(f, stat):
    f.enter_scope(True)
    cg_local_var_stat(f, {'names': ['(for gen)', '(for state)', '(for ctrl)'], 'exps': stat['exps']})
    for name in stat['names']:
        f.add_local_var(name)
    pc_jump_to_tfc = f.emit('jump', 0, 0)
    cg_block(f, stat['block'])
    f.close_open_up_values()
    f.fix_b(pc_jump_to_tfc, f.pc() - pc_jump_to_tfc)
    r_gen = f.slot_of_local_var('(for gen)')
    f.emit('t_for_call', r_gen, len(stat['names']))
    f.emit('t_for_loop', r_gen + 2, pc_jump_to_tfc - f.pc() - 1)
    f.exit_scope()


def cg_local_var_stat(f, stat):
    exps = stat['exps']
    names = stat['names']
    n_exps = len(exps)
    n_names = len(names)
    old_regs = f.used_regs
    if n_exps == n_names:
        for exp in exps:
            r = f.alloc_reg()
            cg_exp(f, exp, r, 1)
    elif n_exps > n_names:
        for i in range(n_exps):
            a = f.alloc_reg()
            if i == n_exps - 1 and is_vararg_or_call(exps[i]):
                cg_exp(f, exps[i], a, 0)
            else:
                cg_exp(f, exps[i], a, 1)
    else:
        multi_ret = False
        for i in range(n_exps):
            a = f.alloc_reg()
            if i == n_exps - 1 and is_vararg_or_call(exps[i]):
                multi_ret = True
                n = n_names - n_exps + 1
                cg_exp(f, exps[i], a, n)
                f.alloc_regs(n - 1)
            else:
                cg_exp(f, exps[i], a, 1)
        if not multi_ret:
            n = n_names - n_exps
            a = f.alloc_regs(n)
            f.emit('load_nil', a, n - 1)
    f.used_regs = old_regs
    for name in stat['names']:
        f.add_local_var(name)


def cg_assign_stat(f, stat):
    n_exps = len(stat['exps'])
    n_vars = len(stat['vars'])
    old_regs = f.used_regs
    table_regs = [-1] * n_vars
    k_regs = [-1] * n_vars
    v_regs = [-1] * n_vars
    for i in range(n_vars):
        var = stat['vars'][i]
        if type(var) is dict and var.get('op', None) is 'access':
            table_regs[i] = f.alloc_reg()
            cg_exp(f, var['1'], table_regs[i], 1)
            k_regs[i] = f.alloc_reg()
            cg_exp(f, var['2'], k_regs[i], 1)
    for i in range(n_vars):
        v_regs[i] = f.used_regs + i

    if n_exps >= n_vars:
        for i in range(n_exps):
            exp = stat['exps'][i]
            a = f.alloc_reg()
            if i >= n_vars and i == n_exps - 1 and is_vararg_or_call(exp):
                cg_exp(f, exp, a, 0)
            else:
                cg_exp(f, exp, a, 1)
    else:
        multi_ret = False
        for i in range(n_exps):
            exp = stat['exps'][i]
            a = f.alloc_reg()
            if i == n_exps - 1 and is_vararg_or_call(exp):
                multi_ret = True
                n = n_vars - n_exps + 1
                cg_exp(f, exp, a, n)
                f.alloc_reg(n - 1)
            else:
                cg_exp(f, exp, a, 1)
        if not multi_ret:
            n = n_vars - n_exps
            a = f.alloc_regs(n)
            f.emit('load_nil', a, n - 1)

    for i in range(n_vars):
        var = stat['vars'][i]
        if type(var) is str:
            a = f.slot_of_local_var(var)
            if a >= 0:
                f.emit('move', a, v_regs[i])
            else:
                b = f.index_of_up_value(var)
                if b >= 0:
                    f.emit('set_up_val', v_regs[i], b)
                else:
                    a = f.index_of_up_value('_ENV')
                    b = 0x100 + f.index_of_constant(var)
                    f.emit('set_tab_up', a, b, v_regs[i])
        else:
            f.emit('set_table', table_regs[i], k_regs[i], v_regs[i])

    f.used_regs = old_regs


def cg_exp(f, exp, r, n):
    if type(exp) is str:
        cg_name(f, exp, r)
        return
    op = exp.get('op', exp.get('exp_type', None))
    if op == TOKEN.NIL:
        f.emit('load_nil', r, n - 1)
    elif op == TOKEN.FALSE:
        f.emit('load_bool', r, 0, 0)
    elif op == TOKEN.TRUE:
        f.emit('load_bool', r, 1, 0)
    elif op == TOKEN.NUMBER or op == TOKEN.STRING:
        f.emit('load_k', r, exp['content'])
    elif op == 'parenthesis':
        cg_exp(f, exp['1'], r, 1)
    elif op == TOKEN.VARARG:
        assert f.is_vararg
        f.emit('vararg', r, n)
    elif op == 'def':
        cg_func_def_exp(f, exp, r)
    elif op == 'table':
        cg_table_exp(f, exp, r)
    elif op == 'call':
        cg_func_call_exp(f, exp, r, n)
    elif op == 'access':
        cg_table_access_exp(f, exp, r)
    elif op == TOKEN.OP_CONCAT:
        cg_concat_exp(f, exp, r)
    elif '2' in exp:
        cg_2op_exp(f, exp, r)
    elif '1' in exp:
        cg_1op_exp(f, exp, r)
    else:
        print('not support op', op)


def new_func_info(parent, fd):
    info = FuncInfo()
    info.breaks.append([])
    info.parent = parent
    info.is_vararg = fd['params']['var']
    info.param_num = len(fd['params']['params'])
    return info


def cg_func_def_exp(f, exp, a):
    sub = new_func_info(f, exp)
    f.sub_funcs.append(sub)
    for name in exp['params']['params']:
        sub.add_local_var(name)
    cg_block(sub, exp['block'])
    sub.exit_scope()
    sub.emit('return', 0, 0)
    bx = len(f.sub_funcs) - 1
    f.emit('closure', a, bx)


def cg_table_exp(f, exp, a):

    n_arr = 0
    for k in exp['keys']:
        if k is None:
            n_arr += 1
    n_exp = len(exp['keys'])
    multi_ret = n_exp > 0 and is_vararg_or_call(exp['values'][-1])
    f.emit('new_table', a, n_arr, n_exp - n_arr)
    idx = 0

    for i in range(n_exp):
        k = exp['keys'][i]
        v = exp['values'][i]
        if k is None:
            idx += 1
            tmp = f.alloc_reg()
            if i == n_exp - 1 and multi_ret:
                cg_exp(f, v, tmp, -1)
            else:
                cg_exp(f, v, tmp, 1)
            if idx % FIELDS_PER_FLUSH == 0 or idx == n_arr:
                n = idx % FIELDS_PER_FLUSH
                if n == 0:
                    n = FIELDS_PER_FLUSH
                c = (idx - 1) // FIELDS_PER_FLUSH + 1
                f.free_regs(n)
                if i == n_exp - 1 and multi_ret:
                    f.emit('set_list', a, 0, c)
                else:
                    f.emit('set_list', a, n, c)

        else:
            b = f.alloc_reg()
            cg_exp(f, k, b, 1)
            c = f.alloc_reg()
            cg_exp(f, v, c, 1)
            f.free_regs(2)
            f.emit('set_table', a, b, c)


def cg_1op_exp(f, exp, a):
    b = f.alloc_reg()
    cg_exp(f, exp['1'], b, 1)
    f.emit(exp['op'], a, b)
    f.free_reg()


def cg_2op_exp(f, exp, a):
    if exp['op'] in [TOKEN.OP_AND, TOKEN.OP_OR]:
        b = f.alloc_reg()
        cg_exp(f, exp['1'], b, 1)
        f.free_reg()
        if exp['op'] == TOKEN.OP_AND:
            f.emit('test_set', a, b, 0)
        else:
            f.emit('test_set', a, b, 1)
        pc_jump = f.emit('jump', 0, 0)
        b = f.alloc_reg()
        cg_exp(f, exp['2'], b, 1)
        f.free_reg()
        f.emit('move', a, b)
        f.fix_b(pc_jump, f.pc() - pc_jump)
    else:
        b = f.alloc_reg()
        cg_exp(f, exp['1'], b, 1)
        c = f.alloc_reg()
        cg_exp(f, exp['2'], c, 1)
        f.emit(exp['op'], a, b, c)
        f.free_regs(2)


def cg_concat_exp(f, exp, a):
    for sub in exp['1']:
        r = f.alloc_reg()
        cg_exp(f, sub, r, 1)
    c = f.used_regs - 1
    b = c - len(exp['1']) + 1
    f.free_regs(c - b + 1)
    f.emit(TOKEN.OP_CONCAT, a, b, c)


def cg_name(f, name, a):
    r = f.slot_of_local_var(name)
    if r >= 0:
        f.emit('move', a, r)
    else:
        idx = f.index_of_up_value(name)
        if idx >= 0:
            f.emit('get_up_val', a, idx)
        else:
            cg_table_access_exp(f, {'op': 'access', '1': '_ENV',
                                    '2': {'exp_type': TOKEN.STRING, 'content': name, 'line': -1}}, a)


def cg_table_access_exp(f, exp, a):
    b = f.alloc_reg()
    cg_exp(f, exp['1'], b, 1)
    c = f.alloc_reg()
    cg_exp(f, exp['2'], c, 1)
    f.emit('get_table', a, b, c)
    f.free_regs(2)


def cg_func_call_exp(f, exp, a, n):
    n_args = len(exp['args'])
    last_vararg_or_call = False
    cg_exp(f, exp['exp'], a, 1)

    if exp['name'] is not None:
        c = 0x100 + f.index_of_constant(exp['name'])
        f.emit('self', a, a, c)

    for i in range(n_args):
        tmp = f.alloc_reg()
        arg = exp['args'][i]
        if i == n_args - 1 and is_vararg_or_call(arg):
            last_vararg_or_call = True
            cg_exp(f, arg, tmp, -1)
        else:
            cg_exp(f, arg, tmp, 1)

    f.free_regs(n_args)
    if exp['name'] is not None:
        n_args += 1
    if last_vararg_or_call:
        n_args = -1

    f.emit('call', a, n_args, n)


def intermediate(code):
    parser = Parser(code)
    block = parser.parse()
    # print(block)
    fd = {'params': {'var': True, 'params': []}, 'block': block}
    info = new_func_info(None, fd)
    info.add_local_var('_ENV')
    cg_func_def_exp(info, fd, 0)
    # print(info.sub_funcs[0].ins)
    return info

