import sys
import os
import subprocess
import json
import time
from pathlib import Path

# Goal: Assert the "evidence integrity contract" purely from artifacts.
# Do not rely on internal code imports (black-box test).

def test_watch_cycle_integrity():
    repo_root = Path(__file__).resolve().parent.parent
    
    # 1. Run Watchtower in "Watch Mode" via standard module command
    print("[TEST] Running Watchtower via module execution...")
    cmd = [sys.executable, "-m", "src.agent", "watch"]
    
    # We expect it to run 5 cycles and exit 0
    start = time.time()
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=60
    )
    
    # Assert Exit Code
    if result.returncode != 0:
        print(f"[FAIL] Exit Code {result.returncode}")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        assert result.returncode == 0, "Watchtower crashed"
        
    print(f"[PASS] Execution time: {time.time() - start:.2f}s")

    # 2. Find Evidence Directory
    evidence_root = repo_root / "evidence"
    assert evidence_root.exists(), "Evidence root missing"
    
    # Find the most recent directory starting with "watch_"
    runs = sorted([d for d in evidence_root.iterdir() if d.is_dir() and d.name.startswith("watch_")])
    assert runs, "No watch_ output directories found"
    latest_run = runs[-1]
    print(f"[TEST] Verifying artifacts in: {latest_run.name}")
    
    # 3. Verify Cycle 1
    cycle_1 = latest_run / "cycle_1"
    assert cycle_1.exists(), "Cycle 1 directory missing"
    
    # A. Cycle Summary (The Truth)
    summary_path = cycle_1 / "cycle_summary.json"
    assert summary_path.exists(), "cycle_summary.json missing"
    
    with open(summary_path) as f:
        summary = json.load(f)
        
    assert "decision" in summary, "Summary missing 'decision'"
    assert summary["decision"] in ["MITIGATE", "NOOP", "ERROR", "SKIPPED_DEBOUNCE"], f"Invalid decision: {summary['decision']}"
    assert "signals" in summary, "Summary checks signals"
    
    # B. Analysis (The Signal)
    analysis_path = cycle_1 / "analysis.json"
    assert analysis_path.exists(), "analysis.json missing"
    
    with open(analysis_path) as f:
        analysis = json.load(f)
    
    assert analysis["schema_version"] == "watchtower.analysis.v1", "Invalid Schema V1"
    assert "variance_detected" in analysis
    # Source can be 'engine' or 'python_fallback' (mock)
    assert analysis.get("source") in ["engine", "python_fallback"], f"Unknown source: {analysis.get('source')}"

    # C. Mitigation (The Action) - Conditional
    if summary["decision"] == "MITIGATE":
        mitigation_path = cycle_1 / "mitigation_plan.json"
        assert mitigation_path.exists(), "Decision was MITIGATE but mitigation_plan.json is missing"
        with open(mitigation_path) as f:
            plan = json.load(f)
        assert plan["trigger"]["status"] == "INTERDICT"
        assert len(plan["recommended_actions"]) > 0

    print("[PASS] Evidence Integrity Contract Verified")

def test_output_dir_override():
    print("\n[TEST] Verifying --output-dir override...")
    repo_root = Path(__file__).resolve().parent.parent
    output_target = repo_root / "runs" / "test_override"
    
    # Clean up previous run if exists
    if output_target.exists():
        import shutil
        shutil.rmtree(output_target)
        
    cmd = [
        sys.executable, "-m", "src.agent", "watch",
        "--cycles", "1",
        "--output-dir", str(output_target)
    ]
    
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, f"Override run failed: {result.stderr}"
    
    # Verify directory created
    # Code behavior: evidence_dir = Path(output_dir). It does NOT append session_id if override is set.
    # So we expect cycle_1 directly inside the output_target.
    
    assert output_target.exists(), "Output directory not created"
    assert (output_target / "cycle_1").exists(), "Cycle 1 not found in custom output dir"
    print("[PASS] --output-dir flag verified")

    assert output_target.exists(), "Output directory not created"
    assert (output_target / "cycle_1").exists(), "Cycle 1 not found in custom output dir"
    print("[PASS] --output-dir flag verified")

def test_adapter_flags():
    print("\n[TEST] Verifying --telemetry/--actuation flags...")
    repo_root = Path(__file__).resolve().parent.parent
    output_target = repo_root / "runs" / "test_adapters"
    
    if output_target.exists():
        import shutil
        shutil.rmtree(output_target)
        
    cmd = [
        sys.executable, "-m", "src.agent", "watch",
        "--cycles", "2", # Run 2 cycles to ensure we hit the mock drift
        "--output-dir", str(output_target),
        "--telemetry", "mock",
        "--actuation", "noop"
    ]
    
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, f"Adapter run failed: {result.stderr}"
    
    # Check if we got a mitigation (which is expected with currently high mock drift)
    # If so, check for actuation_result.json
    found_actuation = False
    for cycle_dir in output_target.glob("cycle_*"):
        summary_path = cycle_dir / "cycle_summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                s = json.load(f)
            if s["decision"] == "MITIGATE":
                act_res = cycle_dir / "actuation_result.json"
                assert act_res.exists(), f"Mitigation in {cycle_dir.name} but no actuation_result.json"
                with open(act_res) as f:
                    act = json.load(f)
                assert act["status"] == "noop", "Actuation status mismatch"
                found_actuation = True
    
    if found_actuation:
        print("[PASS] Adapter output (actuation_result.json) verified")
    else:
        print("[WARN] No mitigation triggered, so actuation not tested (but run valid)")

if __name__ == "__main__":
    try:
        test_watch_cycle_integrity()
        test_output_dir_override()
        test_adapter_flags()
        print("\n[OK] ALL TESTS PASSED")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] FAIL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        sys.exit(1)
