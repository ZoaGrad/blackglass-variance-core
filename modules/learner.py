import yaml
import os
import json
from datetime import datetime

class Learner:
    def __init__(self, expertise_path="evidence/expertise.yaml", vault_path="evidence/proposals"):
        self.expertise_path = expertise_path
        self.vault_path = vault_path
        os.makedirs(os.path.dirname(expertise_path), exist_ok=True)
        
    def load_expertise(self):
        if not os.path.exists(self.expertise_path):
            return {"global_rules": [], "assets": {}}
        with open(self.expertise_path, 'r') as f:
            return yaml.safe_load(f) or {"global_rules": [], "assets": {}}

    def save_expertise(self, expertise):
        with open(self.expertise_path, 'w') as f:
            yaml.dump(expertise, f, default_flow_style=False, sort_keys=False)

    def learn_from_mutation(self, mutation_file):
        """
        Analyzes a single mutation file and updates the expertise matrix.
        """
        if not os.path.exists(mutation_file):
            return False

        with open(mutation_file, 'r') as f:
            mutation_data = json.load(f)

        expertise = self.load_expertise()
        
        # Simple Logic: If a mutation failed (PnL < 0), record the trait that caused it
        pnl = mutation_data.get("pnl", 0)
        traits = mutation_data.get("traits", {})
        outcome = mutation_data.get("event_type", "")

        if pnl < 0 or outcome == "DIED":
            # Extract actionable insights (this would be more complex in production)
            # For now, we manually look for common pitfalls like slippage
            asset = traits.get("asset", "UNKNOWN")
            slippage = traits.get("slippage", "UNKNOWN")
            
            if asset not in expertise["assets"]:
                expertise["assets"][asset] = []
                
            rule_id = f"{asset}-ERR-{int(datetime.utcnow().timestamp())}"
            insight = f"Detected failure with slippage guard {slippage}. Consider increasing threshold or reducing exposure."
            
            # Check if a similar rule already exists to avoid duplicates
            exists = any(r["insight"] == insight for r in expertise["assets"][asset])
            
            if not exists:
                expertise["assets"][asset].append({
                    "rule_id": rule_id,
                    "insight": insight,
                    "status": "ACTIVE",
                    "confidence": 75 # Initial low confidence until verified
                })
                self.save_expertise(expertise)
                return True
        
        return False

    def scan_vault(self):
        """
        Scans the vault for all mutation records and learns from them.
        """
        files = [os.path.join(self.vault_path, f) for f in os.listdir(self.vault_path) if f.startswith("mutation_") and f.endswith(".json")]
        learned_count = 0
        for f in files:
            if self.learn_from_mutation(f):
                learned_count += 1
        return learned_count

if __name__ == "__main__":
    # Self-test/CLI entry point
    learner = Learner()
    count = learner.scan_vault()
    print(f"Post-Mortem scan complete. Captured {count} new insights into the Grimoire.")
