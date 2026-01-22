# radiance_server.py
# The Mind's Projection: An MCP Server for Blackglass Variance Core

from mcp.server.fastmcp import FastMCP
import os
import json
import httpx
from dotenv import load_dotenv
from supabase import create_client, Client

# --- 1. CONFIGURATION ---
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Must be Service Role to invoke functions/heal
WEST_NODE_URL = os.getenv("WEST_NODE_URL")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("CRITICAL: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")

# Initialize Supabase Client (The connection to Body)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize MCP Server (The Projection)
mcp = FastMCP("Blackglass-Variance-Core")

# --- 2. TOOLS ---

@mcp.tool()
def get_variance_status() -> str:
    """
    OBSERVE the current state of the System (The Mind's Eye).
    Returns 'HYPER-COHERENT' if no active anomalies exist, otherwise 'VARIANCE DETECTED'.
    """
    try:
        response = supabase.table("guardian_anomalies").select("*").eq("status", "ACTIVE").execute()
        active_anomalies = response.data
        
        if not active_anomalies:
            return "HYPER-COHERENT"
        else:
            return f"VARIANCE DETECTED ({len(active_anomalies)} active anomalies)"
    except Exception as e:
        return f"ERROR OBSERVING REALITY: {str(e)}"

@mcp.tool()
def get_compliance_seal() -> str:
    """
    VERIFY the cryptographic proof of the System's state (The Truth's Seal).
    Reads the local compliance_certificate.json from the South Node.
    Standard 1.1 enforcement.
    """
    cert_path = os.path.join(os.path.dirname(__file__), "../coherence-sre/compliance_certificate.json")
    
    try:
        if not os.path.exists(cert_path):
            return "SEAL BREACHED: Certificate not found."
            
        with open(cert_path, "r") as f:
            cert = json.load(f)
        
        # Standard 1.1 Verification
        status = cert.get("compliance_status")
        is_valid = (status == "PASSED")
        
        # Enrich with meta-verification
        cert["_meta_verification"] = "VALID" if is_valid else "INVALID"
        
        return json.dumps(cert, indent=2)
    except Exception as e:
        return f"ERROR VERIFYING SEAL: {str(e)}"

@mcp.tool()
async def invoke_regulation(mode: str = "AUTO") -> str:
    """
    ACT upon the System to resolve variance (The Body's Hand).
    Triggers the West Node's guardian_autoregulate function.
    mode: 'AUTO' (fix it) or 'MANUAL' (log it).
    """
    if not WEST_NODE_URL:
        return "ERROR: West Node URL not configured."

    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "mode": mode,
        "source": "MCP_RADIANCE_SERVER"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(WEST_NODE_URL, json=payload, headers=headers)
            
        if response.status_code == 200:
            return f"REGULATION INVOKED: {response.text}"
        else:
            return f"REGULATION FAILED: HTTP {response.status_code} - {response.text}"
    except Exception as e:
        return f"ERROR INVOKING HEALER: {str(e)}"

if __name__ == "__main__":
    mcp.run()
