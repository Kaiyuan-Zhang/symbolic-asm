import z3


def gen_name(base):
    name_idx_map_name = 'name_idx_map'
    name_map = None
    if not hasattr(gen_name, name_idx_map_name):
        setattr(gen_name, name_idx_map_name, {})
    name_map = getattr(gen_name, name_idx_map_name)
    if base not in name_map:
        name_map[base] = 0
    idx = name_map[base]
    name_map[base] = idx + 1
    return f"{base}_{idx}"


class Memory(object):
    def __init__(self, name):
        self.name = name

    def load(self, address):
        raise NotImplementedError()

    def store(self, address, value):
        raise NotImplementedError()

    def duplicate_mem(self):
        raise NotImplementedError()


class AsmState(object):
    def __init__(self):
        self.regs = {}
        self.memories = {}
        self.pc = 0
        self.pre_cond = []
        self.pc_history = []

    def add_precond(self, precond):
        self.pre_cond.append(precond)

    def get_precond(self):
        if len(self.pre_cond) == 0:
            return True
        else:
            z3.And(*self.pre_cond)

    def add_memory(self, memory_name, memory_obj):
        self.memories[memory_name] = memory_obj

    def get_memory(self, memory_name):
        return self.memories[memory_name]

    def pc_inc(self, offset):
        self.pc_history.append(self.pc)
        self.pc = self.pc + offset

    def symexec_state_copy(self):
        ns = AsmState()
        ns.pc = self.pc
        ns.pc_history = self.pc_history[:]
        for k, v in self.regs.items():
            if 'reg_val_copy' in dir(v):
                ns.regs[k] = v.reg_val_copy()
            else:
                ns.regs[k] = v
        for k, v in self.memories.items():
            ns.memories[k] = v.duplicate_mem()
        ns.pre_cond = self.pre_cond[:]
        return ns


class UfMemory(Memory):
    def __init__(self, name, addr_sort, value_sort):
        super().__init__(name)
        self.uf = z3.Function(f"{name}_uf", addr_sort, value_sort)
        self.addr_sort = addr_sort
        self.value_sort = value_sort
        self.updates = []

    def load(self, address):
        addr_casted = self.addr_sort.cast(address)
        ret_val = self.uf(address)
        for addr, val in self.updates[::-1]:
            ret_val = z3.If(addr == addr_casted, val, ret_val)
        return ret_val

    def store(self, address, value):
        self.updates.append((self.addr_sort.cast(address), self.value_sort.cast(value)))

    def duplicate_mem(self):
        nm = UfMemory('tmp', self.addr_sort, self.value_sort)
        nm.name = self.name
        nm.uf = self.uf
        nm.updates = self.updates[:]
        return nm


class ArrayMemory(Memory):
    def __init__(self, name, addr_sort, value_sort):
        super().__init__(name)
        self.arr = z3.Array(f"{name}_arr", addr_sort, value_sort)
        self.addr_sort = addr_sort
        self.value_sort = value_sort

    def load(self, address):
        return self.arr[address]

    def store(self, address, value):
        self.arr = z3.Store(self.arr, address, value)

    def duplicate_mem(self):
        nm = ArrayMemory('tmp', self.addr_sort, self.value_sort)
        nm.name = self.name
        nm.arr = self.arr
        return nm


class Pointer(object):
    def __init__(self, memory_name, offset):
        self.memory_name = memory_name
        self.offset = offset

    def load(self, state):
        mem = state.get_memory(self.memory_name)
        return mem.load(self.offset)

    def store(self, state, value):
        mem = state.get_memory(self.memory_name)
        mem.store(self.offset, value)

    def reg_val_copy(self):
        return Pointer(self.memory_name, self.offset)
