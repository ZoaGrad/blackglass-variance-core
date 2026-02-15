
import time
import random
import logging
from modules.logic_gasket import LogicGasket

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def simulate_entropy(gasket: LogicGasket, cycles=20):
    print(f"\n--- GASKET SIMULATION (Threshold: {gasket.panic_threshold}) ---")
    
    for i in range(cycles):
        # Simulate increasing entropy (failure probability rises)
        fail_prob = min(0.1 + (i * 0.05), 1.0) 
        
        print(f"[{i+1}/{cycles}] Prob_Fail={fail_prob:.2f} | State={gasket.state.name} | ConstStatus={gasket.constitutional_status}")
        
        with gasket.guard() as token:
            if token is None:
                print("    ---> [BLOCKED] System Locked.")
                continue
                
            # Simulate work
            if random.random() < fail_prob:
                print("    ---> [FAIL] Computation Error")
                raise RuntimeError("Entropy Error")
            else:
                print("    ---> [OK] Result Computed")
                
        time.sleep(0.1)

if __name__ == "__main__":
    # Initialize with strict remediation standard
    gasket = LogicGasket(reset_timeout=2) 
    try:
        simulate_entropy(gasket)
    except RuntimeError:
        pass # Expected during simulation
    except Exception as e:
        print(f"FATAL: {e}")
