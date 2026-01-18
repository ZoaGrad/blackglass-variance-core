import os
import subprocess
import time
from dotenv import load_dotenv

load_dotenv()
BLACKGLASS_PATH = os.getenv("BLACKGLASS_REPO_PATH")

def run_simulation(run_dir="runs/run_latest", duration_sec=30, drift=0.0, seed=None, threshold=None, interval=None, allow_long=False):
    if not BLACKGLASS_PATH:
        return {"status": "error", "message": "BLACKGLASS_REPO_PATH not set in .env"}

    run_dir = os.path.abspath(run_dir) # Ensure absolute path for cross-repo consistency
    duration_sec = int(duration_sec)
    if not allow_long:
        duration_sec = min(duration_sec, 120)

    exe_path = os.path.join(BLACKGLASS_PATH, "simulate.exe")
    if not os.path.exists(exe_path):
        return {"status": "error", "message": f"simulate.exe not found at {exe_path}"}

    os.makedirs(run_dir, exist_ok=True)
    report_path = os.path.join(run_dir, "report.html")

    cmd = [exe_path, "-out", report_path, "-duration", str(duration_sec)]

    # optional supported flags (only if provided)
    if drift is not None:
        cmd += ["-drift", str(drift)]
    if seed is not None:
        cmd += ["-seed", str(int(seed))]
    if threshold is not None:
        cmd += ["-threshold", str(threshold)]
    if interval is not None:
        cmd += ["-interval", str(interval)]

    start = time.time()
    try:
        # Timeout safety: duration + Buffer
        result = subprocess.run(
            cmd,
            cwd=BLACKGLASS_PATH,
            capture_output=True,
            text=True,
            timeout=duration_sec + 10
        )
    except Exception as e:
        return {"status": "error", "message": str(e)}

    elapsed = round(time.time() - start, 2)

    if result.returncode != 0:
        return {"status": "error", "stdout": result.stdout, "stderr": result.stderr}

    if not os.path.exists(report_path):
        return {"status": "error", "message": f"simulate.exe finished but report not found: {report_path}"}

    return {
        "status": "ok",
        "run_dir": run_dir,
        "report_path": report_path,
        "elapsed_sec": elapsed,
        "stdout": result.stdout.strip()
    }
