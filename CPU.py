from core_blocks import *
from myhdl._Signal import _Signal, Signal
from myhdl import always, StopSimulation, delay
from utils import check_diff, SAOK


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
    # Pipeline signals
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
    dstE = Signal(intbv(0)[4:])
    dstM = Signal(intbv(0)[4:])
    Cnd = Signal(intbv(0)[1:])
    Stat = Signal(intbv(0)[3:])
    CC = Signal(intbv(0)[3:])
    imem_error = Signal(intbv(0)[1:])
    dmem_error = Signal(intbv(0)[1:])
    instr_valid = Signal(intbv(1)[1:])
    
    # Register file
    Regs = [Signal(intbv(0)[64:].signed()) for _ in range(15)]
    #rsp
    Regs[4] = Signal(intbv(MEM_SIZE - 1)[64:])
    old_Regs = [Signal(Regs[i].val) for i in range(15)]

    # Memory
    mem = [Signal(intbv(0)[64:].signed()) for _ in range(MEM_SIZE)]
    old_mem = [Signal(mem[i].val) for i in range(MEM_SIZE)]
    old_CC = Signal(CC.val)

    # Create the pipeline cycle block
    pipeline = pipeline_cycle(program, clk, reset, 
                             pc, icode, ifun, rA, rB, valC, valP, instr_valid, imem_error,
                             srcA, srcB, valA, valB, valE, Cnd, CC, dstE, dstM,
                             valM, dmem_error, Stat, Regs, mem)

    @always_seq(clk.posedge, reset=reset)
    def controller():
        # Check for differences and update old values
        check_diff(old_Regs, Regs, old_mem, mem, old_CC, CC)
        
        # Check for halt condition
        if Stat.val != SAOK:
            raise StopSimulation(f"Execution was stopped at time {myhdl.now()}. State:{bin(Stat.val)}")

        # Update old values for next cycle
        for i in range(15):
            old_Regs[i].next = Regs[i].val
        for i in range(MEM_SIZE):
            old_mem[i].next = mem[i].val
        old_CC.next = CC.val
                
    return pipeline, controller

