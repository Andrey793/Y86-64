from core_blocks import *
from myhdl._Signal import _Signal, Signal
from myhdl import always, StopSimulation, delay
from cpu_utils import CPU_state
#from utils import check_diff_n_update
from utils import MEM_SIZE


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
    cpu_state = CPU_state(main)
    old_CC = Signal(cpu_state.CC.val)
    old_Registers = [Signal(cpu_state.Registers[i].val) for i in range(15)]
    old_Mem = [Signal(cpu_state.Mem[i].val) for i in range(MEM_SIZE)]
    #Registers and memory to track changes
    last_dstE = Signal(0)
    last_dstM = Signal(0)
    last_valE = Signal(0)
    last_valA = Signal(0)

    fetching_inst = fetching(program, cpu_state, clk, reset)
    decoding_inst = decoding(cpu_state, clk, reset)
    execution_inst = execution(cpu_state, clk, reset)
    memory_access_inst = memory_access(cpu_state, clk, reset, last_valE, last_valA)
    writing_back_inst = writing_back(cpu_state, clk, reset, last_dstE, last_dstM)

   

    @always_seq(clk.posedge, reset=reset)
    def controller():
        check_diff_n_update(old_Registers, cpu_state.Registers, old_Mem, cpu_state.Mem, \
            old_CC, cpu_state.CC, last_dstE.val, last_dstM.val, \
            last_valE.val, last_valA.val)

        #if cpu_state.F_predPC.val == 0:
            #cpu_state.F_predPC.next = intbv(main)[64:]
        if cpu_state.Stat.val != SAOK:
            raise StopSimulation(f"Executions was stopped at time {myhdl.now()}. State:{bin(cpu_state.W_stat.val)}")
   
    return fetching_inst, decoding_inst, execution_inst, memory_access_inst, writing_back_inst, controller

