from myhdl import intbv
import re
from utils import write_8byte_number


commands = {"halt": 0x00, "nop": 0x10, "rrmovq": 0x20, "irmovq": 0x30, "mrmovq": 0x50, \
"rmmovq": 0x40, "addq": 0x60, "subq": 0x61, "andq": 0x62, "xorq": 0x63, "jmp": 0x70, \
"jle": 0x71, "jl": 0x72, "je": 0x73, "jne": 0x74, "jge": 0x75, "jg": 0x76, "call": 0x80, \
"ret": 0x90, "pushq": 0xa0, "popq": 0xb0, "cmovle": 0x21, "cmovl": 0x22, "cmove": 0x23, \
"cmovne": 0x24, "cmovge": 0x25, "cmovg": 0x26}

registers = {"%rax": 0, "%rcx": 1, "%rdx": 2, "%rbx": 3, "%rsp": 4, "%rbp": 5, "%rsi": 6,\
     "%rdi": 7, "%r8": 8, "%r9": 9, "%r10": 0xA, "%r11": 0xB, "%r12": 0xC, "%r13": 0xD, \
        "%r14": 0xE}

def yassembling(file_path: str) -> list[intbv]:
    with open(file_path, 'r') as file:
        lines = file.readlines()
    machine_code = []
    labels = {}
    for line in lines:
        if line.startswith('#'):
            continue
        if line.strip() == '':
            continue
        if line.strip().startswith('$') and line.strip().endswith(':'):
            labels[line.strip()[1:-1]] = len(machine_code)
            continue
        words = re.split(r'[,\s; ]+', line.strip())
        words = list(filter(lambda x: x != '', words))
        if words[0] not in commands:
            raise ValueError(f"Invalid command: {words[0]}")
        m_command = intbv(commands[words[0]])[8:]
        if len(words) == 1:
            if words[0] in ["halt", "nop", "ret"]:
                machine_code.append(m_command)
            else:
                raise ValueError(f"Wrong number of arguments: {line}")
        elif len(words) == 2:
            if words[0] in ["jmp", "jle", "jl", "je", "jne", "jge", "jg", "call"]:
                if words[1].isdigit():
                    m_dest = intbv(int(words[1]))[64:]
                    machine_code.append(m_command)
                    for _ in range(8):
                        machine_code.append(intbv(0)[8:])
                    write_8byte_number(machine_code, len(machine_code) - 8, m_dest)
                elif words[1] in labels:
                    m_dest = intbv(labels[words[1]])[64:]
                    machine_code.append(m_command)
                    for _ in range(8):
                        machine_code.append(intbv(0)[8:])
                    write_8byte_number(machine_code, len(machine_code) - 8, m_dest)
                else:
                    raise ValueError(f"Second argument must be an addres of destination: {line}")
            elif words[0] in ["pushq", "popq"]:
                if words[1] in registers:
                    m_reg = intbv(0)[8:]
                    m_reg[8:4] = registers[words[1]]
                    m_reg[4:0] = 0xF
                    machine_code.append(m_command)
                    machine_code.append(m_reg)
                else:
                    raise ValueError(f"Second argument must be a register: {line}")
            else:
                raise ValueError(f"Invalid command: {line}")
        elif len(words) == 3:
            if words[0] in ["rrmovq", "addq", "subq", "andq", "xorq", "cmovle", \
                "cmovl", "cmove", "cmovne", "cmovge", "cmovg"]:
                if words[1] in registers and words[2] in registers:
                    m_regs = intbv(0)[8:]
                    m_regs[8:4] = registers[words[1]]
                    m_regs[4:0] = registers[words[2]]
                    machine_code.append(m_command)
                    machine_code.append(m_regs)
                else:
                    raise ValueError(f"Second and third arguments must be registers: {line}")
            elif words[0] == "irmovq":
                if re.fullmatch(r'[+-]?\d+', words[1]) and words[2] in registers:
                    m_dest = intbv(int(words[1]))[64:]
                    m_reg = intbv(0)[8:]
                    m_reg[8:4] = 0xF
                    m_reg[4:0] = registers[words[2]]
                    machine_code.append(m_command)
                    machine_code.append(m_reg)
                    for _ in range(8):
                        machine_code.append(intbv(0)[8:])
                    write_8byte_number(machine_code, len(machine_code) - 8, m_dest)
                else:
                    raise ValueError(f"Second argument must be an immediate value and first argument must be an register: {line}")
            elif words[0] == "mrmovq":
                arg1 = re.split(r'[,\s;() ]+', words[1].strip())
                arg1 = list(filter(lambda x: x != '', arg1))
                if arg1[0].isdigit() and arg1[1] in registers and words[2] in registers:
                    m_reg = intbv(0)[8:]
                    m_reg[8:4] = registers[words[2]]
                    m_reg[4:0] = registers[arg1[1]]
                    machine_code.append(m_command)
                    machine_code.append(m_reg)
                    for _ in range(8):
                        machine_code.append(intbv(0)[8:])
                    write_8byte_number(machine_code, len(machine_code) - 8, intbv(arg1[0])[64:])
                else:
                    raise ValueError(f"First argument must be an address and second argument must be a register - D(rB), rA: {line}")
            elif words[0] == "rmmovq":
                arg1 = re.split(r'[,\s;() ]+', words[2].strip())
                arg1 = list(filter(lambda x: x != '', arg1))
                if arg1[0].isdigit() and arg1[1] in registers and words[1] in registers:
                    m_reg = intbv(0)[8:]
                    m_reg[8:4] = registers[words[1]]
                    m_reg[4:0] = registers[arg1[1]]
                    machine_code.append(m_command)
                    machine_code.append(m_reg)
                    for _ in range(8):
                        machine_code.append(intbv(0)[8:])
                    write_8byte_number(machine_code, len(machine_code) - 8, intbv(arg1[0])[64:])
                else:
                    raise ValueError(f"First argument must be an address and second argument must be a register - rA, D(rB): {line}")
            else:
                raise ValueError(f"This command should have 1 or 0 arguments, but has 2: {line}")
        else:
            raise ValueError(f"Too many arguments. Max is 2, but has {len(words) - 1}: {line}")
    main = -1 if 'main' not in labels else labels['main']
    return machine_code, main

if __name__ == "__main__":
    file_path = input("Enter the path to the file with the program: ")
    program, main = yassembling(file_path)
    for elem in program:
        print(hex(int(elem)), end=" ")