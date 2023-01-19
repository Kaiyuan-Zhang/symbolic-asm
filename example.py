import z3
from asm_state import *
from sym_exec import *


if __name__ == '__main__':
    prog = [
        MovInst('rax', 'rbp_8'),
        MovInst(z3.BitVecVal(0, 64), 'rbp_c'),
        JmpInst(7),

        MovInst('rbp_8', 'rax'),
        LoadInst('rax', 0, 'rax'),
        ArithInst('add', 'rax', 'rbp_c'),
        MovInst('rbp_8', 'rax'),
        LoadInst('rax', 8, 'rax', 'mem'),
        MovInst('rax', 'rbp_8'),

        CmpJmpInst('ne', 'rbp_8', 0, -6),
        MovInst('rbp_c', 'rax'),
    ]

    memory = UfMemory('mem', z3.BitVecSort(64), z3.BitVecSort(64))
    # memory = ArrayMemory('mem', z3.BitVecSort(64), z3.BitVecSort(64))
    init_state = AsmState()
    init_state.add_memory('mem', memory)
    init_state.regs['rax'] = Pointer('mem', z3.BitVec('init_rax', 64))

    loop_cnt = 100
    ending_states = symbolic_execute(prog, init_state, 0, lambda s: len(s.pre_cond) <= loop_cnt)

    state_of_interest = list(filter(lambda s: len(s.pre_cond) == loop_cnt, ending_states))
    print(state_of_interest)
    for i, s in enumerate(state_of_interest):
        print(f"state {i} instruction cnt == {len(s.pc_history)}")
        z3.solve(*s.pre_cond, s.regs['rax'] == loop_cnt)
