import time
import random
from blackglass.resilience.circuit import ThermodynamicBreaker

# Initialize the Governor
governor = ThermodynamicBreaker(recovery_timeout=5, variance_threshold=1.5)

@governor
def fetch_market_data(ticker: str):
    """Simulates a network call that sometimes lags (The OpenBB Scenario)."""
    print(f"Requesting {ticker}...")
    
    # Simulate Entropy: Random latency spike
    latency = random.uniform(0.1, 0.5)
    
    # 20% chance of Hydrostatic Lock (3.0s delay)
    if random.random() < 0.2:
        print(">>> NETWORK LAG SPIKE (Simulating Lock)...")
        latency = 3.0
        
    time.sleep(latency)
    return f"Data for {ticker}"

# Run the Simulation
print("=== BLACKGLASS PREDICTIVE INTERDICTION DEMO ===")
for i in range(15):
    print(f"\n[Tick {i+1}]")
    result = fetch_market_data("AAPL")
    if result is None:
        print(">>> SYSTEM SAVED. Call was blocked.")
    else:
        print(">>> SUCCESS.")
    time.sleep(0.5)
