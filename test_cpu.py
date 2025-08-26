import yasm
from CPU import *
from myhdl import ResetSignal
from myhdl import Simulation, StopSimulation

def test_cpu(program: list[intbv]):
    # Create signals
    clk = Signal(bool(0))
    reset = ResetSignal(val=0, active=1, isasync=False)
    
    # Instantiate CPU and generators
    cpu = CPU(program, clk, reset)
    clock_gen = clock_generator(clk, period=40)
    reset_gen = reset_generator(reset, clk, reset_cycles=3)
    
    # Run simulation
    try:
        sim = Simulation(cpu, clock_gen, reset_gen)
        sim.run(2000)  # Run for 100 time units
        sim.quit()
    except StopSimulation as e:
        print(e)

    
if __name__ == "__main__":
    file_path = input("Enter the path to the file with the program: ")
    program = yasm.yassembling(file_path)
    test_cpu(program)

    #добавить метки и уметь их парсить в машинный код