import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

EVIDENCE_PATH = Path("evidence/proposals")
MAX_FILES = 1000
RETENTION_HOURS = 24

def rotate():
    if not EVIDENCE_PATH.exists():
        return {"status": "no_op", "reason": "path_absent"}
    
    files = sorted(EVIDENCE_PATH.glob("*.json"), key=lambda x: x.stat().st_mtime)
    deleted = []
    
    # Time-based culling
    cutoff = time.time() - (RETENTION_HOURS * 3600)
    for f in files:
        if f.stat().st_mtime < cutoff:
            f.unlink()
            deleted.append(f.name)
    
    # Count-based culling (retain newest)
    remaining = sorted(EVIDENCE_PATH.glob("*.json"), key=lambda x: x.stat().st_mtime)
    if len(remaining) > MAX_FILES:
        for old_file in remaining[:-MAX_FILES]:
            old_file.unlink()
            deleted.append(old_file.name)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "deleted_count": len(deleted),
        "retained_count": len(remaining) - (len(remaining) - MAX_FILES if len(remaining) > MAX_FILES else 0),
        "status": "purged" if deleted else "optimal"
    }

if __name__ == "__main__":
    result = rotate()
    print(json.dumps(result))
