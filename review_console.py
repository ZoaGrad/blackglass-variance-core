import os
import json
import glob
import sys
from colorama import Fore, Style, init

init(autoreset=True)

# Path to Evidence Vault
# Assuming review_console.py is in blackglass-variance-core (same dir as radiance_server.py)
EVIDENCE_VAULT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../evidence/proposals"))

def list_proposals():
    print(Fore.CYAN + f"\n>>> SCANNING VAULT: {EVIDENCE_VAULT}")
    pattern = os.path.join(EVIDENCE_VAULT, "prop-*.json")
    files = glob.glob(pattern)
    
    if not files:
        print(Fore.YELLOW + "   [EMPTY] No active proposals found.")
        return

    print(Fore.WHITE + f"{'ID':<40} | {'TYPE':<25} | {'URGENCY':<10} | {'STATUS'}")
    print("-" * 100)
    
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            pid = data.get("id", "UNKNOWN")
            ptype = data.get("type", "UNKNOWN")
            purgency = data.get("urgency", "NORMAL")
            pstatus = data.get("status", "PROPOSED")
            
            color = Fore.GREEN if pstatus == "PROPOSED" else Fore.DIM
            print(color + f"{pid:<40} | {ptype:<25} | {purgency:<10} | {pstatus}")
        except Exception as e:
            print(Fore.RED + f"!! CORRUPT FILE: {os.path.basename(fpath)}")

def read_proposal(prop_id):
    # Allow user to pass just the uuid part or full name
    if not prop_id.startswith("prop-"):
        prop_id = f"prop-{prop_id}"
    if not prop_id.endswith(".json"):
        prop_id = f"{prop_id}.json"
        
    fpath = os.path.join(EVIDENCE_VAULT, prop_id)
    
    if not os.path.exists(fpath):
        print(Fore.RED + f"!! PROPOSAL NOT FOUND: {prop_id}")
        return
        
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(Fore.RED + f"!! ERROR READING PROPOSAL: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python review_console.py [list | read <id>]")
        return

    command = sys.argv[1].lower()
    
    if command == "list":
        list_proposals()
    elif command == "read":
        if len(sys.argv) < 3:
            print("Usage: python review_console.py read <proposal_id>")
        else:
            read_proposal(sys.argv[2])
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
