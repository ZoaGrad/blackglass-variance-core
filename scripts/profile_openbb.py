import sys
import os
import re

# Hook into the Blackglass kernel
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from blackglass.rlm.tools import SecureToolbox

def profile_target():
    # 1. ACQUIRE TARGET
    # Note: We assume running from blackglass-variance-core/scripts/
    # Correction: Use the known correct path based on previous exploration
    target_path = r"C:\Users\colem\OpenBB"
    
    # Fallback logic from user provided script, adjusted for reality
    if not os.path.exists(target_path):
        target_path = os.path.abspath(os.path.join(os.getcwd(), "../OpenBB"))
    
    if not os.path.exists(target_path):
         target_path = os.path.abspath(os.path.join(os.getcwd(), "OpenBB")) # If running from workspace root
    
    if not os.path.exists(target_path):
        print(f"[ERROR] Target not found at {target_path}")
        return

    print(f"[PROFILE] TARGET LOCKED: {target_path}")
    tools = SecureToolbox(root_dir=target_path)

    # 2. DEFINING THE HEAT SIGNATURES
    # We aren't looking for bugs; we are looking for "Coupling" (Risk)
    signatures = {
        "External Coupling (Blocking Risk)": {
            "pattern": r"requests\.(get|post|put|delete)\(",
            "glob": "*.py",
            "desc": "Sync HTTP calls. If these lack timeouts (default), they hang the Agent."
        },
        "Cognitive Surface (AI Dependence)": {
            "pattern": r"(openai\.|langchain|anthropic\.|temperature=)",
            "glob": "*.py",
            "desc": "Points of Non-Deterministic Variance (Hallucination risk)."
        },
        "Entropy (Technical Debt)": {
            "pattern": r"(TODO|FIXME|HACK):",
            "glob": "*.py",
            "desc": "Known instability or unfinished logic."
        }
    }

    # 3. EXECUTE THE SCAN
    total_risk_score = 0
    
    for category, sig in signatures.items():
        print(f"\n>>> SCANNING: {category}")
        # We use a lower-level list since we want counts, not just 5 lines
        # Using grep_variance from your tools
        hits = tools.grep_variance(pattern=sig["pattern"], glob_pattern=sig["glob"])
        
        # Note: grep_variance might filter lines, but this gives us a sample density
        count = len(hits)
        risk_weight = 1 if "Entropy" in category else 5 # External/AI is higher risk
        total_risk_score += (count * risk_weight)
        
        print(f"    HITS: {count}")
        print(f"    IMPLICATION: {sig['desc']}")
        if count > 0:
            # Print sample, stripping path info if it's there
            print(f"    SAMPLE: {hits[0].strip()[:100]}...")

    # 4. THE THERMODYNAMIC VERDICT
    print(f"\n{'='*40}")
    print(f"SYSTEM THERMODYNAMIC SCORE: {total_risk_score}")
    print(f"{'='*40}")
    
    if total_risk_score > 100:
        print("VERDICT: HIGH VARIANCE DETECTED.")
        print("RECOMMENDATION: Deploy Watchtower to interdict blocking calls and AI drift.")
    else:
        print("VERDICT: STABLE.")

if __name__ == "__main__":
    profile_target()
