from myhdl import block, always_seq, intbv
from myhdl._Signal import _Signal, Signal

IHALT = 0x0
INOP = 0x1
IRRMOVQ = 0x2
IIRMOVQ = 0x3
IRMMOVQ = 0x4
IMRMOVQ = 0x5
IOPQ = 0x6
IJXX = 0x7
ICMOVXX = 0x2
ICALL = 0x8
IRET = 0X9
IPUSHQ = 0XA
IPOPQ = 0XB

FNONE = 0X0
RRSP = 4
RNONE = 0XA
ALUADD = 0X0
SAOK = 0X1
SADR = 0X2
SINS = 0X3
SHLT = 0X4

RRAX = 0X0
RRCX = 0X1
RRDX = 0X2
RRBX = 0X3
RRBP = 0X5
RRSI = 0X6
RRDI = 0X7
RR8 = 0X8
RR9 = 0X9
RR10 = 0XA
RR11 = 0XB
RR12 = 0XC
RR13 = 0XD
RR14 = 0XE


def get_8byte_number(s: list[int]) -> int:
    val = 0
    for i in range(8):
        val |= s[i] << (8 * i)
    return val


@block
def Fetching(program: list[int], clk: _Signal, reset: _Signal, pc: _Signal, 
                            icode: _Signal, ifun: _Signal, rA: _Signal, rB: _Signal, 
                            valC: _Signal, valP: _Signal, instr_valid: _Signal, imem_error: _Signal):
    @always_seq(clk.posedge, reset=reset)
    def fetch():
        # Read current PC value
        pc_val = int(pc)
        if pc_val < 0 or pc_val >= len(program):
            instr_valid.next = 0
            imem_error.next = 1
            return
        
        # Get instruction data
        instr = intbv(program[pc_val])[8:]
        if instr < 0 or instr > 0xB:
            instr_valid.next = 0
            imem_error.next = 0
            return
        
        # Calculate all values first
        icode_val = instr[8:4]
        ifun_val = instr[4:]

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
                immediate_val = get_8byte_number(program[pc_val + 1:pc_val + 9])
                valC.next = intbv(immediate_val)[64:]
                valP.next = pc_val + 9
        else:
            # Handle register instructions
            regs = intbv(program[pc_val + 1])[8:]
            rA.next = regs[8:4]
            rB.next = regs[4:]
            
            # Use named constants for instruction types
            if icode_val in [IIRMOVQ, IRMMOVQ, IMRMOVQ]:
                immediate_val = get_8byte_number(program[pc_val + 2:pc_val + 10])
                valC.next = intbv(immediate_val)[64:]
                valP.next = pc_val + 10
            else:
                valC.next = intbv(0)[64:]
                valP.next = pc_val + 2

    return fetch


@block
def decoding(clk: _Signal, reset: _Signal,  icode: _Signal, \
            rA: _Signal, rB: _Signal,  valA: _Signal, valB: _Signal, \
                    srcA: _Signal, srcB: _Signal, Regs: list[_Signal]):
    @always_seq(clk.posedge, reset=reset)
    def decode():
        if icode.val in [IRRMOVQ, IRMMOVQ, IOPQ, IPUSHQ]:
            srcA.next = int(rA)
        elif icode.val in [IPOPQ, IRET]:
            srcA.next = RRSP
        else:
            srcA.next = RNONE
        
        if icode.val in [IMRMOVQ, IRMMOVQ, IIRMOVQ, IOPQ, ICMOVXX]:
            srcB.next = int(rB)
        elif icode.val in [IPUSHQ, ICALL, IRET, IPOPQ]:
            srcB.next = RRSP
        else:
            srcB.next = RNONE

        if srcA.next != RNONE:
            valA.next = Regs[srcA.next]
        if srcB.next != RNONE:
            valB.next = Regs[srcB.next]
        
        
    return decode


@block
def execution(clk: _Signal, reset: _Signal,  icode: _Signal, ifun: _Signal, \
            valA: _Signal, valB: _Signal, srcA: _Signal, srcB: _Signal, \
                valE: _Signal):
    @always_seq(clk.posedge, reset=reset)
    def execute():
        pass
    
    return execute