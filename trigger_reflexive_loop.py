import asyncio
import json
import os
from dotenv import load_dotenv

# Load env before importing module that uses it
load_dotenv(r"C:\Users\colem\Code\blackglass-variance-core\.env")

from radiance_server import propose_self_optimization

async def main():
    print("🔮 TRIGGERING REFLEXIVE OPTIMIZAION LOOP...")
    
    # 1. Force the optimization tool
    result = await propose_self_optimization()
    
    print(f"\n✅ RESULT: {result['status']}")
    print(f"❤️ HEALTH SCORE: {result.get('health_score')}")
    
    if result.get("proposals_generated"):
        print(f"📜 PROPOSALS GENERATED: {len(result['proposals_generated'])}")
        for p_id in result["proposals_generated"]:
            print(f"   - {p_id}")
            
            # Read back the proposal
            path = os.path.join(os.path.dirname(__file__), f"evidence/proposals/{p_id}.json")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                    print(f"     TYPE: {data.get('type')}")
                    print(f"     JUSTIFICATION: {data.get('justification')}")
                    print(f"     STATUS: {data.get('status')}")
                    print("\n👉 RUN 'python ratify_proposal.py' TO ENTER THE CEREMONY.")

if __name__ == "__main__":
    asyncio.run(main())
