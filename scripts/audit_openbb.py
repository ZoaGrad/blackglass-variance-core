import sys
import os

# Ensure we can import the blackglass modules
# We are in scripts/, so parent is root.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from blackglass.rlm.tools import SecureToolbox

def run_audit():
    # 1. Point the Tooling at the Sibling Repo (The Target)
    # Original: target_path = os.path.abspath(os.path.join(os.getcwd(), "../OpenBB"))
    # Correction: We need to go up two levels from local repo root if assume local repo is under 'Code' and Target is under 'Users/colem'
    # Current CWD is usually repo root C:\Users\colem\Code\blackglass-variance-core
    # So ../OpenBB is C:\Users\colem\Code\OpenBB (which is empty/wrong)
    # We want C:\Users\colem\OpenBB
    
    # Try absolute path first for certainty, based on exploration
    target_path = r"C:\Users\colem\OpenBB"
    
    # Fallback/verification
    if not os.path.exists(target_path):
        # Try relative
        target_path = os.path.abspath(os.path.join(os.getcwd(), "../../OpenBB"))
        
    print(f"[AUDIT] TARGET LOCKED: {target_path}")
    
    if not os.path.exists(target_path):
        print("[ERROR] Target not found. Did you clone it to the right place?")
        return

    # Check if we are pointing at the empty one
    if not os.path.exists(os.path.join(target_path, 'openbb_platform')): 
         # The populated one had 'openbb_platform' dir. The empty one had only .git
         print(f"[WARNING] Target {target_path} might be empty. Checking contents...")
         print(os.listdir(target_path))

    tools = SecureToolbox(root_dir=target_path)

    # 2. SCAN: Look for "Infinite Wait" risks (timeout=None)
    # This is a classic reliability flaw in financial agents.
    print("\n[STEP 1] Scanning for Infinite Wait Risks (timeout=None)...")
    hits_timeout = tools.grep_variance(pattern="timeout=None", glob_pattern="*.py")
    
    if hits_timeout:
        print(f"   >>> DANGER: Found {len(hits_timeout)} instances of potential infinite hangs.")
        for hit in hits_timeout[:5]: # Show first 5
            print(f"   [EVIDENCE] {hit}")
    else:
        print("   >>> CLEAN: No explicit timeout=None patterns found.")

    # 3. SCAN: Look for "Blind Excepts" (Swallowing Errors)
    print("\n[STEP 2] Scanning for Error Suppression (bare 'except:')...")
    hits_except = tools.grep_variance(pattern="except:", glob_pattern="*.py")
    
    # Filter for bare excepts (heuristic)
    bare_excepts = [h for h in hits_except if "except:" in h and "except Exception" not in h]

    if bare_excepts:
        print(f"   >>> DANGER: Found {len(bare_excepts)} instances of blind error suppression.")
        for hit in bare_excepts[:5]:
            print(f"   [EVIDENCE] {hit}")
    else:
        print("   >>> CLEAN: No bare except blocks found.")

    # 4. SCAN: Look for "Blocking Coupling" (Synchronous Requests)
    print("\n[STEP 3] Scanning for Blocking Coupling (requests.get etc)...")
    # broadening pattern to capture common synchronous calls
    hits_blocking = []
    for method in ["requests.get", "requests.post", "requests.put", "requests.delete"]:
        hits_blocking.extend(tools.grep_variance(pattern=method, glob_pattern="*.py"))
    
    if hits_blocking:
        print(f"   >>> CRITICAL: Found {len(hits_blocking)} instances of synchronous blocking coupling.")
        print(f"       Risk: Hydrostatic Lock if target API stalls.")
        for hit in hits_blocking[:5]:
            print(f"   [EVIDENCE] {hit}")
    else:
        print("   >>> CLEAN: No synchronous requests calls found (unexpected for this codebase).")

    # 5. SCAN: Look for "Technical Debt" (TODO/FIXME)
    print("\n[STEP 4] Scanning for Technical Debt (TODO/FIXME)...")
    hits_debt = []
    for marker in ["TODO", "FIXME"]:
        hits_debt.extend(tools.grep_variance(pattern=marker, glob_pattern="*.py"))
        
    if hits_debt:
        print(f"   >>> WARNING: Found {len(hits_debt)} unaddressed technical debt items.")
        for hit in hits_debt[:5]:
            print(f"   [EVIDENCE] {hit}")
    else:
        print("   >>> CLEAN: No TODO/FIXME markers found.")

    # 6. SCAN: Cognitive Surface (OpenAI integration)
    hits_cognitive = tools.grep_variance(pattern="openai", glob_pattern="*.py")
    # We treat any hit as existence of surface
    
    # 7. CALCULATE VARIANCE SCORE
    # Formula: (Blocking * 5) + (TechDebt * 1) + (Cognitive * 5) + (BareExcept * 10) + (TimeoutNone * 10)
    score = (len(hits_blocking) * 5) + (len(hits_debt) * 1) + (len(hits_cognitive) * 5) + (len(bare_excepts) * 10) + (len(hits_timeout) * 10)
    
    print("\n" + "="*40)
    print(f"BLACKGLASS VARIANCE SCORE: {score}")
    print("="*40)
    
    if score > 500:
        print(">>> RESULT: HIGH RISK (HYDROSTATIC LOCK IMMINENT)")
        print(">>> ACTION: BLACKGLASS WATCHTOWER INTERDICTION RECOMMENDED")
    elif score > 100:
        print(">>> RESULT: MODERATE RISK")
    else:
        print(">>> RESULT: STABLE")

if __name__ == "__main__":
    run_audit()
