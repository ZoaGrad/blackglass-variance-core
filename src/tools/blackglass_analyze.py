import os
import sys
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()
BLACKGLASS_PATH = os.getenv("BLACKGLASS_REPO_PATH")


def _run_python_generator(run_dir: str, duration_sec: int = 900, fault_time: str = "14:00"):
    """
    Runs blackglass-variance-core/blackglass/simulate.py to generate:
      - metrics.json
      - services/checkout.log
    into the provided run_dir.
    """
    sim_py = os.path.join(BLACKGLASS_PATH, "blackglass", "simulate.py")
    if not os.path.exists(sim_py):
        return {"status": "error", "message": f"Python generator not found: {sim_py}"}

    # IMPORTANT: This assumes blackglass/simulate.py exposes a callable generate_drift().
    # If it is CLI-only, we can adjust to call it with args instead.
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


def analyze_variance(run_dir="runs/run_latest", duration_sec=30, fault_time="14:00"):
    """
    Tool: analyze_variance

    Hybrid mode:
      1) Ensure raw artifacts exist (metrics.json + services/*.log) by running the Python generator.
      2) Invoke the Blackglass RLM/engine to analyze evidence in run_dir.
      3) Return structured results and file paths.
    """
    if not BLACKGLASS_PATH:
        return {"status": "error", "message": "BLACKGLASS_REPO_PATH not set in .env"}

    run_dir = os.path.abspath(run_dir) # Ensure absolute path for cross-repo consistency
    os.makedirs(run_dir, exist_ok=True)

    # 1) Generate machine-readable artifacts
    gen = _run_python_generator(run_dir=run_dir, duration_sec=int(duration_sec), fault_time=fault_time)
    if gen.get("status") != "ok":
        return {"status": "error", "stage": "python_generate", **gen}

    metrics_path = os.path.join(run_dir, "metrics.json")
    log_path = os.path.join(run_dir, "services", "checkout.log")

    if not os.path.exists(metrics_path):
        return {"status": "error", "message": f"metrics.json not found at {metrics_path}"}
    if not os.path.exists(log_path):
        return {"status": "error", "message": f"checkout.log not found at {log_path}"}

    # 2) Run the RLM engine if available
    engine = _find_engine_entrypoint()
    if not engine:
        # Fallback: return a minimal evidence summary (still useful)
        # (Your watch_variance tool can consume this and decide interdiction)
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)

        max_q = max(m.get("queue_depth", 0) for m in metrics)
        max_lat = max(m.get("latency_ms", 0) for m in metrics)
        min_av = min(m.get("availability", 100) for m in metrics)

        return {
            "status": "ok",
            "mode": "fallback_no_engine",
            "run_dir": run_dir,
            "artifacts": {"metrics": metrics_path, "log": log_path},
            "summary": {
                "max_queue_depth": max_q,
                "max_latency_ms": max_lat,
                "min_availability": min_av
            }
        }

    # If engine.py exists: try calling it with common args
    cmd = [
        sys.executable,
        engine,
        "--root", run_dir,
        "--objective", "Analyze metrics and logs. Detect drift, prediction window, and interdiction opportunities."
    ]

    env = os.environ.copy()
    # Canonical PYTHONPATH injection
    # Prepend to ensure no masking by other paths
    current_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{BLACKGLASS_PATH}{os.pathsep}{current_pythonpath}"

    try:
        result = subprocess.run(
            cmd,
            cwd=BLACKGLASS_PATH,
            capture_output=True,
            text=True,
            timeout=180,
            env=env
        )
    except Exception as e:
         return {
            "status": "error",
            "stage": "engine_execution",
            "message": str(e)
        }

    # Check for Rate Limit / Quota errors in output or exit code
    stdout_lower = result.stdout.lower()
    stderr_lower = result.stderr.lower()
    is_rate_limited = "429" in stderr_lower or "resource_exhausted" in stderr_lower or "quota" in stderr_lower

    if result.returncode != 0:
        if is_rate_limited:
            # Fallback logic: Engine skipped due to rate limit, rely on metrics
            with open(metrics_path, "r", encoding="utf-8") as f:
                metrics = json.load(f)
            
            # Simple aggregation
            max_q = max((m.get("queue_depth", 0) for m in metrics), default=0)
            max_lat = max((m.get("latency_ms", 0) for m in metrics), default=0)
            min_av = min((m.get("availability", 100) for m in metrics), default=100)
            
            return {
                "status": "ok",
                "mode": "degraded_engine", # Signal to watchtower
                "note": "ENGINE_SKIPPED_RATE_LIMIT",
                "run_dir": run_dir,
                "artifacts": {"metrics": metrics_path, "log": log_path},
                "summary": {
                    "max_queue_depth": max_q,
                    "max_latency_ms": max_lat,
                    "min_availability": min_av
                }
            }

        return {
            "status": "error",
            "stage": "engine_run",
            "engine": engine,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    return {
        "status": "ok",
        "mode": "engine",
        "run_dir": run_dir,
        "engine": engine,
        "artifacts": {"metrics": metrics_path, "log": log_path},
        "engine_output": result.stdout.strip()
    }
