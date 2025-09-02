from myhdl import block, always_seq, intbv
from myhdl._Signal import _Signal
from utils import *


@block
def pipeline_cycle(program: list[intbv], clk: _Signal, reset: _Signal, 
                   # Fetch stage signals
                   pc: _Signal, icode: _Signal, ifun: _Signal, rA: _Signal, rB: _Signal, 
                   valC: _Signal, valP: _Signal, instr_valid: _Signal, imem_error: _Signal,
                   # Decode stage signals  
                   srcA: _Signal, srcB: _Signal, valA: _Signal, valB: _Signal,
                   # Execute stage signals
                   valE: _Signal, Cnd: _Signal, CC: _Signal, dstE: _Signal, dstM: _Signal,
                   # Memory stage signals
                   valM: _Signal, dmem_error: _Signal, Stat: _Signal,
                   # Register file and memory
                   Regs: list[_Signal], mem: list[intbv]):
    
    @always_seq(clk.posedge, reset=reset)
    def cycle():
        
        # ===== FETCH STAGE =====
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

        # Determine instruction type and calculate immediate values
        is_simple = icode_val in [IHALT, INOP, IJXX, ICALL, IRET]
        valC_val = intbv(0)[64:]
        valP_val = pc_val + 1
        regs = intbv(0)[8:]
        
        if is_simple:
            rA_val = RNONE
            rB_val = RNONE
            
            if icode_val in [IHALT, INOP, IRET]:
                valC_val = intbv(0)[64:]
                valP_val = pc_val + 1
            else:
                # Calculate immediate value for JXX and CALL
                immediate_val = read_8byte_number(program, pc_val + 1)
                valC_val = intbv(immediate_val)[64:]
                valP_val = pc_val + 9
        else:
            # Handle register instructions
            regs = intbv(program[pc_val + 1])[8:]
            rA_val = regs[8:4]
            rB_val = regs[4:]
            
            # Use named constants for instruction types
            if icode_val in [IIRMOVQ, IRMMOVQ, IMRMOVQ]:
                immediate_val = read_8byte_number(program, pc_val + 2)
                valC_val = immediate_val
                valP_val = pc_val + 10
            else:
                valC_val = intbv(0)[64:]
                valP_val = pc_val + 2

        valA_val = intbv(0)[64:]
        valB_val = intbv(0)[64:]
        
        # ===== DECODE STAGE =====
        srcA_val = RNONE
        srcB_val = RNONE
        
        if icode_val in [IRRMOVQ, IRMMOVQ, IOPQ, IPUSHQ]:
            srcA_val = int(rA_val)
        elif icode_val in [IPOPQ, IRET]:
            srcA_val = int(rA_val)
        
        if icode_val in [IMRMOVQ, IIRMOVQ, IOPQ, ICMOVXX]:
            srcB_val = int(rB_val)
        elif icode_val in [IPUSHQ, ICALL, IRET, IPOPQ]:
            srcB_val = RRSP
        
        if srcA_val != RNONE:
            valA_val = Regs[srcA_val].val
        if srcB_val != RNONE:
            valB_val = Regs[srcB_val].val

        # ===== EXECUTE STAGE =====
        aluA = intbv(0)[64:]
        aluB = intbv(0)[64:]
        if icode_val in [IRRMOVQ, IOPQ]:
            aluA = valA_val
        if icode_val in [IIRMOVQ, IRMMOVQ, IMRMOVQ]:
            aluA = valC_val
        if icode_val in [ICALL, IPUSHQ]:
            aluA = -8
        if icode_val in [IRET, IPOPQ]:
            aluA = 8

        if icode_val in [IMRMOVQ, IOPQ, IRMMOVQ, IPUSHQ, IPOPQ, ICALL, IRET]:
            aluB = valB_val
       
        #CC = intvbv(0)[3:] and CC[0] -> ZF, CC[1] -> SF, CC[2] -> OF
        valE_val = intbv(0)[64:]
        CC_val = intbv(0)[3:]
        
        if icode_val == IOPQ:
            if ifun_val == 0:
                valE_val = aluA + aluB
            elif ifun_val == 1:
                valE_val = aluA - aluB
            elif ifun_val == 2:
                valE_val = aluA & aluB
            elif ifun_val == 3:
                valE_val = aluA ^ aluB
            if valE_val == 0:
                CC_val[0] = 1
            if valE_val < 0:
                CC_val[1] = 1
            if is_overflow(valA_val, valB_val, valE_val, ifun_val):
                CC_val[2] = 1
        else:
            valE_val = aluA + aluB
            
        Cnd_val = 1
        if icode_val == IJXX or icode_val == ICMOVXX:
            Cnd_val = Cond(CC_val, ifun_val)

        #dstE
        dstE_val = RNONE
        if icode_val == ICMOVXX and ifun_val != 0:
            if Cnd_val:
                dstE_val = srcB_val
        elif icode_val in [IOPQ, IRRMOVQ, IIRMOVQ, IMRMOVQ]:
            dstE_val = srcB_val
        elif icode_val in [IPUSHQ, ICALL, IPOPQ, IRET]:
            dstE_val = RRSP
        
        #dstM
        dstM_val = RNONE
        if icode_val in [IPOPQ, IMRMOVQ]:
            dstM_val = srcA_val

        # ===== MEMORY STAGE =====
        mem_addr = intbv(0)[64:]
        mem_data = intbv(0)[64:]
        mem_read = 0
        mem_write = 0

        if icode_val in [IRMMOVQ, IPUSHQ, ICALL, IMRMOVQ]:
            mem_addr = valE_val
        if icode_val in [IPOPQ, IRET]:
            mem_addr = valB_val

        mem_read = icode_val in [IMRMOVQ, IPOPQ, IRET]
        mem_write = icode_val in [IRMMOVQ, IPUSHQ, ICALL]
        
        if icode_val in [ICALL]:
            mem_data = valP_val
        if icode_val in [IPUSHQ, IRMMOVQ]:
            mem_data = valA_val

        dmem_error_val = 0
        if mem_read or mem_write:
            dmem_error_val = mem_addr >= len(mem)

        valM_val = intbv(0)[64:]
        if mem_read and not dmem_error_val:
            valM_val = read_8byte_number_sig(mem, mem_addr)
        if mem_write and not dmem_error_val:
            write_8byte_number_sig(mem, mem_addr, mem_data)

        # ===== STATUS DETERMINATION =====
        Stat_val = SAOK
        if imem_error.val:
            Stat_val = SADR  # Address error
        elif not instr_valid.val:
            Stat_val = SINS  # Invalid instruction
        elif dmem_error_val:
            Stat_val = SADR  # Data memory error
        elif icode_val == IHALT:
            Stat_val = SHLT  # Halt

        # ===== FINAL ASSIGNMENTS TO SIGNALS =====
        icode.next = icode_val
        ifun.next = ifun_val
        rA.next = regs[8:4]
        rB.next = regs[4:]
        valC.next = valC_val
        valP.next = valP_val
        srcA.next = srcA_val
        srcB.next = srcB_val
        valA.next = valA_val
        valB.next = valB_val
        valE.next = valE_val
        Cnd.next = Cnd_val
        CC.next = CC_val
        dstE.next = dstE_val
        dstM.next = dstM_val
        valM.next = valM_val
        dmem_error.next = dmem_error_val
        Stat.next = Stat_val

        # ===== WRITEBACK STAGE =====
        if dstE_val != RNONE:
            Regs[int(dstE_val)].next = valE_val
        if dstM_val != RNONE:
            Regs[int(dstM_val)].next = valM_val

        # ===== PC UPDATE =====
        if icode_val == ICALL:
            pc.next = valC_val
        elif icode_val == IRET:
            pc.next = valM_val
        elif icode_val == IJXX and Cnd_val:
            pc.next = valC_val
        else:
            pc.next = valP_val

    return cycle