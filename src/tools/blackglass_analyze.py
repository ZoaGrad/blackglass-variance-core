import os
import sys
import json
import subprocess
import datetime
import math
from dotenv import load_dotenv

load_dotenv()
BLACKGLASS_PATH = os.getenv("BLACKGLASS_REPO_PATH")


import random
import time

def _generate_mock_artifacts(run_dir: str, duration_sec: int = 30):
    """
    Generates synthetic metrics.json and checkout.log for standalone verification.
    Simulates a saturation event (queue > 50).
    """
    print("[WARN] Using Mock Generator (Standalone Mode)")
    
    metrics = []
    start_time = time.time()
    for i in range(10):
        # Create a trend: Queue rises from 10 to 60
        q = 10 + (i * 6) + random.randint(-2, 2)
        q = max(0, q)
        
        # Latency correlates with queue
        lat = 20 + (q * 2) + random.randint(-10, 10)
        
        metrics.append({
            "timestamp": start_time + (i * 3),
            "queue_depth": q,
            "latency_ms": lat,
            "availability": 100 if q < 50 else 95
        })
        
    metrics_path = os.path.join(run_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
        
    # Mock Log
    os.makedirs(os.path.join(run_dir, "services"), exist_ok=True)
    log_path = os.path.join(run_dir, "services", "checkout.log")
    with open(log_path, "w") as f:
        f.write("INFO: CheckoutService: Processing...\n")
        f.write("WARN: Queue depth high!\n")
        
    return {"status": "ok", "stdout": "Mock artifacts generated."}

def _run_python_generator(run_dir: str, duration_sec: int = 900, fault_time: str = "14:00"):
    """
    Runs blackglass-variance-core/blackglass/simulate.py to generate artifacts.
    Falls back to mock generator if script is missing.
    """
    sim_py = os.path.join(BLACKGLASS_PATH, "blackglass", "simulate.py") if BLACKGLASS_PATH else ""
    
    if not sim_py or not os.path.exists(sim_py):
        return _generate_mock_artifacts(run_dir, duration_sec)

    cmd = [
        sys.executable,
        "-c",
        (
            "import sys; "
            f"sys.path.append(r'''{BLACKGLASS_PATH}'''); "
            "from blackglass.simulate import generate_drift; "
            f"generate_drift(r'''{run_dir}''', duration_sec={int(duration_sec)}, fault_time=r'''{fault_time}'''); "
            "print('OK')"
        )
    ]

    result = subprocess.run(
        cmd,
        cwd=BLACKGLASS_PATH,
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode != 0:
        return {"status": "error", "stdout": result.stdout, "stderr": result.stderr}

    return {"status": "ok", "stdout": result.stdout.strip()}


def _find_engine_entrypoint():
    """
    Try common locations for the RLM engine entrypoint inside blackglass-variance-core.
    Adjust if your repo differs.
    """
    if not BLACKGLASS_PATH:
        return None
        
    candidates = [
        os.path.join(BLACKGLASS_PATH, "blackglass", "rlm", "run.py"),
        os.path.join(BLACKGLASS_PATH, "blackglass", "rlm", "engine.py"),
        os.path.join(BLACKGLASS_PATH, "scripts", "demo_agent.py"),
        os.path.join(BLACKGLASS_PATH, "scripts", "demo_agent.pyw"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _calculate_fallback_variance(metrics: list) -> dict:
    """
    Deterministic drift calculation from metrics.
    Returns: { "drift": float, "details": dict }
    Logic: 
      - Latency Standard Deviation (Dispersion)
      - Queue Slope (Trend)
    """
    if not metrics:
        return {"drift": 0.0, "details": {}}
        
    latencies = [m.get("latency_ms", 0) for m in metrics]
    queues = [m.get("queue_depth", 0) for m in metrics]
    timestamps = [m.get("timestamp", 0) for m in metrics] # Assuming relative or absolute TS exists, or index

    # 1. Dispersion: Standard Deviation of Latency
    n = len(latencies)
    if n < 2:
        return {"drift": 0.0, "details": {"reason": "insufficient_data"}}
        
    mean_lat = sum(latencies) / n
    variance_lat = sum((x - mean_lat) ** 2 for x in latencies) / n
    std_lat = math.sqrt(variance_lat)
    
    # Normalize dispersion: Assume > 50ms stddev is "high" (drift=1.0)
    norm_dispersion = min(std_lat / 50.0, 1.0)

    # 2. Trend: Slope of Queue Depth
    # Simple linear regression slope for queue depth over time (steps)
    # x = step index, y = queue depth
    # slope = (n * sum(xy) - sum(x)*sum(y)) / (n * sum(x^2) - sum(x)^2)
    # Using step index is robust enough for fallback.
    
    sum_x = sum(range(n))
    sum_y = sum(queues)
    sum_xy = sum(i * q for i, q in enumerate(queues))
    sum_xx = sum(i * i for i in range(n))
    
    denom = (n * sum_xx - sum_x * sum_x)
    if denom == 0:
        slope = 0
    else:
        slope = (n * sum_xy - sum_x * sum_y) / denom
        
    # Normalize trend: > 1.0 item/step increase is "high"
    norm_trend = min(max(slope, 0) / 1.0, 1.0) # Only responsive to increasing queues
    
    # Combined Drift Score
    # Weight: 60% dispersion, 40% trend
    drift_score = (0.6 * norm_dispersion) + (0.4 * norm_trend)
    
    return {
        "drift": float(drift_score),
        "details": {
            "latency_std_ms": float(std_lat),
            "queue_slope_per_step": float(slope),
            "norm_dispersion": float(norm_dispersion),
            "norm_trend": float(norm_trend)
        }
    }


def analyze_variance(run_dir="runs/run_latest", duration_sec=30, fault_time="14:00"):
    """
    Tool: analyze_variance
    
    Strict Schema Return (v1):
    {
        "status": "ok",
        "schema_version": "watchtower.analysis.v1",
        "timestamp_utc": "...",
        "variance_detected": 0.0 - 1.0,
        "queue_depth": int,
        "latency_ms": float, 
        "features": { ... },
        "source": "engine|python_fallback",
        "raw_artifacts": { ... }
    }
    """
    start_ts_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    if not BLACKGLASS_PATH:
        return {"status": "error", "message": "BLACKGLASS_REPO_PATH not set in .env"}

    run_dir = os.path.abspath(run_dir)
    os.makedirs(run_dir, exist_ok=True)

    # 1) Generate machine-readable artifacts (Simulation)
    gen = _run_python_generator(run_dir=run_dir, duration_sec=int(duration_sec), fault_time=fault_time)
    if gen.get("status") != "ok":
        return {"status": "error", "stage": "python_generate", **gen}

    metrics_path = os.path.join(run_dir, "metrics.json")
    log_path = os.path.join(run_dir, "services", "checkout.log")
    engine_output_path = os.path.join(run_dir, "engine_output.txt") # Persist raw engine output

    if not os.path.exists(metrics_path):
        return {"status": "error", "message": f"metrics.json not found at {metrics_path}"}
    
    # Load metrics for fallback/summary
    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"Invalid metrics.json: {e}"}

    # Basic stats
    max_q = max((m.get("queue_depth", 0) for m in metrics), default=0)
    max_lat = max((m.get("latency_ms", 0) for m in metrics), default=0.0)

    # 2) Run Engine (if available) - Attempt execution but fail safely to pure Python
    engine = _find_engine_entrypoint()
    engine_ran = False
    engine_stdout = ""
    engine_error = None
    
    if engine:
        cmd = [
            sys.executable,
            engine,
            "--root", run_dir,
            "--objective", "Analyze metrics and logs. Return structured drift analysis."
        ]
        
        env = os.environ.copy()
        current_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{BLACKGLASS_PATH}{os.pathsep}{current_pythonpath}"

        try:
            result = subprocess.run(
                cmd, cwd=BLACKGLASS_PATH, capture_output=True, text=True, timeout=180, env=env
            )
            engine_stdout = result.stdout
            engine_ran = (result.returncode == 0)
            
            # Persist raw output
            with open(engine_output_path, "w", encoding="utf-8") as f:
                f.write(f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}")
                
        except Exception as e:
            engine_error = str(e)
            with open(engine_output_path, "w", encoding="utf-8") as f:
                f.write(f"EXECUTION_ERROR: {e}")

    # 3) Determine output source (Engine vs Fallback)
    # TODO: If engine returns strict JSON in future, parse it here. 
    # For now, we assume engine output is unstructured text, so we rely on Python Fallback 
    # for the canonical 'variance_detected' signal to ensure causality.
    
    fallback = _calculate_fallback_variance(metrics)
    variance_score = fallback["drift"]
    variance_details = fallback["details"]
    source = "python_fallback"
    
    # If engine ran, we could try to extract drift from it, but per "Fail Closed/Structured",
    # unless we trust the engine's JSON output, we stick to our calculated metric for safety.
    # In a full production env, we'd prioritize engine JSON if valid.
    
    return {
        "status": "ok",
        "schema_version": "watchtower.analysis.v1",
        "timestamp_utc": start_ts_utc,
        "variance_detected": round(variance_score, 4),
        "queue_depth": int(max_q),
        "latency_ms": float(max_lat),
        "features": {
            "latency_std_ms": variance_details.get("latency_std_ms", 0.0),
            "queue_slope_per_step": variance_details.get("queue_slope_per_step", 0.0),
            "norm_dispersion": variance_details.get("norm_dispersion", 0.0),
            "norm_trend": variance_details.get("norm_trend", 0.0)
        },
        "source": source,
        "raw_artifacts": {
            "metrics": metrics_path,
            "engine_output": engine_output_path if engine else None,
            "engine_ran": engine_ran,
            "engine_error": engine_error
        }
    }

