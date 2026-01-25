import os
import time
import asyncio
from modules.oracle_hunter import OracleHunter
from web3 import Web3

class VisualCortex:
    def __init__(self, w3, hunter):
        self.w3 = w3
        self.hunter = hunter
        self.history_len = 60  # Keep last 60 data points
        self.cex_history = [0] * self.history_len
        self.dex_history = [0] * self.history_len
        self.delta_history = [0] * self.history_len

    def clear_screen(self):
        # Clears the terminal based on OS
        os.system('cls' if os.name == 'nt' else 'clear')

    def normalize(self, value, min_val, max_val):
        # Normalize price to fit in a 50-char wide graph (actually height in the loop logic potentially)
        # The user's snippet prints line by line vertically, essentially a horizontal chart rotated?
        # Let's align with user's provided render logic:
        # User Logic: print "Price ^"; for i in range(50, 0, -2): ...
        # This implies 'i' is the Y-axis (Price), 50 chars high.
        # So we map Value -> 0..50
        range_val = max_val - min_val
        if range_val == 0:
            return 25
        return int(((value - min_val) / range_val) * 50)

    def render(self, cex_price, dex_price, delta):
        # Update History - we aren't plotting history on X-axis in this simple version, 
        # but tracking it for min/max scaling over time is smart.
        self.cex_history.pop(0)
        self.cex_history.append(cex_price)
        self.dex_history.pop(0)
        self.dex_history.append(dex_price)
        self.delta_history.pop(0)
        self.delta_history.append(delta)

        self.clear_screen()

        # Determine Scale based on recent history to keep chart centered
        valid_cex = [x for x in self.cex_history if x > 0]
        valid_dex = [x for x in self.dex_history if x > 0]
        all_prices = valid_cex + valid_dex
        
        if not all_prices:
            min_p = cex_price * 0.99
            max_p = cex_price * 1.01
        else:
            min_p = min(all_prices) * 0.999  # Tight buffer
            max_p = max(all_prices) * 1.001

        # Status Header
        status_color = "\033[92m"  # Green
        if abs(delta) > 0.005:     # 0.5% Threshold
            status_color = "\033[91m" # Red Alert
        
        print(f"\033[95m[SYSTEM] :: PROJECT OCULUS :: VISUAL CORTEX ACTIVE\033[0m")
        print(f"--------------------------------------------------")
        print(f"{status_color}DELTA: {delta*100:.4f}% ({'ARB OPPORTUNITY' if abs(delta) > 0.005 else 'MARKET EFFICIENT'})\033[0m")
        print(f"--------------------------------------------------")
        
        # Legend
        print(f"CYAN (X) :: CEX (Kraken) : ${cex_price:.2f}")
        print(f"MAGN (+) :: DEX (Base)   : ${dex_price:.2f}")
        print(f"--------------------------------------------------")

        # The Graph 
        # Y-axis is Price (0 to 50 scale)
        # We only draw the CURRENT price point (no history on X-axis in this specific snippet, 
        # effectively it's a 1-column bar chart or 'level meter' if not careful).
        # Actually user said "Price ^" and loop 50..0. This draws a vertical scale.
        # But where is the Time axis? 
        # The user's request code renders a single time slice vertically? 
        # Or maybe it's meant to show just the relative position of the two prices on a vertical scale.
        # Let's stick to the prompt's code structure exactly.
        
        print(f"Price  ^")
        for i in range(50, 0, -2):  # 25 rows of resolution
            line = ""
            current_level = i
            
            cex_pos = self.normalize(cex_price, min_p, max_p)
            dex_pos = self.normalize(dex_price, min_p, max_p)
            
            # Draw CEX Line Marker
            # If the normalized position is close to this row 'i'
            if abs(cex_pos - i) <= 1:
                line += " \033[96mX\033[0m" # Cyan X
            else:
                line += "  "
                
            # Draw DEX Line Marker
            if abs(dex_pos - i) <= 1:
                line += " \033[35m+\033[0m" # Magenta +
            else:
                line += "  "
            
            # Simple visualization of spread distance
            print(f"       |{line}")

        print(f"       +------------------ Price Level")

async def run_dashboard():
    from dotenv import load_dotenv
    load_dotenv()
    BASE_RPC = os.getenv('BASE_RPC_URL')
    
    w3 = Web3(Web3.HTTPProvider(BASE_RPC))
    hunter = OracleHunter(config={})
    cortex = VisualCortex(w3, hunter)

    print("[OCULUS] :: Booting...")
    # Seed history to avoid empty list errors
    cex_start = await hunter.get_cex_price()
    dex_start = hunter.get_on_chain_price(w3)
    cortex.cex_history = [cex_start] * cortex.history_len
    cortex.dex_history = [dex_start] * cortex.history_len
    
    await asyncio.sleep(1)

    while True:
        try:
            # 1. Get Data
            dex_price = hunter.get_on_chain_price(w3)
            cex_price = await hunter.get_cex_price()
            
            if dex_price == 0 or cex_price == 0:
                print("Error fetching data...")
                await asyncio.sleep(1)
                continue

            # 2. Calc Delta
            delta = (cex_price - dex_price) / dex_price

            # 3. Render
            cortex.render(cex_price, dex_price, delta)

            # 4. Heartbeat
            await asyncio.sleep(2) # Update every 2 seconds to avoid rate limits
            
        except KeyboardInterrupt:
            print("\n[OCULUS] :: DISENGAGED.")
            break
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_dashboard())
