"""
Blackglass Continuum - Hugging Face Telemetry Dataset
Converts swarm.log to CSV dataset format for HuggingFace.
"""
from huggingface_hub import HfApi, create_repo, login
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import re
import os

# Load environment variables
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
if HF_TOKEN and HF_TOKEN != "PASTE_YOUR_NEW_TOKEN_HERE":
    login(token=HF_TOKEN)

# Configuration
REPO_ID = "Ardethbay/blackglass-telemetry"
LOG_FILE = "swarm.log"

def parse_log_to_dataframe(log_path):
    """Parse swarm.log into structured DataFrame."""
    if not os.path.exists(log_path):
        print(f"[HF_UPLINK] :: ERROR :: {log_path} not found")
        return None
    
    records = []
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Extract timestamp if present
            timestamp_match = re.match(r'\[(.*?)\]', line)
            timestamp = timestamp_match.group(1) if timestamp_match else None
            
            # Extract log level/type
            level = None
            if '::' in line:
                parts = line.split('::', 1)
                level = parts[0].strip('[]').strip()
                message = parts[1].strip() if len(parts) > 1 else line
            else:
                message = line
            
            records.append({
                'timestamp': timestamp,
                'level': level,
                'message': message,
                'raw_line': line
            })
    
    if not records:
        return None
        
    df = pd.DataFrame(records)
    return df

def upload_telemetry_dataset():
    """Upload swarm logs as CSV dataset to HuggingFace."""
    api = HfApi()
    
    # Create repo if it doesn't exist
    try:
        create_repo(REPO_ID, repo_type="dataset", private=True, exist_ok=True)
        print(f"[HF_UPLINK] :: Repository confirmed: {REPO_ID}")
    except Exception as e:
        print(f"[HF_UPLINK] :: Repo creation warning: {e}")
    
    # Parse logs
    df = parse_log_to_dataframe(LOG_FILE)
    if df is None or df.empty:
        print(f"[HF_UPLINK] :: No data to upload")
        return
    
    # Save as CSV
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"telemetry_{timestamp}.csv"
    df.to_csv(csv_filename, index=False)
    
    try:
        # Upload CSV
        api.upload_file(
            path_or_fileobj=csv_filename,
            path_in_repo=f"data/{csv_filename}",
            repo_id=REPO_ID,
            repo_type="dataset"
        )
        print(f"[HF_UPLINK] :: UPLOADED :: data/{csv_filename} ({len(df)} records)")
        
        # Clean up local CSV
        os.remove(csv_filename)
        
    except Exception as e:
        print(f"[HF_UPLINK] :: UPLOAD FAILED :: {e}")
        if os.path.exists(csv_filename):
            os.remove(csv_filename)

if __name__ == "__main__":
    upload_telemetry_dataset()
