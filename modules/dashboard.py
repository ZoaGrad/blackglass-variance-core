import asyncio
import os
import sys
import time
import random
from colorama import init, Fore, Style, Back

# [VISUALS]
init(autoreset=True)

# [MOCK CONFIG FOR VISUALIZATION]
TARGETS = {
    "ETH":   {"cex": 3100.00, "volatility": 0.5},
    "AERO":  {"cex": 1.45,    "volatility": 2.0},
    "BRETT": {"cex": 0.12,    "volatility": 5.0} # Memecoins go crazy
}

class OculusV2:
    def __init__(self):
        self.width = 50

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def draw_header(self):
        print(f"{Back.WHITE}{Fore.BLACK} == [ BLACKGLASS OMNI-SPECTRAL RADAR ] == {Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}Scanning Base L2 Liquidity Pools...{Style.RESET_ALL}\n")

    def draw_target_panel(self, symbol, base_price, volatility):
        """
        Simulates the live feed for one target.
        """
        # Simulate CEX Price (The Anchor)
        cex_price = base_price
        
        # Simulate DEX Price (The Chaos)
        # Higher volatility = Bigger jitter
        jitter_percent = random.uniform(-volatility, volatility)
        dex_price = cex_price * (1 + (jitter_percent / 100))
        
        # Calculate Delta
        delta = ((cex_price - dex_price) / dex_price) * 100
        
        # Determine Color Status
        status_color = Fore.GREEN
        status_text = "SYNC"
        
        if abs(delta) > 1.0:
             status_color = Fore.RED + Style.BRIGHT
             status_text = "ARBITRAGE !!!"
        elif abs(delta) > 0.5:
             status_color = Fore.YELLOW
             status_text = "DRIFTING"

        # Render the Bar
        print(f"{Fore.CYAN}{symbol:<6} {Style.RESET_ALL} | CEX: ${cex_price:<7.4f} | DEX: ${dex_price:<7.4f}")
        print(f"STATUS: {status_color}{status_text:<12} {Style.RESET_ALL} | DELTA: {status_color}{delta:+.4f}%{Style.RESET_ALL}")
        
        # Visual Bar
        bar_len = int(abs(delta) * 10) # Scale bar by deviation
        bar_char = "█" * min(bar_len, 40)
        print(f"{status_color}{bar_char}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}" + "-"*self.width + f"{Style.RESET_ALL}")

    async def run(self):
        while True:
            self.clear_screen()
            self.draw_header()
            
            # Loop through targets
            for symbol, data in TARGETS.items():
                # Add some random walk to the price
                move = random.uniform(-0.1, 0.1)
                TARGETS[symbol]['cex'] += (TARGETS[symbol]['cex'] * (move/100))
                
                self.draw_target_panel(symbol, TARGETS[symbol]['cex'], TARGETS[symbol]['volatility'])
            
            print(f"\n{Back.BLUE}{Fore.WHITE} [SYSTEM READY] AWAITING CAPITAL DEPLOYMENT {Style.RESET_ALL}")
            await asyncio.sleep(0.2) # Fast refresh

if __name__ == "__main__":
    try:
        hud = OculusV2()
        asyncio.run(hud.run())
    except KeyboardInterrupt:
        sys.exit()
