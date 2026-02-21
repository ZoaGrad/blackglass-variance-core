
import time
import os
import json
import datetime
import sys
from pathlib import Path
from src.tools.blackglass_sim import run_simulation
from src.tools.blackglass_analyze import analyze_variance
from src.tools.recommend_mitigation import recommend_mitigation

def watch_variance(
    iterations: int = 5, 
    interval_sec: int = 5, 
    iterations: int = 5, 
    interval_sec: int = 5, 
    variance_threshold: float = None, # Defaults to Constitutional Standard
    queue_threshold: int = 50,
    queue_threshold: int = 50,
    cooldown_cycles: int = 3,
    duration_sec: int = 30,
    output_dir: str = None,
    telemetry_mode: str = "mock",
    actuation_mode: str = "noop"
) -> str:
    """
    Enters 'Continuous Mode' to act as a reliability watchtower.
    """
    session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Anchor paths to repo root (parent of src/)
    repo_root = Path(__file__).resolve().parent.parent.parent
    
    # --- CONSTITUTIONAL WIRING (Article I) ---
    if str(repo_root) not in sys.path:
        sys.path.append(str(repo_root))
    from constitution import Constitution
    
    if variance_threshold is None:
        variance_threshold = Constitution.STANDARD.DRIFT_LIMIT_SEMANTIC
        print(f"[WATCH] Constitutional Variance Threshold Set: {variance_threshold}V")
    
    if output_dir:
        evidence_dir = Path(output_dir)
        if not evidence_dir.is_absolute():
            evidence_dir = repo_root / evidence_dir
    else:
        evidence_dir = repo_root / "evidence" / f"watch_{session_id}"
        
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = "watchtower.log"
    print(f"[WATCH] Starting Watchtower Session {session_id}")
    print(f"[WATCH] Rules: Variance > {variance_threshold} OR Queue > {queue_threshold}")
    print(f"[WATCH] Telemetry: {telemetry_mode.upper()} | Actuation: {actuation_mode.upper()}")
    
    # Initialize Adapters
    telemetry_adapter = None
    if telemetry_mode == "mock":
        from src.adapters.telemetry.mock import MockTelemetryAdapter
        # Mock adapter needs run_dir to generate/read artifacts
        # We'll pass the *current cycle's* dir dynamically or set base?
        # The Mock adapter currently wraps analyze_variance which takes a run_dir.
        # Let's instantiate it per cycle or pass None here and handle in loop?
        # Better: The Mock adapter in our impl expects run_dir in constructor.
        # But we change run_dir every cycle.
        # Refactor: We will instantiate inside the loop for Mock, or pass root?
        # Simplest consistent way: Instantiate in loop for Mock.
        pass
    elif telemetry_mode == "air_node":
        from src.adapters.telemetry.air_node import AirNodeTelemetryAdapter
        telemetry_adapter = AirNodeTelemetryAdapter()
        print(f"[WATCH] A.I.R. VaultNode: {telemetry_adapter.base_url}")
        print(f"[WATCH] Incident window: {telemetry_adapter.window_sec}s | Saturation: {telemetry_adapter.saturation_rate} inc/min")
    elif telemetry_mode == "prometheus":
        from src.adapters.telemetry.prometheus import PrometheusTelemetryAdapter
        telemetry_adapter = PrometheusTelemetryAdapter()
        
    actuation_adapter = None
    if actuation_mode == "noop":
        from src.adapters.actuation.noop import NoopActuationAdapter
        actuation_adapter = NoopActuationAdapter()
    elif actuation_mode == "k8s":
        from src.adapters.actuation.k8s import KubernetesActuationAdapter
        actuation_adapter = KubernetesActuationAdapter()

    interdictions = []
    last_interdiction_cycle = -999
    last_interdiction_status = None
    
    # Init Log
    with open(log_file, "a") as f:
        f.write(f"--- Session {session_id} Start ---\n")
    
    # Pre-flight Checklist (Only for Mock mode if it relies on external tools)
    if telemetry_mode == "mock" and not os.getenv("BLACKGLASS_REPO_PATH"):
         print("[WATCH] WARN: BLACKGLASS_REPO_PATH not set. Mock generator will be used.")

    # Lock File Mechanism
    lock_file = Path(".watchtower.lock")
    if lock_file.exists():
        try:
            mtime = lock_file.stat().st_mtime
            age = time.time() - mtime
            if age > 300:
                print(f"[WATCH] Clearing stale lock ({age:.0f}s old).")
                lock_file.unlink()
            else:
                return f"[WATCH] FATAL: Lock active ({age:.0f}s old)."
        except Exception as e:
            return f"[WATCH] FATAL: Lock check failed: {e}"
    
    try:
        lock_file.touch()
        print(f"[WATCH] Lock acquired: {lock_file}")

        for i in range(iterations):
            cycle_idx = i + 1
            cycle_dir = evidence_dir / f"cycle_{cycle_idx}"
            cycle_dir.mkdir(parents=True, exist_ok=True)
            
            # Kill switch
            if os.path.exists(".stop"):
                return "[WATCH] Halted by .stop file."
            
            # Log Rotation
            if Path(log_file).exists() and Path(log_file).stat().st_size > 10 * 1024 * 1024:
                Path(log_file).rename(f"watchtower_{session_id}.log")
                with open(log_file, "w") as f: f.write("--- Log Rotated ---\n")

            timestamp_iso = datetime.datetime.now().isoformat()
            print(f"[WATCH] Cycle {cycle_idx}/{iterations}...")
            
            # Runtime Heartbeat
            with open("watchtower_runtime.json", "w") as f:
                json.dump({
                    "session": session_id,
                    "cycle": cycle_idx,
                    "last_active": timestamp_iso,
                    "status": "RUNNING"
                }, f)
            
            summary_written = False
            decision = "UNKNOWN"
            
            try:
                # 1. Collect & Analyze (via Telemetry Adapter)
                print("    -> Analyzing Variance...")
                
                # Mock Mode Special Handling (needs per-cycle dir)
                current_telemetry = telemetry_adapter
                if telemetry_mode == "mock":
                    from src.adapters.telemetry.mock import MockTelemetryAdapter
                    current_telemetry = MockTelemetryAdapter(run_dir=str(cycle_dir))
                
                try:
                    t_start = time.time()
                    analysis = current_telemetry.get_window(duration_sec=duration_sec)
                    latency = time.time() - t_start
                except Exception as e:
                    print(f"[ERROR] Logic Crash: {e}")
                    analysis = {"status": "crash", "message": str(e)}

                # 3. Fail Closed / Schema Validation
                is_valid = (
                    analysis.get("status") == "ok" and 
                    "variance_detected" in analysis
                )
                
                if not is_valid:
                    # FAIL CLOSED
                    error_msg = f"Analysis Failed: {analysis.get('message', 'Unknown Schema Error')}"
                    print(f"[ERROR] {error_msg}")
                    with open(log_file, "a") as f: f.write(f"[{timestamp_iso}] Cycle={cycle_idx} ERROR {error_msg}\n")
                    
                    decision = "ERROR"
                    with open(cycle_dir / "cycle_summary.json", "w") as f:
                        json.dump({
                            "cycle": cycle_idx,
                            "decision": "ERROR",
                            "reason": error_msg,
                            "input_error": analysis
                        }, f, indent=2)
                    summary_written = True
                    continue 

                # 4. Extract Signals (Typed)
                drift = float(analysis["variance_detected"])
                queue_depth = int(analysis["queue_depth"])
                
                # --- MERCY PROTOCOL CHECK (Article IV) ---
                mercy_status = Constitution.MERCY.evaluate_integrity(latency, drift)
                if "LOCKED" in mercy_status:
                    signal = Constitution.MERCY.declare_distress()
                    # Fail Closed
                    return f"[WATCH] HALTED BY MERCY PROTOCOL: {mercy_status}"
                
                # Write Analysis Artifact
                with open(cycle_dir / "analysis.json", "w") as f:
                    json.dump(analysis, f, indent=2)

                # 5. Evaluate & Assert Causality
                breach_drift = drift > variance_threshold
                breach_queue = queue_depth > queue_threshold
                should_interdict = breach_drift or breach_queue
                
                decision = "NOOP"
                mitigation_plan = {}
                actuation_result = {}
                status_tag = "OK"

                if should_interdict:
                    status_tag = "INTERDICT_DRIFT" if breach_drift else "INTERDICT_QUEUE"
                    decision = "MITIGATE"
                    
                    # Debounce
                    is_repeat = (status_tag == last_interdiction_status) and \
                                (cycle_idx - last_interdiction_cycle <= cooldown_cycles)
                    
                    if is_repeat:
                        decision = "SKIPPED_DEBOUNCE"
                        print(f"    -> [DEBOUNCE] {status_tag} persists (Cycle {last_interdiction_cycle})")
                    else:
                        print(f"    -> [DETECTED] {status_tag} (Drift={drift:.4f}, Queue={queue_depth})")
                        last_interdiction_cycle = cycle_idx
                        last_interdiction_status = status_tag
                        
                        # Generate Mitigation
                        mitigation_plan = recommend_mitigation(analysis)
                        
                        # CAUSALITY ASSERTION
                        if not mitigation_plan:
                             crasher = f"VIOLATION: Thresholds breached but recommend_mitigation returned empty plan!"
                             print(f"[FATAL] {crasher}")
                             raise RuntimeError(crasher)

                        # Persist Plan
                        with open(cycle_dir / "mitigation_plan.json", "w") as f:
                            json.dump(mitigation_plan, f, indent=2)
                            
                        # ACTUATION (via Adapter)
                        print(f"    -> Actuating via {actuation_mode.upper()}...")
                        actuation_result = actuation_adapter.apply(mitigation_plan)
                        
                        with open(cycle_dir / "actuation_result.json", "w") as f:
                            json.dump(actuation_result, f, indent=2)
                            
                        interdictions.append(f"Cycle {cycle_idx}: {status_tag}")

                else:
                     print(f"    -> OK (Drift={drift:.4f}, Queue={queue_depth})")

                # 6. Cycle Summary (The Truth)
                summary = {
                    "cycle": cycle_idx,
                    "timestamp": timestamp_iso,
                    "decision": decision,
                    "signals": {
                        "variance_detected": drift,
                        "queue_depth": queue_depth
                    },
                    "thresholds": {
                        "variance": variance_threshold,
                        "queue": queue_threshold
                    },
                    "artifacts": {
                        "analysis": "analysis.json",
                        "mitigation": "mitigation_plan.json" if decision == "MITIGATE" else None,
                        "actuation": "actuation_result.json" if decision == "MITIGATE" else None
                    }
                }
                with open(cycle_dir / "cycle_summary.json", "w") as f:
                    json.dump(summary, f, indent=2)
                summary_written = True

                # Log Line
                log_line = f"[{timestamp_iso}] Cycle={cycle_idx} Status={status_tag} Decision={decision} Drift={drift:.4f} Queue={queue_depth}"
                with open(log_file, "a") as f: f.write(log_line + "\n")
                
                time.sleep(interval_sec)

            except Exception as e:
                # CATASTROPHIC FAILURE TRAP
                print(f"[FATAL] Cycle {cycle_idx} crashed: {e}")
                import traceback
                traceback.print_exc()
                
                if not summary_written:
                    with open(cycle_dir / "cycle_summary.json", "w") as f:
                        json.dump({
                            "cycle": cycle_idx,
                            "decision": "CRASH",
                            "reason": str(e),
                            "traceback": traceback.format_exc()
                        }, f, indent=2)
                continue # Try next cycle

        return f"Watchtower session complete. {len(interdictions)} interdictions."
        
    finally:
        if lock_file.exists():
            lock_file.unlink()

