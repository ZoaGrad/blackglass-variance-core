
import time
import os
import json
import datetime
from pathlib import Path
from src.tools.blackglass_sim import run_simulation
from src.tools.blackglass_analyze import analyze_variance
from src.tools.recommend_mitigation import recommend_mitigation

def watch_variance(
    iterations: int = 5, 
    interval_sec: int = 5, 
    variance_threshold: float = 0.05, 
    queue_threshold: int = 10,
    cooldown_cycles: int = 3
) -> str:
    """
    Enters 'Continuous Mode' to act as a reliability watchtower.
    
    Args:
        iterations: Number of cycles to run.
        interval_sec: Seconds to sleep between cycles.
        variance_threshold: Drift score above which to trigger interdiction.
        queue_threshold: Queue depth above which to trigger interdiction.
        cooldown_cycles: Cycles to wait before re-emitting a recommendation for the same issue.
        
    Returns:
        A human-readable summary of the watch session.
    """
    
    log_file = "watchtower.log"
    session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    evidence_dir = Path("evidence") / f"watch_{session_id}"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[WATCH] Starting Watchtower Session {session_id}")
    print(f"[WATCH] Rules: Variance > {variance_threshold} OR Queue > {queue_threshold}")
    
    interdictions = []
    last_interdiction_cycle = -999
    last_interdiction_status = None
    
    with open(log_file, "a") as f:
        f.write(f"--- Session {session_id} Start ---\n")
    
    for i in range(iterations):
        # Kill switch
        if os.path.exists(".stop"):
            msg = "[WATCH] .stop file detected. Halted."
            print(msg)
            return msg

        timestamp = datetime.datetime.now().isoformat()
        print(f"[WATCH] Cycle {i+1}/{iterations}...")
        
        # 1. Collect Artifacts (Simulate)
        # Note: In a real loop we might just scrape metrics, but here we run the sim
        report_path = run_simulation(scenarios=["watchtower_probe"])
        
        # 2. Analyze Variance
        analysis = analyze_variance(report_path)
        drift = analysis.get("variance_detected", 0.0)
        queue_depth = analysis.get("queue_depth", 0)
        
        # 3. Evaluate Thresholds
        status = "OK"
        if drift > variance_threshold:
            status = "INTERDICT_DRIFT"
        elif queue_depth > queue_threshold:
            status = "INTERDICT_QUEUE"
            
        log_entry = f"[{timestamp}] Cycle={i+1} Status={status} Drift={drift} Queue={queue_depth}"
        
        # 4. Durable Logging
        with open(log_file, "a") as f:
            f.write(log_entry + "\n")
            
        if status != "OK":
            # Debounce Logic
            is_repeat = (status == last_interdiction_status) and \
                        ((i + 1) - last_interdiction_cycle <= cooldown_cycles)
            
            if is_repeat:
                msg = f"    -> REPEAT DETECTED (Cooldown Active - Cycle {last_interdiction_cycle})"
                with open(log_file, "a") as f:
                    f.write(msg + "\n")
                print(f"[WARN] {status} PERSISTS (Debounced)")
                
            else:
                print(f"[WARN] {status} DETECTED! (Drift={drift}, Queue={queue_depth})")
                
                # Generate Mitigation Plan
                plan = recommend_mitigation(analysis)
                if plan:
                    # Save full plan
                    plan_file = evidence_dir / f"mitigation_cycle_{i+1}.json"
                    with open(plan_file, "w") as pf:
                        json.dump(plan, pf, indent=2)
                    
                    # Log summary line
                    top_action = plan["recommended_actions"][0]["action"] if plan["recommended_actions"] else "investigate"
                    rec_log = f"    -> RECOMMENDED: {top_action}"
                    with open(log_file, "a") as f:
                        f.write(rec_log + "\n")
                    print(rec_log)
                
                last_interdiction_cycle = i + 1
                last_interdiction_status = status

            interdictions.append(log_entry)
        
        time.sleep(interval_sec)
        
    summary = f"Watchtower complete. {iterations} cycles. {len(interdictions)} interdictions."
    if interdictions:
        summary += "\nFindings:\n" + "\n".join(interdictions)
        
    return summary
