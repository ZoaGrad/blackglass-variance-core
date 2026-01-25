import sys
import os
from colorama import Fore, Style, init

# Add root directory to path to allow importing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.learner import Learner

init(autoreset=True)

def main():
    print(f"{Fore.CYAN}{Style.BRIGHT}BLACKGLASS // PROTOCOL OROBOROS // SCRIBE LEARN")
    print(f"{Fore.YELLOW}Initiating post-mortem analysis of mutation records...")
    
    learner = Learner()
    
    # Check if vault exists
    if not os.path.exists(learner.vault_path):
        print(f"{Fore.RED}Error: Vault directory '{learner.vault_path}' not found.")
        return

    count = learner.scan_vault()
    
    if count > 0:
        print(f"{Fore.GREEN}Success! Captured {count} new insights into 'evidence/expertise.yaml'.")
        print(f"{Fore.CYAN}The Genesis Clones have evolved.")
    else:
        print(f"{Fore.WHITE}No new signals detected in the Vault. System is at nominal stability.")

if __name__ == "__main__":
    main()
