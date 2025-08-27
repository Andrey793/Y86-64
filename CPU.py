from core_blocks import *
from myhdl._Signal import _Signal, Signal
from enum import Enum
from myhdl import always, StopSimulation, delay


MEM_SIZE = 1024


@block
def clock_generator(clk, period=10):
    """Generate clock signal for simulation"""
    period = delay(period // 2)
    @always(period)
    def gen():
        clk.next = not clk
    return gen

@block
def reset_generator(reset, clk, reset_cycles=3):
    """Generate reset signal for simulation"""
    counter = Signal(intbv(reset_cycles, min=0, max=reset_cycles + 1))
    @always_seq(clk.posedge, reset=None)
    def gen():
        if counter > 0:
            reset.next = 1
            counter.next = counter - 1
        else:
            reset.next = 0
    return gen

@block 
def CPU(program: list[intbv], clk: _Signal, reset: _Signal, main: int):
    pc = Signal(intbv(main)[64:])
    icode = Signal(intbv(0)[4:])
    ifun = Signal(intbv(0)[4:])
    rA = Signal(intbv(0)[4:])
    rB = Signal(intbv(0)[4:])
    valA = Signal(intbv(0)[64:].signed())
    valB = Signal(intbv(0)[64:].signed())
    valC = Signal(intbv(0)[64:].signed())
    valE = Signal(intbv(0)[64:].signed())
    valM = Signal(intbv(0)[64:])
    valP = Signal(intbv(0)[64:])
    srcA = Signal(intbv(0)[4:])
    srcB = Signal(intbv(0)[4:])
    Regs = [Signal(intbv(0)[64:].signed()) for _ in range(15)]
    #rsp
    Regs[4] = Signal(intbv(MEM_SIZE - 1)[64:])
    old_Regs = [Signal(Regs[i].val) for i in range(15)]

    dstE = Signal(intbv(0)[4:])
    dstM = Signal(intbv(0)[4:])
    Cnd = Signal(intbv(0)[1:])
    Stat = Signal(intbv(0)[3:])
    CC = Signal(intbv(0)[3:])
    old_CC = Signal(intbv(0)[3:])
    imem_error = Signal(intbv(0)[1:])
    dmem_error = Signal(intbv(0)[1:])
    instr_valid = Signal(intbv(1)[1:])
    mem = [Signal(intbv(0)[64:].signed()) for _ in range(MEM_SIZE)]
    old_mem = [Signal(intbv(0)[64:].signed()) for _ in range(MEM_SIZE)]


    # Stage enables (only one active at a time)
    en_fetch = Signal(bool(0))
    en_decode = Signal(bool(0))
    en_execute = Signal(bool(0))
    en_memory = Signal(bool(0))
    en_writeback = Signal(bool(0))
    en_PC_update = Signal(bool(0))

    fetching_inst = fetching(program, clk, reset, pc, icode, ifun, rA, rB, valC, valP, instr_valid, imem_error, en_fetch)
    decoding_inst = decoding(clk, reset, icode, rA, rB, valA, valB, srcA, srcB, Regs, en_decode)
    execution_inst = execution(clk, reset, icode, ifun, valA, valB, valC, valE, Cnd, CC, dstE, dstM, rA, rB, en_execute)
    memory_access_inst = memory_access(clk, reset, icode, valE, valA, valP, valM, imem_error, dmem_error, instr_valid, Stat, mem, en_memory)
    writing_back_inst = writing_back(clk, reset, valM, valE, dstE, dstM, Regs, en_writeback, icode)
    PC_update_inst = PC_update(clk, reset, valP, valM, Cnd, Stat, pc, icode, valC, en_PC_update)

    class t_state(Enum):
        F = 1
        D = 2
        E = 3
        M = 4
        W = 5
        PC = 6
        HALT = 7
    state = Signal(t_state.F)

    @always_seq(clk.posedge, reset=reset)
    def controller():
        check_diff(old_Regs, Regs, old_mem, mem, old_CC, CC)
        if state.val == t_state.HALT:
            raise StopSimulation(f"Executions was stopped at time {myhdl.now()}. State:{bin(Stat.val)}")

        for i in range(15):
            old_Regs[i].next = Regs[i].val
        for i in range(MEM_SIZE):
            old_mem[i].next = mem[i].val
        old_CC.next = CC.val
        # Set enables based on current state
        en_fetch.next = (state.val == t_state.F)
        en_decode.next = (state.val == t_state.D)
        en_execute.next = (state.val == t_state.E)
        en_memory.next = (state.val == t_state.M)
        en_writeback.next = (state.val == t_state.W)
        en_PC_update.next = (state.val == t_state.PC)
        
        # Advance to next state
        if state.val == t_state.F:
            state.next = t_state.D
        elif state.val == t_state.D:
            state.next = t_state.E
        elif state.val == t_state.E:
            state.next = t_state.M
        elif state.val == t_state.M:
            state.next = t_state.W
        elif state.val == t_state.W:
            state.next = t_state.PC
        elif state.val == t_state.PC:
            if Stat.val in [SHLT, SADR, SINS]:
                state.next = t_state.HALT
            else:
                state.next = t_state.F
                
    return fetching_inst, decoding_inst, execution_inst, memory_access_inst, writing_back_inst, PC_update_inst, controller

