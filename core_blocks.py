from myhdl import block, always_seq, intbv
from myhdl._Signal import _Signal
from utils import *


@block
def fetching(program: list[intbv], clk: _Signal, reset: _Signal, pc: _Signal, 
                            icode: _Signal, ifun: _Signal, rA: _Signal, rB: _Signal, 
                            valC: _Signal, valP: _Signal, instr_valid: _Signal, \
                            imem_error: _Signal, enable: _Signal):
    @always_seq(clk.posedge, reset=reset)
    def fetch():
        if not enable.val:
            return
        
        # Read current PC value
        pc_val = int(pc)
        if pc_val < 0 or pc_val >= len(program):
            instr_valid.next = 0
            imem_error.next = 1
            return
        
        # Get instruction data
        instr = intbv(program[pc_val])[8:]
    
        # Calculate all values first
        icode_val = instr[8:4]
        ifun_val = instr[4:]

        if icode_val < 0 or icode_val > 0xB:
            instr_valid.next = 0
            imem_error.next = 0
            return

        icode.next = icode_val
        ifun.next = ifun_val
        
        # Determine instruction type using named constants
        is_simple = icode_val in [IHALT, INOP, IJXX, ICALL, IRET]
        
        if is_simple:
            rA.next = RNONE
            rB.next = RNONE
            
            if icode_val in [IHALT, INOP, IRET]:
                valC.next = intbv(0)[64:]
                valP.next = pc_val + 1
            else:
                # Calculate immediate value for JXX and CALL
                immediate_val = read_8byte_number(program, pc_val + 1)
                valC.next = intbv(immediate_val)[64:]
                valP.next = pc_val + 9
        else:
            # Handle register instructions
            regs = intbv(program[pc_val + 1])[8:]
            rA.next = regs[8:4]
            rB.next = regs[4:]
            
            # Use named constants for instruction types
            if icode_val in [IIRMOVQ, IRMMOVQ, IMRMOVQ]:
                immediate_val = read_8byte_number(program, pc_val + 2)
                valC.next = immediate_val
                valP.next = pc_val + 10
            else:
                valC.next = intbv(0)[64:]
                valP.next = pc_val + 2

    return fetch


@block
def decoding(clk: _Signal, reset: _Signal,  icode: _Signal, \
            rA: _Signal, rB: _Signal,  valA: _Signal, valB: _Signal, \
                    srcA: _Signal, srcB: _Signal, Regs: list[_Signal], enable: _Signal):
    @always_seq(clk.posedge, reset=reset)
    def decode():
        if not enable.val:
            return
        
        if icode.val in [IRRMOVQ, IRMMOVQ, IOPQ, IPUSHQ]:
            srcA.next = int(rA)
        elif icode.val in [IPOPQ, IRET]:
            srcA.next = RRSP
        else:
            srcA.next = RNONE
        
        if icode.val in [IMRMOVQ, IRMMOVQ, IOPQ, ICMOVXX]:
            srcB.next = int(rB)
        elif icode.val in [IPUSHQ, ICALL, IRET, IPOPQ]:
            srcB.next = RRSP
        else:
            srcB.next = RNONE

        if srcA.next != RNONE:
            valA.next = Regs[srcA.next].val
        if srcB.next != RNONE:
            valB.next = Regs[srcB.next].val
        
        
    return decode



@block
def execution(clk: _Signal, reset: _Signal,  icode: _Signal, ifun: _Signal, \
            valA: _Signal, valB: _Signal, valC: _Signal, \
                valE: _Signal, Cnd: _Signal, CC: _Signal, \
                dstE: _Signal, dstM: _Signal, rA: _Signal, rB: _Signal, enable: _Signal):
    @always_seq(clk.posedge, reset=reset)
    def execute():
        if not enable.val:
            return

        aluA = intbv(0)[64:]
        aluB = intbv(0)[64:]
        if icode.val in [IRRMOVQ, IOPQ]:
            aluA = valA.val
        if icode.val in [IIRMOVQ, IRMMOVQ, IMRMOVQ]:
            aluA = valC.val
        if icode.val in [ICALL, IPUSHQ]:
            aluA = -8
        if icode.val in [IRET, IPOPQ]:
            aluA = 8

        if icode.val in [IMRMOVQ, IOPQ, IRMMOVQ, IPUSHQ, IPOPQ, ICALL, IRET]:
            aluB = valB.val
       

        #CC = intvbv(0)[3:] and CC[0] -> ZF, CC[1] -> SF, CC[2] -> OF
        if icode.val == IOPQ:
            if ifun.val == 0:
                valE.next = valA + valB
            elif ifun.val == 1:
                valE.next = valA - valB
            elif ifun.val == 2:
                valE.next = valA & valB
            elif ifun.val == 3:
                valE.next = valA ^ valB
            CC.next = intbv(0)[3:]
            if valE.next == 0:
                CC.next[0] = 1
            if valE.next < 0:
                CC.next[1] = 1
            if is_overflow(valA.val, valB.val, valE.val, ifun.val):
                CC.next[2] = 1
        else:
            valE.next = aluA + aluB
            
        if icode.val == IJXX or icode.val == ICMOVXX:
            Cnd.next = Cond(CC.val, ifun.val)

        #dstE
        if icode.val == ICMOVXX and ifun.val != 0:
            if Cnd.val:
                dstE.next = rB.val
            else:
                dstE.next = RNONE
        elif icode.val in [IOPQ, IRRMOVQ, IIRMOVQ, IMRMOVQ]:
            dstE.next = rB.val
        elif icode.val in [IPUSHQ, ICALL, IPOPQ, IRET]:
            dstE.next = RRSP
        else:
            dstE.next = RNONE
        
        #dstM
        if icode.val in [IPOPQ, IMRMOVQ]:
            dstM.next = rA.val
        else:
            dstM.next = RNONE
        
    return execute


@block
def memory_access(clk: _Signal, reset: _Signal, icode: _Signal,
                  valE: _Signal, valA: _Signal, valP: _Signal, valM: _Signal,
                  imem_error: _Signal, dmem_error: _Signal,
                  instr_valid: _Signal, Stat: _Signal, mem: list[intbv], enable: _Signal):
    @always_seq(clk.posedge, reset=reset)
    def access():
        if not enable.val:
            return
        
        mem_addr = intbv(0)[64:]
        mem_data = intbv(0)[64:]
        mem_read = 0
        mem_write = 0

        if icode.val in [IRMMOVQ, IPUSHQ, ICALL, IMRMOVQ]:
            mem_addr = valE.val
        if icode.val in [IPOPQ, IRET]:
            mem_addr = valA.val

        mem_read = icode.val in [IMRMOVQ, IPOPQ, IRET]
        mem_write = icode.val in [IRMMOVQ, IPUSHQ, ICALL]
        
        if icode.val in [ICALL]:
            mem_data = valP.val
        if icode.val in [IPUSHQ, IRMMOVQ]:
            mem_data = valA.val

        if mem_read or mem_write:
            dmem_error.next = mem_addr >= len(mem)

        if mem_read and not dmem_error.next:
            valM.next = read_8byte_number_sig(mem, mem_addr)
        if mem_write and not dmem_error.next:
            write_8byte_number_sig(mem, mem_addr, mem_data)

        if imem_error.val:
            Stat.next = SADR  # Address error
        elif not instr_valid.val:
            Stat.next = SINS  # Invalid instruction
        elif dmem_error.val:
            Stat.next = SADR  # Data memory error
        elif icode.val == IHALT:
            Stat.next = SHLT  # Halt
        else:
            Stat.next = SAOK  # OK - normal operation
        
    return access

@block
def writing_back(clk: _Signal, reset: _Signal, valM: _Signal, valE: _Signal, \
    dstE: _Signal, dstM: _Signal, Regs: list[_Signal], enable: _Signal, icode: _Signal):

    @always_seq(clk.posedge, reset=reset)
    def write_back():   
        if not enable.val:
            return
        
        if dstE.val != RNONE:
            Regs[int(dstE.val)].next = valE.val
        if dstM.val != RNONE:
            Regs[int(dstM.val)].next = valM.val
    
    return write_back

@block
def PC_update(clk: _Signal, reset: _Signal, valP: _Signal, valM: _Signal, \
    Cnd: _Signal, Stat: _Signal, pc: _Signal, icode: _Signal,\
         valC: _Signal, enable: _Signal):
    @always_seq(clk.posedge, reset=reset)
    def update():
        if not enable.val:
            return
        
        if icode.val == ICALL:
            pc.next = valC.val
        elif icode.val == IRET:
            pc.next = valM.val
        elif icode.val == IJXX and Cnd.val:
            pc.next = valC.val
        else:
            pc.next = valP.val
       
    return update