from myhdl import intbv
import myhdl
from myhdl._Signal import _Signal

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

def read_8byte_number_sig(s: list[_Signal], ind: int) -> int:
    val = intbv(0)[64:]
    for j in range(8):
        val[8 * (j + 1) : 8 * j] = intbv(s[j + ind].val)[8:]
    return val

def write_8byte_number_sig(s: list[_Signal], ind: int, val: int | intbv):
    num = intbv(val)[64:]
    for j in range(8):
        s[j + ind].next = num[8 * (j + 1) : 8 * j]

def read_8byte_number(s: list[intbv], ind: int) -> int:
    val = intbv(0)[64:]
    for j in range(8):
        val[8 * (j + 1) : 8 * j] = intbv(s[j + ind])[8:]
    return val

def write_8byte_number(s: list[intbv], ind: int, val: int | intbv):
    num = intbv(val)[64:]
    for j in range(8):
        s[j + ind] = num[8 * (j + 1) : 8 * j]

def is_overflow(valA: int, valB: int, result: int, ifun: int) -> bool:
    if ifun == 0:
        return (valA > 0 and valB > 0 and result < 0) or (valA < 0 and valB < 0 and result > 0)
    elif ifun == 1:
        return (valA > 0 and valB < 0 and result < 0) or (valA < 0 and valB > 0 and result > 0)
    else:
        return False

def Cond(CC: intbv, ifun: int) -> bool:
    # Extract flag variables from condition codes
    zf = bool(CC[0]) 
    sf = bool(CC[1])  
    of = bool(CC[2])  
    
    # Unconditional jump
    if ifun == 0:
        return True
    # less or equal - (SF^OF) | ZF
    if ifun == 1:
        return (sf != of) or zf
    #less - SF^OF
    if ifun == 2:
        return sf != of
    # equal - ZF
    if ifun == 3:
        return zf
    #not equal  - ~ZF
    if ifun == 4:
        return not zf
    # greater or equal  - ~(SF^OF)
    if ifun == 5:
        return not (sf != of)
    #greater - ~(SF^OF) & ~ZF
    if ifun == 6:
        return not (sf != of) and not zf
    
    # Invalid jump function - return False
    return False


regs = {0: "rax", 1: "rcx", 2: "rdx", 3: "rbx", 4: "rsp", 5: "rbp", 6: "rsi", 7: \
"rdi", 8: "r8", 9: "r9", 10: "r10", 11: "r11", 12: "r12", 13: "r13", 14: "r14"}

def print_registers(Regs: list[intbv]):
    print("Registers: ", end="")
    for i in range(15):
        print(f"{regs[i]}: {int(Regs[i])}", end=" | ")
    print('\n' + "-" * 50)
    print()

def check_diff(old_regs: list[intbv], new_regs: list[intbv], old_mem: list[intbv], new_mem: list[intbv], old_CC: intbv, new_CC: intbv):
    #check regs
    d1 = False
    d2 = False
    d3 = False
    for i in range(15):
        if old_regs[i].val != new_regs[i].val:
            print(f"{regs[i]}: {int(old_regs[i].val)} -> {int(new_regs[i].val)}", end=" | ")
            d1 = True
    #check mem
    if d1:
        print()
    for i in range(1024):
        if old_mem[i].val != new_mem[i].val:
            print(f"Mem addr {i}: {int(old_mem[i].val)} -> {int(new_mem[i].val)}")
            d2 = True
    if old_CC.val != new_CC.val:
        print(f"CC: {bin(old_CC.val)} -> {bin(new_CC.val)}")
        d3 = True
    if d1 or d2 or d3:
        print("Sim time =", myhdl.now())
        print("-" * 50)
