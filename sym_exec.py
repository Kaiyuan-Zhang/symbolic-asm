import z3
from asm_state import *


class AsmInst(object):
    def get_val(self, v, state):
        if isinstance(v, str):
            return state.regs[v]
        else:
            return v

    def exec(self, state):
        raise NotImplementedError()


class MovInst(AsmInst):
    def __init__(self, src, dst):
        self.src = src
        self.dst = dst

    def exec(self, state):
        if isinstance(self.src, str):
            state.regs[self.dst] = state.regs[self.src]
        else:
            state.regs[self.dst] = self.src
        state.pc_inc(1)
        return [state]

    def __repr__(self):
        return f"MovInst({self.src}, {self.dst})"


class ArithInst(AsmInst):
    def __init__(self, op, src, dst):
        self.op = op
        self.src = src
        self.dst = dst

    def exec(self, state):
        arith_func = {
            'add' : lambda x, y: x + y,
        }

        op = arith_func[self.op]
        dst_val = state.regs[self.dst]
        if isinstance(self.src, str):
            state.regs[self.dst] = op(dst_val, state.regs[self.src])
        else:
            state.regs[self.dst] = op(dst_val, self.src)
        state.pc_inc(1)
        return [state]

    def __repr__(self):
        return f"ArithInst({self.op}, {self.src}, {self.dst})"


class LoadInst(AsmInst):
    def __init__(self, ptr_reg, offset, dst, memory_name=None):
        self.ptr_reg = ptr_reg
        self.offset = offset
        self.dst = dst
        self.mem_name = memory_name

    def exec(self, state):
        ptr = state.regs[self.ptr_reg]
        ptr.offset += self.offset
        val = ptr.load(state)
        if self.mem_name is None:
            state.regs[self.dst] = val
        else:
            state.regs[self.dst] = Pointer(self.mem_name, val)
        state.pc_inc(1)
        return [state]

    def __repr__(self):
        extra_str = f", {self.mem_name}" if self.mem_name is not None else ""
        return f"LoadInst({self.ptr_reg}, {self.offset}, {self.dst}{extra_str})"


class StoreInst(AsmInst):
    def __init__(self, ptr_reg, val):
        self.ptr_reg = ptr_reg
        self.immediate_val = False
        if isinstance(val, str):
            self.val_reg = val
        else:
            self.val = val
            self.immediate_val = True

    def exec(self, state):
        ptr = state.regs[self.ptr_reg]
        val = None
        if self.immediate_val:
            val = self.val
        else:
            val = state.regs[self.val_reg]
        ptr.store(state, val)
        state.pc_inc(1)
        return [state]

    def __repr__(self):
        return f"StoreInst({self.ptr_reg}, {self.val})"


class JmpInst(AsmInst):
    def __init__(self, pc_offset):
        self.pc_offset = pc_offset

    def exec(self, state):
        state.pc_inc(self.pc_offset)
        return [state]

    def __repr__(self):
        return f"JmpInst({self.pc_offset})"


class CmpJmpInst(AsmInst):
    def __init__(self, cond, arg1, arg2, pc_offset):
        self.pc_offset = pc_offset
        self.cond = cond
        self.arg1 = arg1
        self.arg2 = arg2

    def exec(self, state):
        cond_funcs = { 'ne' : lambda x, y: x != y }
        arg1 = self.get_val(self.arg1, state)
        arg2 = self.get_val(self.arg2, state)
        ns = state.symexec_state_copy()
        state.pc_inc(1)
        ns.pc_inc(self.pc_offset)

        if isinstance(arg1, Pointer) or isinstance(arg2, Pointer):
            assert(self.cond in ['eq', 'ne'])
            if isinstance(arg1, Pointer):
                ptr = arg1
                other = arg2
            else:
                ptr = arg2
                other = arg1
            assert(not isinstance(other, Pointer) or other.memory_name == ptr.memory_name)
            if isinstance(other, Pointer):
                assert(other.memory_name == ptr.memory_name)
            else:
                assert(other == 0)

            if isinstance(arg1, Pointer):
                arg1 = arg1.offset
            if isinstance(arg2, Pointer):
                arg2 = arg2.offset

        cond = cond_funcs[self.cond](arg1, arg2)
        state.add_precond(z3.Not(cond))
        ns.add_precond(cond)

        return [ns, state]

    def __repr__(self):
        return f"CmpJmpInst({self.cond}, {self.arg1}, {self.arg2}, {self.pc_offset})"


def symbolic_execute(prog, init_state, start_pc, pre_cond_filter=None):
    init_state_copy = init_state.symexec_state_copy()
    init_state_copy.pc = start_pc
    ending_states = []

    state_stack = [init_state_copy]

    while len(state_stack) > 0:
        state = state_stack.pop()
        num_pre_cond = len(state.pre_cond)
        if state.pc < 0 or state.pc >= len(prog):
            state.pc = None
            ending_states.append(state)
            continue
        print(f"running {state.pc} : {prog[state.pc]}")
        new_states = prog[state.pc].exec(state)

        to_add = []
        if pre_cond_filter is not None:
            for s in new_states:
                n_pre_cond = len(s.pre_cond)
                if n_pre_cond == num_pre_cond or pre_cond_filter(s):
                    to_add.append(s)
        else:
            to_add = new_states
        state_stack = state_stack + to_add[::-1]
    return ending_states
