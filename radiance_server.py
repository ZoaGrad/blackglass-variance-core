# radiance_server.py
# The Mind's Projection: An MCP Server for Blackglass Variance Core

from mcp.server.fastmcp import FastMCP
import os
import json
import httpx
import uuid
import datetime
import time
from dotenv import load_dotenv
from supabase import create_client, Client

# --- 1. CONFIGURATION ---
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Must be Service Role to invoke functions/heal
WEST_NODE_URL = os.getenv("WEST_NODE_URL")

# Path to Evidence Vault
EVIDENCE_VAULT = os.path.abspath(os.path.join(os.path.dirname(__file__), "evidence/proposals"))

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("CRITICAL: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")

# Initialize Supabase Client (The connection to Body)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize MCP Server (The Projection)
mcp = FastMCP("Blackglass-Variance-Core")

# Ensure Vault Exists
os.makedirs(EVIDENCE_VAULT, exist_ok=True)

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

@mcp.tool()
def propose_directive(type: str, content: str, justification: str, urgency: str = "NORMAL") -> str:
    """
    PROPOSE a new Directive to the System (The Ballot Box).
    Stores the proposal in the Evidence Vault for review.
    type: "MANIFEST_UPDATE", "CONSTITUTIONAL_AMENDMENT", "PARAMETER_TUNE"
    """
    ALLOWED_TYPES = ["MANIFEST_UPDATE", "CONSTITUTIONAL_AMENDMENT", "PARAMETER_TUNE", "SYSTEM_OBSERVATION"]
    
    if type not in ALLOWED_TYPES:
        return f"REJECTED: Invalid directive type. Allowed: {ALLOWED_TYPES}"
        
    prop_id = f"prop-{uuid.uuid4()}"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    proposal = {
        "id": prop_id,
        "timestamp": timestamp,
        "status": "PROPOSED",
        "author": "EXTERNAL_AGENT",
        "type": type,
        "content": content,
        "justification": justification,
        "urgency": urgency
    }
    
    filepath = os.path.join(EVIDENCE_VAULT, f"{prop_id}.json")
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(proposal, f, indent=2)
        return json.dumps({ "proposal_id": prop_id, "status": "QUEUED_FOR_REVIEW" })
    except Exception as e:
        return f"ERROR WRITING PROPOSAL: {str(e)}"

@mcp.tool()
async def inspect_system_file(relative_path: str) -> str:
    """
    Read the content of a system file to verify configuration or logic.
    Allowed paths: ../blackglass-variance-core/, ../coherence-sre/, ../mythotech-spiralos/, ../evidence/
    """
    # Security: Prevent traversing above project root
    if ".." in relative_path and not relative_path.startswith(".."):
        return "ACCESS DENIED: Invalid traversal."
    
    # Normalization for windows/linux safety
    safe_roots = ["blackglass-variance-core", "coherence-sre", "mythotech-spiralos", "evidence", "vector_null"]
    
    # Simple check: Is the path pointing to a safe zone?
    # (In a real production env, we would use os.path.abspath checks)
    is_safe = any(root in relative_path for root in safe_roots)
    
    if not is_safe:
        return f"ACCESS DENIED: Path '{relative_path}' is outside Sovereign Territory."

    try:
        # Adjust for the fact that radiance_server is inside blackglass-variance-core
        if not os.path.exists(relative_path):
            return "ERROR: File not found."
            
        with open(relative_path, "r", encoding="utf-8") as f:
            content = f.read()
            return content
    except Exception as e:
        return f"ERROR: Could not read file. {str(e)}"

from constitution import Constitution, SovereignState

@mcp.tool()
async def perform_self_audit(audit_scope: str = "FULL") -> dict:
    """
    Perform a rigorous self-health check against the CONSTITUTION.
    Thresholds: Defined in constitution.py (0.05V Standard).
    """
    start_time = time.time()
    report = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "scope": audit_scope,
        "components": {},
        "health_score": 100,
        "findings": [],
        "sovereign_state": "ACTIVE"
    }

    # 1. READ RUNTIME CONFIG (The Mutable State)
    config_path = os.path.join(os.path.dirname(__file__), "runtime_config.json")
    latency_delay = 0.1 # Default 100ms
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                ms = config.get("audit_logic", {}).get("latency_simulator_ms", 100)
                latency_delay = ms / 1000.0
        except:
            pass # Fallback to default if config is locked/corrupt

    # 2. RIGOROUS TIMING (The 0.05s Standard)
    # We measure overhead first to fail fast if we are cognitively slow.
    time.sleep(latency_delay) # DYNAMIC LATENCY based on Config
    duration = time.time() - start_time
    report["audit_duration_seconds"] = duration
    
    # 2. CONSTITUTIONAL CHECK: The Mercy Protocol
    # "If the System exceeds the Critical Failure Threshold... Declare LOCKED."
    integrity_status = Constitution.MERCY.evaluate_integrity(latency=duration, variance_score=0.0)
    
    if integrity_status.startswith("LOCKED"):
        Constitution.MERCY.declare_distress()
        report["sovereign_state"] = "LOCKED"
        report["health_score"] = 0
        report["findings"].append(f"MERCY PROTOCOL ENGAGED: {integrity_status}")
        report["findings"].append("ΔΩ_SEQ_BREAK: System has surrendered kinetic control.")
        return report # ABORT AUDIT - The System is Broken

    # 3. KINETIC AUDIT: West Node (The Body)
    # We query the Shard API directly. To observe is to change.
    
    west_status = "UNKNOWN"
    shard_drawdown = 0.0
    shard_equity = 0.0
    
    if WEST_NODE_URL:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{WEST_NODE_URL}/status")
                if resp.status_code == 200:
                    data = resp.json()
                    west_status = data.get("status", "UNKNOWN")
                    shard_drawdown = data.get("drawdown_pct", 0.0)
                    shard_equity = data.get("equity", 0.0)
                    report["components"]["WEST"] = west_status
                    report["fiscal_state"] = {
                        "equity": shard_equity,
                        "drawdown": shard_drawdown
                    }
                else:
                    report["components"]["WEST"] = "UNREACHABLE"
                    report["health_score"] -= 10
                    report["findings"].append(f"West Node API Error: {resp.status_code}")
        except Exception as e:
            report["components"]["WEST"] = "UNREACHABLE"
            report["health_score"] -= 10
            report["findings"].append(f"West Node Connection Failed: {str(e)}")
    else:
         report["components"]["WEST"] = "MISSING_CONFIG"
         report["findings"].append("West Node URL not configured.")
         report["health_score"] -= 10

    # 4. CONSTITUTIONAL CHECK: Fiscal Drift (Survival)
    # "If the System exceeds the Fiscal Threshold... IT MUST STOP."
    
    if shard_drawdown > Constitution.STANDARD.DRIFT_LIMIT_FISCAL:
         Constitution.MERCY.declare_distress()
         
         # ACTIVE INTERDICTION (The Kill Switch)
         if WEST_NODE_URL:
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    pkg = {
                        "reason": f"Sovereign Interdiction: Drawdown {shard_drawdown:.2%} > Limit",
                        "source": "RADIANCE_CORE"
                    }
                    await client.post(f"{WEST_NODE_URL}/interdict", json=pkg)
                    report["findings"].append("⚡ KINETIC INTERDICTION EXECUTED: Shard Halted.")
            except:
                report["findings"].append("CRITICAL: Failed to execute Kinetic Interdiction.")
         
         report["sovereign_state"] = "LOCKED"
         report["health_score"] = 0
         report["findings"].append(f"CRITICAL FISCAL FAILURE: Drawdown {shard_drawdown:.2%} > Limit")
         return report

    # 5. CONSTITUTIONAL CHECK: The 0.05V Standard (Drift)
    if duration > Constitution.STANDARD.DRIFT_LIMIT_TEMPORAL:
        report["health_score"] -= 5
        report["findings"].append(f"TEMPORAL DRIFT DETECTED: {duration:.4f}s > {Constitution.STANDARD.DRIFT_LIMIT_TEMPORAL}s")

    # 6. CHECK EAST NODE (The Mind) - Self-Check
    report["components"]["EAST"] = "ONLINE"
    
    # 7. CHECK SOUTH NODE (The Truth) - Seal Check
    # (Simplified for now to avoid file path complexity in this refactor)
    report["components"]["SOUTH"] = "ASSUMED_VALID" 

    # 8. CHECK NORTH NODE (The Will) - Directive Engine
    if os.path.exists(EVIDENCE_VAULT):
            report["components"]["NORTH"] = "READY"
    else:
            report["components"]["NORTH"] = "DORMANT"
            report["findings"].append("North Node Evidence Vault missing.")
            report["health_score"] -= 10
    
    return report

@mcp.tool()
async def propose_self_optimization() -> dict:
    """
    Analyze audit findings and propose a Directive to fix them.
    """
    # 1. Run the Audit
    audit = await perform_self_audit("FULL")
    
    if audit["health_score"] >= 98:
        return {"status": "NO_ACTION", "message": "System is too healthy to optimize."}
    
    proposals = []
    
    for finding in audit["findings"]:
        f_upper = finding.upper()
        if "TEMPORAL DRIFT" in f_upper or "LATENCY" in f_upper:
            # Construct a Directive Proposal
            prop_id = f"prop-{str(uuid.uuid4())[:8]}"
            content = {
                "directive_type": "PARAMETER_TUNE",
                "risk_level": Constitution.REGENCY.RISK_LOW,
                "target": "radiance_server.py",
                "action": "OPTIMIZE_AUDIT_LOGIC",
                "parameters": {"caching": "ENABLED"}
            }
            
            # 3. Write to Evidence Vault (The Ballot Box)
            filename = os.path.join(EVIDENCE_VAULT, f"{prop_id}.json")
            proposal_data = {
                "id": prop_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "status": "PROPOSED",
                "author": "DIAMOND_REFLEXIVE_CORE",
                "type": "PARAMETER_TUNE",
                "risk_level": Constitution.REGENCY.RISK_LOW,
                "content": content,
                "justification": f"Reflexive optimization triggered by finding: {finding}",
                "urgency": "LOW"
            }
            
            with open(filename, "w") as f:
                json.dump(proposal_data, f, indent=2)
                
            proposals.append(prop_id)
    
    return {
        "status": "OPTIMIZATION_PROPOSED", 
        "health_score": audit["health_score"],
        "proposals_generated": proposals
    }

if __name__ == "__main__":
    mcp.run()