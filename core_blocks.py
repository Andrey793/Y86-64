import myhdl
from myhdl import block, always_seq, intbv
from myhdl._Signal import _Signal, Signal

IHALT = 0x0
INOP = 0x1
IRRMOVQ = 0x2
IRMOVQ = 0x3
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
def instruction_mem(program: list[int], clk: _Signal, reset: _Signal, pc: _Signal, icode: _Signal, ifun: _Signal, rA: _Signal, rB: _Signal, valC: _Signal, valP: _Signal):
    @always_seq(clk.posedge, reset=reset)
    def read():
        pc_val = int(pc)
        instr = intbv(program[pc_val])[8:]
        icode.next = instr[8:4]
        ifun.next = instr[4:]
        #halt, nop, jXX, call, ret
        if instr[8:4] in [0x0, 0x1, 0x7, 0x8, 0x9]:
            rA.next = 0xF
            rB.next = 0xF
            #halt, nop, ret
            if instr[8:4] in [0x0, 0x1, 0x9]:
                valC.next = intbv(0)[64:]
                valP.next = pc_val + 1
            else:
                valC.next = intbv(get_8byte_number(program[pc_val + 1:pc_val + 9]))[64:]
                valP.next = pc_val + 9
        else:
            regs = intbv(program[pc_val + 1])[8:]
            rA.next = regs[8:4]
            rB.next = regs[4:]
            # irmovq, rmmovq, mrmovq
            if instr[8:4] in [0x3, 0x4, 0x5]:
                valC.next = intbv(get_8byte_number(program[pc_val + 2:pc_val + 10]))[64:]
                valP.next = pc_val + 10
            else:
                valC.next = intbv(0)[64:]
                valP.next = pc_val + 2

    return read


@block
def decoding(clk: _Signal, reset: _Signal,  icode: _Signal, ifun: _Signal, rA: _Signal, rB: _Signal, valC: _Signal, valA: _Signal, valB: _Signal, valP: _Signal):
    if int(ifun) in []
