from myhdl import Signal, intbv

#from utils import RNONE, INOP

MEM_SIZE = 1024
STACK_SIZE = 648
RNONE = 0XF
RRSP = 4
INOP = 0X1

class CPU_state:
    def __init__(self, main: int):
        self.F_predPC = Signal(intbv(main)[64:])
        self.F_valM = Signal(intbv(0)[64:])
        self.predPC_queue = []
        self.call_stack = []
        
        self.D_stat = Signal(intbv(0)[3:])
        self.D_icode = Signal(intbv(0)[4:])
        self.D_ifun = Signal(intbv(0)[4:])
        self.D_rA = Signal(intbv(RNONE)[4:])
        self.D_rB = Signal(intbv(RNONE)[4:])
        self.D_valC = Signal(intbv(0)[64:].signed())
        self.D_valP = Signal(intbv(0)[64:])

        self.E_stat = Signal(intbv(0)[3:])
        self.E_icode = Signal(intbv(INOP)[4:])
        self.E_ifun = Signal(intbv(0)[4:])
        self.E_valA = Signal(intbv(0)[64:].signed())
        self.E_valB = Signal(intbv(0)[64:].signed())
        self.E_valC = Signal(intbv(0)[64:].signed())
        self.E_dstE = Signal(intbv(RNONE)[4:])
        self.E_dstM = Signal(intbv(RNONE)[4:])
        self.E_srcA = Signal(intbv(0)[4:])
        self.E_srcB = Signal(intbv(0)[4:])
        self.CC = Signal(intbv(0)[3:])
        self.CC_stack = []

        self.M_stat = Signal(intbv(0)[3:])
        self.M_icode = Signal(intbv(0)[4:])
        self.M_cnd = Signal(intbv(1)[1:])
        self.M_valE = Signal(intbv(0)[64:].signed())
        self.M_valA = Signal(intbv(0)[64:].signed())
        self.M_dstE = Signal(intbv(RNONE)[4:])
        self.M_dstM = Signal(intbv(RNONE)[4:])

        self.W_stat = Signal(intbv(0)[3:])
        self.W_icode = Signal(intbv(0)[4:])
        self.W_valE = Signal(intbv(0)[64:].signed())
        self.W_valM = Signal(intbv(0)[64:])
        self.W_dstE = Signal(intbv(RNONE)[4:])
        self.W_dstM = Signal(intbv(RNONE)[4:])



        self.Stat = Signal(intbv(0)[3:])
        self.bubble = Signal(0)
        self.Registers = [Signal(intbv(0)[64:].signed()) for _ in range(15)]
        self.Registers[RRSP] = Signal(intbv(STACK_SIZE)[64:].signed())
        self.Mem = [Signal(intbv(0)[64:].signed()) for _ in range(MEM_SIZE)]

    def buble_M_stage(self):
        self.M_stat.next = intbv(0)[3:]
        self.M_icode.next = INOP
        self.M_dstE.next = RNONE
        self.M_dstM.next = RNONE
    
    def buble_E_stage(self):
        self.E_stat.next = intbv(0)[3:]
        self.E_icode.next = INOP
        self.E_srcA.next = RNONE
        self.E_srcB.next = RNONE
    
    def buble_D_stage(self):
        self.D_stat.next = intbv(0)[3:]
        self.D_icode.next = INOP
        self.D_ifun.next = 0
        self.D_rA.next = RNONE
        self.D_rB.next = RNONE