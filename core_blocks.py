from myhdl import block, always_seq, intbv, always_comb, always
from myhdl._Signal import _Signal
from utils import *
from cpu_utils import CPU_state


@block 
def fetching(program: list[intbv], cpu_state: CPU_state, clk: _Signal, reset: _Signal):
    @always_seq(clk.posedge, reset)
    def fetch():
        if (cpu_state.E_srcA.val != RNONE and cpu_state.E_srcA.val == cpu_state.M_dstM.val) or (cpu_state.E_srcB.val != RNONE and cpu_state.E_srcB.val == cpu_state.M_dstM.val) and cpu_state.bubble.val:
            return
        cpu_state.bubble.next = 1
        instr_valid = 1
        imem_error = 0
        #F_valM is computed in memory access stage. And it is set to valid address only if 
        #icode == RETURN.

        if cpu_state.F_valM.val != 0:
            pc_val = cpu_state.F_valM.val
            cpu_state.CC.next = cpu_state.CC_stack.pop(0)

        #F_valA and F_cnd are computed in execution stage. 
        #and F_cnd is set to 0 only if icode == JXX and then F_valA is set to correct address.
        elif not cpu_state.M_cnd.val:
            pc_val = cpu_state.M_valA.val
            cpu_state.CC.next = cpu_state.CC_stack.pop(0)
        
        else:
            pc_val = cpu_state.F_predPC.val
        
        if pc_val < 0 or pc_val >= len(program):
            imem_error = 1
            #insert bubble. Wait till it change WB state or new PC come from another stage.
            instr = intbv(INOP)[8:]
        else:
        # Get instruction data
            instr = intbv(program[pc_val])[8:]
    
        # Calculate all values first
        icode_val = instr[8:4]
        ifun_val = instr[4:]

        if icode_val < 0 or icode_val > 0xB:
            instr_valid =  0

        cpu_state.D_icode.next = icode_val
        cpu_state.D_ifun.next = ifun_val
        
        is_simple = icode_val in [IHALT, INOP, IJXX, ICALL, IRET]
        
        if is_simple:
            cpu_state.  D_rA.next = RNONE
            cpu_state.D_rB.next = RNONE
            
            if icode_val in [IHALT, INOP, IRET]:
                cpu_state.D_valC.next = intbv(0)[64:]
                cpu_state.D_valP.next = pc_val + 1
            else:
                # Calculate immediate value for JXX and CALL
                immediate_val = read_8byte_number(program, pc_val + 1)
                cpu_state.D_valC.next = intbv(immediate_val)[64:]
                cpu_state.D_valP.next = pc_val + 9
        else:
            # Handle register instructions
            regs = intbv(program[pc_val + 1])[8:]
            cpu_state.D_rA.next = regs[8:4]
            cpu_state.D_rB.next = regs[4:]
            
            # Use named constants for instruction types
            if icode_val in [IIRMOVQ, IRMMOVQ, IMRMOVQ]:
                immediate_val = read_8byte_number(program, pc_val + 2)
                cpu_state.D_valC.next = immediate_val
                cpu_state.D_valP.next = pc_val + 10
            else:
                cpu_state.D_valC.next = intbv(0)[64:]
                cpu_state.D_valP.next = pc_val + 2

        stat = intbv(0)[3:]
        if imem_error or not instr_valid:
            stat[0] = 1
        if icode_val == IHALT:
            stat[1] = 1
        cpu_state.D_stat.next = stat

        #PC prediction. strategy: always jump
        if icode_val == ICALL or icode_val == IJXX:
            cpu_state.CC_stack.append(cpu_state.CC.val)
            cpu_state.call_stack.append(cpu_state.D_valP.next)
            cpu_state.F_predPC.next = cpu_state.D_valC.next
        elif icode_val == IRET:
            cpu_state.F_predPC.next = cpu_state.call_stack.pop()
            cpu_state.predPC_queue.append(cpu_state.F_predPC.next)
        else:
            cpu_state.F_predPC.next = cpu_state.D_valP.next

    return fetch
    
@block
def decoding(cpu_state: CPU_state, clk: _Signal, reset: _Signal):
    @always_seq(clk.posedge, reset)
    def decode():
        if (cpu_state.E_srcA.val != RNONE and cpu_state.E_srcA.val == cpu_state.M_dstM.val) or (cpu_state.E_srcB.val != RNONE and cpu_state.E_srcB.val == cpu_state.M_dstM.val) and cpu_state.bubble.val:
            return
        cpu_state.E_stat.next = cpu_state.D_stat.val
        if cpu_state.D_icode.val in [IRRMOVQ, IRMMOVQ, IOPQ, IPUSHQ]:
            cpu_state.E_srcA.next = cpu_state.D_rA.val
        elif cpu_state.D_icode.val in [IPOPQ, IRET]:
            cpu_state.E_srcA.next = cpu_state.D_rA.val
        else:
            cpu_state.E_srcA.next = RNONE
        
        if cpu_state.D_icode.val in [IMRMOVQ, IIRMOVQ, IOPQ, ICMOVXX]:
            cpu_state.E_srcB.next = int(cpu_state.D_rB)
        elif cpu_state.D_icode.val in [IPUSHQ, ICALL, IRET, IPOPQ]:
            cpu_state.E_srcB.next = RRSP
        else:
            cpu_state.E_srcB.next = RNONE

        if cpu_state.E_srcA.next != RNONE:
            cpu_state.E_valA.next = cpu_state.Registers[cpu_state.E_srcA.next].val
        else:
            cpu_state.E_valA.next = cpu_state.D_valP.val
        if cpu_state.E_srcB.next != RNONE:
            cpu_state.E_valB.next = cpu_state.Registers[cpu_state.E_srcB.next].val

        cpu_state.E_icode.next = cpu_state.D_icode.val
        cpu_state.E_ifun.next = cpu_state.D_ifun.val
        cpu_state.E_valC.next = cpu_state.D_valC.val

        #detect hazard only for wb stage
        if cpu_state.E_srcA.next != RNONE:
            if cpu_state.E_srcA.next == cpu_state.W_dstE.val:
                cpu_state.E_valA.next = cpu_state.W_valE.val
            if cpu_state.E_srcA.next == cpu_state.W_dstM.val:
                cpu_state.E_valA.next = cpu_state.W_valM.val
        if cpu_state.E_srcB.next != RNONE:
            if cpu_state.E_srcB.next == cpu_state.W_dstE.val:
                cpu_state.E_valB.next = cpu_state.W_valE.val
            if cpu_state.E_srcB.next == cpu_state.W_dstM.val:
                cpu_state.E_valB.next = cpu_state.W_valM.val
        
    return decode

@block
def execution(cpu_state: CPU_state, clk: _Signal, reset: _Signal):
    @always_seq(clk.posedge, reset)
    def execute():
        #mem-data hazard
        if (cpu_state.E_srcA.val != RNONE and cpu_state.E_srcA.val == cpu_state.M_dstM.val) or (cpu_state.E_srcB.val != RNONE and cpu_state.E_srcB.val == cpu_state.M_dstM.val) and cpu_state.bubble.val:
            cpu_state.bubble.next = 0
            cpu_state.M_stat.next = intbv(0)[3:]
            cpu_state.M_icode.next = INOP
            cpu_state.M_dstE.next = RNONE
            cpu_state.M_dstM.next = RNONE
            return
        
        e_valA = cpu_state.E_valA.val
        e_valB = cpu_state.E_valB.val
        e_valC = cpu_state.E_valC.val
        #data forwarding
        if cpu_state.E_srcA.val != RNONE:
            if cpu_state.E_srcA.val == cpu_state.M_dstE.val:
                e_valA = cpu_state.M_valE.val
            elif cpu_state.E_srcA.val == cpu_state.W_dstE.val:
                e_valA = cpu_state.W_valE.val
            elif cpu_state.E_srcA.val == cpu_state.W_dstM.val:
                e_valA = cpu_state.W_valM.val
        
        if cpu_state.E_srcB.val != RNONE:
            if cpu_state.E_srcB.val == cpu_state.M_dstE.val:
                e_valB = cpu_state.M_valE.val
            elif cpu_state.E_srcB.val == cpu_state.W_dstE.val:
                e_valB = cpu_state.W_valE.val
            elif cpu_state.E_srcB.val == cpu_state.W_dstM.val:
                e_valB = cpu_state.W_valM.val

        cpu_state.M_stat.next = cpu_state.E_stat.val
        cpu_state.M_cnd.next = 1
        
        aluA = intbv(0)[64:]
        aluB = intbv(0)[64:]
        if cpu_state.E_icode.val in [IRRMOVQ, IOPQ]:
            aluA = e_valA
        if cpu_state.E_icode.val in [IIRMOVQ, IRMMOVQ, IMRMOVQ]:
            aluA = e_valC
        if cpu_state.E_icode.val in [ICALL, IPUSHQ]:
            aluA = -8
        if cpu_state.E_icode.val in [IRET, IPOPQ]:
            aluA = 8

        if cpu_state.E_icode.val in [IMRMOVQ, IOPQ, IRMMOVQ, IPUSHQ, IPOPQ, ICALL, IRET]:
            aluB = e_valB
       

        #CC = intvbv(0)[3:] and CC[0] -> ZF, CC[1] -> SF, CC[2] -> OF
        if cpu_state.E_icode.val == IOPQ:
            if cpu_state.E_ifun.val == 0:
                cpu_state.M_valE.next = aluA + aluB
            elif cpu_state.E_ifun.val == 1:
                cpu_state.M_valE.next = aluA - aluB
            elif cpu_state.E_ifun.val == 2:
                cpu_state.M_valE.next = aluA & aluB
            elif cpu_state.E_ifun.val == 3:
                cpu_state.M_valE.next = aluA ^ aluB
            cpu_state.CC.next = intbv(0)[3:]
            if cpu_state.M_valE.next == 0:
                cpu_state.CC.next[0] = 1
            if cpu_state.M_valE.next < 0:
                cpu_state.CC.next[1] = 1
            if is_overflow(e_valA, e_valB, cpu_state.M_valE.next, cpu_state.E_ifun.val):
                cpu_state.CC.next[2] = 1
        else:
            cpu_state.M_valE.next = aluA + aluB
            
        if cpu_state.E_icode.val == IJXX or cpu_state.E_icode.val == ICMOVXX:
            cpu_state.M_cnd.next = Cond(cpu_state.CC.val, cpu_state.E_ifun.val)
        #wrong prediction
        if not cpu_state.M_cnd.next and cpu_state.E_icode.val == IJXX:
            cpu_state.buble_E_stage()
            cpu_state.buble_D_stage()

        #dstE
        if cpu_state.E_icode.val == ICMOVXX and cpu_state.E_ifun.val != 0:
            if cpu_state.M_cnd.next:
                cpu_state.M_dstE.next = cpu_state.E_srcB.val
            else:
                cpu_state.M_dstE.next = RNONE
        elif cpu_state.E_icode.val in [IOPQ, IRRMOVQ, IIRMOVQ, IMRMOVQ]:
            cpu_state.M_dstE.next = cpu_state.E_srcB.val
        elif cpu_state.E_icode.val in [IPUSHQ, ICALL, IPOPQ, IRET]:
            cpu_state.M_dstE.next = RRSP
        else:
            cpu_state.M_dstE.next = RNONE
        
        #dstM
        if cpu_state.E_icode.val in [IPOPQ, IMRMOVQ]:
            cpu_state.M_dstM.next = cpu_state.E_srcA.val
        else:
            cpu_state.M_dstM.next = RNONE

        cpu_state.M_icode.next = cpu_state.E_icode.val
        cpu_state.M_valA.next = e_valA
        if cpu_state.E_icode.val in [IPOPQ, IRET]:
            cpu_state.M_valA.next = e_valB

    return execute

@block
def memory_access(cpu_state: CPU_state, clk: _Signal, reset: _Signal, last_valE: _Signal, last_valA: _Signal):
    @always_seq(clk.posedge, reset)
    def access():
        mem_addr = intbv(0)[64:]
        mem_data = intbv(0)[64:]
        mem_read = 0
        mem_write = 0
        dmem_error = 0
        #invalid value
        cpu_state.F_valM.next = intbv(0)[64:]

        if cpu_state.M_icode.val in [IRMMOVQ, IPUSHQ, ICALL, IMRMOVQ]:
            mem_addr = cpu_state.M_valE.val
        if cpu_state.M_icode.val in [IPOPQ, IRET]:
            mem_addr = cpu_state.M_valA.val

        mem_read = cpu_state.M_icode.val in [IMRMOVQ, IPOPQ, IRET]
        mem_write = cpu_state.M_icode.val in [IRMMOVQ, IPUSHQ, ICALL]
        
        if cpu_state.M_icode.val in [IPUSHQ, IRMMOVQ, ICALL]:
            mem_data = cpu_state.M_valA.val

        if mem_read or mem_write:
            dmem_error = mem_addr >= len(cpu_state.Mem)

        if mem_read and not dmem_error:
            cpu_state.W_valM.next = read_8byte_number_sig(cpu_state.Mem, mem_addr)
        if mem_write and not dmem_error:
            write_8byte_number_sig(cpu_state.Mem, mem_addr, mem_data)

        #Transfer value to PC selector
        if cpu_state.M_icode.val == IRET:
            if cpu_state.predPC_queue.pop(0) != cpu_state.F_valM.next:
                cpu_state.F_valM.next = cpu_state.W_valM.next
                cpu_state.buble_E_stage()
                cpu_state.buble_M_stage()
                cpu_state.buble_D_stage()

        cpu_state.W_stat.next = cpu_state.M_stat.val
        if dmem_error:
            cpu_state.W_stat.next[2] = 1

        cpu_state.W_dstE.next = cpu_state.M_dstE.val
        cpu_state.W_dstM.next = cpu_state.M_dstM.val    
        cpu_state.W_valE.next = cpu_state.M_valE.val
        cpu_state.W_icode.next = cpu_state.M_icode.val

        last_valE.next = cpu_state.M_valE.val
        last_valA.next = cpu_state.M_valA.val

    return access

@block
def writing_back(cpu_state: CPU_state, clk: _Signal, reset: _Signal, last_dstE: _Signal, last_dstM: _Signal):
    @always_seq(clk.posedge, reset)
    def write_back():
        cpu_state.Stat.next = cpu_state.W_stat.val
        if cpu_state.W_dstE.val != RNONE:
            cpu_state.Registers[int(cpu_state.W_dstE.val)].next = cpu_state.W_valE.val
        if cpu_state.W_dstM.val != RNONE:
            cpu_state.Registers[int(cpu_state.W_dstM.val)].next = cpu_state.W_valM.val
        last_dstE.next = cpu_state.W_dstE.val
        last_dstM.next = cpu_state.W_dstM.val

    return write_back
