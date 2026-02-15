import json
import os
import glob
import datetime
import sys
import time

# Configuration
EVIDENCE_VAULT = os.path.abspath(os.path.join(os.path.dirname(__file__), "evidence/proposals"))
SOVEREIGN_IDENTITY = "ARCHITECT_OVERRIDE_AUTH_001"
REGENCY_IDENTITY = "REGENCY_PROTOCOL_V1"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def check_regency(runtime_config_path):
    """
    Checks if the System is in Regency Mode (Dead Man's Switch).
    """
    try:
        with open(runtime_config_path, "r") as f:
            config = json.load(f)
            gov = config.get("governance_state", {})
            last_ratified = gov.get("last_ratification_timestamp")
            
            if not last_ratified:
                return False, "NO_HISTORY"
                
            last_dt = datetime.datetime.fromisoformat(last_ratified)
            now = datetime.datetime.utcnow()
            delta = now - last_dt
            
            if delta.days >= 7: # Hardcoded 7 days from Constitution
                return True, f"REGENCY ACTIVE (Architect silent for {delta.days} days)"
            else:
                return False, f"ARCHITECT ACTIVE (Silent for {delta.days} days)"
    except Exception as e:
        return False, f"ERROR: {e}"

def load_proposals():
    proposals = []
    if not os.path.exists(EVIDENCE_VAULT):
        return []
    
    files = glob.glob(os.path.join(EVIDENCE_VAULT, "*.json"))
    
    for filepath in files:
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                data["_filepath"] = filepath # Store path for writing back
                proposals.append(data)
        except:
            pass
    return proposals

def print_header():
    print("\n" + "═" * 60)
    print("       🏛️  BLACKGLASS SOVEREIGN RATIFICATION CEREMONY 🏛️")
    print("═" * 60 + "\n")

def display_proposal(p):
    print(f"📄 PROPOSAL ID: {p.get('id')}")
    print(f"   TYPE:        {p.get('type')}")
    print(f"   RISK:        {p.get('risk_level', 'UNKNOWN')}")
    print(f"   AUTHOR:      {p.get('author')}")
    print(f"   TIMESTAMP:   {p.get('timestamp')}")
    print(f"   STATUS:      {p.get('status')}")
    print("-" * 60)
    print(f"   JUSTIFICATION:\n   {p.get('justification')}")
    print("-" * 60)
    print(f"   CONTENT TARGET: {p.get('content', {}).get('target')}")
    print(f"   CONTENT ACTION: {p.get('content', {}).get('action')}")
    print("\n")

def apply_mutation(proposal):
    """
    The Mutation Engine: Transmutes Ratified Will into System Configuration.
    """
    config_path = os.path.join(os.path.dirname(__file__), "runtime_config.json")
    
    if not os.path.exists(config_path):
        print("❌ ERROR: Runtime config not found.")
        return False
        
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            
        target = proposal.get("content", {}).get("target")
        action = proposal.get("content", {}).get("action")
        params = proposal.get("content", {}).get("parameters", {})
        
        # --- MUTATION LOGIC ---
        if target == "radiance_server.py" and action == "OPTIMIZE_AUDIT_LOGIC":
            if params.get("caching") == "ENABLED":
                print("   ⚡ MUTATING: Enabling Audit Caching...")
                config["audit_logic"]["caching"] = "ENABLED"
                config["audit_logic"]["latency_simulator_ms"] = 10 
        
        # Update Governance State
        config["governance_state"]["last_ratification_timestamp"] = datetime.datetime.utcnow().isoformat()
        
        # Stamp the mutation
        config["last_mutation"] = {
            "proposal_id": proposal.get("id"),
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "action": action
        }
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
            
        print("   ✨ MUTATION COMPLETE: Runtime Config Updated.")
        return True
        
    except Exception as e:
        print(f"❌ MUTATION FAILED: {e}")
        return False

def ratify_logic(p, decision, mode="ARCHITECT"):
    p["ratified_at"] = datetime.datetime.utcnow().isoformat()
    if mode == "REGENCY":
        p["ratified_by"] = REGENCY_IDENTITY
    else:
        p["ratified_by"] = SOVEREIGN_IDENTITY
    
    if decision == "APPROVE":
        p["status"] = "RATIFIED" if mode == "ARCHITECT" else "RATIFIED (REGENCY)"
        p["execution_log"] = f"{mode} Will executed. Configuration updated."
        print(f"\n✅ PROPOSAL {p.get('id')} RATIFIED by {mode}.")
        
        # TRIGGER THE MUTATION ENGINE
        apply_mutation(p)
        
    elif decision == "VETO":
        p["status"] = "VETOED"
        p["execution_log"] = f"{mode} Veto executed. Proposal archived."
        print(f"\n🚫 PROPOSAL {p.get('id')} VETOED.")
    
    with open(p["_filepath"], "w") as f:
        # Remove internal key before saving
        save_data = p.copy()
        del save_data["_filepath"]
        json.dump(save_data, f, indent=2)
    
    time.sleep(1.5)

def ratify_proposals_batch(auto_mode=False, regency_mode=False):
    if not auto_mode:
        print("⚖️  INITIATING RATIFICATION CEREMONY...")
    
    all_proposals = load_proposals()
    pending = [p for p in all_proposals if p.get("status") == "PROPOSED"]
    
    if not pending:
        if not auto_mode:
            print("   No pending proposals in the Evidence Vault.")
        return

    if auto_mode:
        print("🤖 AUTO-RATIFICATION INITIATED...")
        if regency_mode:
            print("👑 REGENCY PROTOCOL: Filtering for LOW RISK only...")

    for p in pending:
        p_id = p.get("id")
        p_risk = p.get("risk_level", "UNKNOWN")
        
        if auto_mode:
            if regency_mode:
                if p_risk == "PARAMETER_TUNE": # Constitution.REGENCY.RISK_LOW
                    print(f"👑 REGENCY: Auto-Approving LOW RISK proposal {p_id}...")
                    ratify_logic(p, "APPROVE", mode="REGENCY")
                else:
                    print(f"🔒 REGENCY: Skipping {p_risk} proposal {p_id} (Requires Architect).")
            else:
                print(f"🤖 AUTO-APPROVING: {p_id}")
                ratify_logic(p, "APPROVE", mode="ARCHITECT")
            continue

def interactive_ceremony():
    while True:
        clear_screen()
        print_header()
        
        all_proposals = load_proposals()
        pending = [p for p in all_proposals if p.get("status") == "PROPOSED"]
        
        if not pending:
            print("✨ THE VAULT IS SILENT. No pending proposals.")
            print("\n[H] History  [Q] Quit")
            choice = input("\nSelect Action: ").strip().upper()
            if choice == "Q": break
            if choice == "H":
                print("\n--- HISTORY ---")
                for p in all_proposals:
                    if p.get("status") != "PROPOSED":
                        print(f"[{p.get('status')}] {p.get('id')} - {p.get('type')}")
                input("\nPress Enter to continue...")
            continue
            
        print(f"⚠️  PENDING PROPOSALS: {len(pending)}\n")
        
        for idx, p in enumerate(pending):
            print(f"[{idx + 1}] {p.get('type')} - {p.get('id')} ({p.get('urgency')})")
            
        print("\n[Q] Quit")
        
        choice = input("\nSelect Proposal to Review (Number): ").strip().upper()
        if choice == "Q": break
        
        try:
            selection_idx = int(choice) - 1
            if 0 <= selection_idx < len(pending):
                selected_p = pending[selection_idx]
                clear_screen()
                print_header()
                display_proposal(selected_p)
                
                print("SOVEREIGN DECISION REQUIRED:")
                print("[A] APPROVE (Ratify)")
                print("[V] VETO (Reject)")
                print("[B] BACK (Defer)")
                
                vote = input("\n🗳️  CAST VOTE: ").strip().upper()
                
                if vote == "A":
                    # Simulated Key Ceremony
                    key = input("🔑 AUTHENTICATION (Press Enter to Sign): ")
                    ratify_logic(selected_p, "APPROVE")
                elif vote == "V":
                    reason = input("📝 REASON FOR VETO: ")
                    selected_p["veto_reason"] = reason
                    ratify_logic(selected_p, "VETO")
                else:
                    print("Deferring...")
                    time.sleep(1)
        except ValueError:
            pass

def main():
    # 1. AUTO MODE (CI/CD)
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        ratify_proposals_batch(auto_mode=True)
        return

    # 2. REGENCY CHECK (Dead Man's Switch)
    is_regency_check = len(sys.argv) > 1 and sys.argv[1] == "--regency-check"
    RUNTIME_CONFIG = os.path.abspath(os.path.join(os.path.dirname(__file__), "runtime_config.json"))
    is_regency, regency_msg = check_regency(RUNTIME_CONFIG)
    
    if is_regency_check:
        print(f"👑 REGENCY CHECK: {regency_msg}")
        if is_regency:
            print("   > MODE: DEAD MAN'S SWITCH ACTIVE")
            print("   > ACTION: Auto-Ratifying LOW RISK proposals only.")
            ratify_proposals_batch(auto_mode=True, regency_mode=True)
        else:
            print("   > MODE: ARCHITECT ACTIVE. No automated action taken.")
        return

    # 3. INTERACTIVE MODE (Architect)
    # Clear screen for impact
    clear_screen()
    print(f"Status: {regency_msg}") # Show Regency status on startup
    if is_regency:
        print("⚠️  SYSTEM IS IN REGENCY MODE. YOU ARE OVERRIDING THE DEAD MAN'S SWITCH.")
        time.sleep(2)
        
    interactive_ceremony()

if __name__ == "__main__":
    main()
