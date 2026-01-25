import os
import datetime
import json

def audit():
    print("--- BLACKGLASS SOVEREIGN AUDIT (NIGHT 1) ---")
    
    # 1. Check Repositories
    repos = ["blackglass-variance-core", "Vector_Null", "blackglass-shard-alpha", "coherence-sre"]
    for repo in repos:
        path = f"c:/Users/colem/Code/{repo}"
        if os.path.exists(path):
            print(f"[OK] {repo} located.")
        else:
            print(f"[FAIL] {repo} MISSING.")

    # 2. Check Vigil Status
    last_report = "c:/Users/colem/Code/blackglass-variance-core/VARIANCE_REPORT.md"
    if os.path.exists(last_report):
        mtime = os.path.getmtime(last_report)
        last_mod = datetime.datetime.fromtimestamp(mtime)
        delta = datetime.datetime.now() - last_mod
        print(f"[STATUS] Last Variance Report: {last_mod} ({delta.total_seconds()/3600:.2f} hours ago)")
        if delta.total_seconds() > 1:
            print("[WARNING] Vigil appears STALLED.")
    
    # 3. Check Shard Alpha Integrity
    shard_results = "c:/Users/colem/Code/blackglass-shard-alpha/results.json"
    if os.path.exists(shard_results):
        with open(shard_results, "r") as f:
            data = json.load(f)
            print(f"[SHARD] Final Equity: ${data['final_equity']:.2f}")
            print(f"[SHARD] Locked Status: {data.get('compliance_logs', [])[-1].get('status') if data.get('compliance_logs') else 'UNKNOWN'}")

    print("--- AUDIT COMPLETE ---")

if __name__ == "__main__":
    audit()
