import requests
import json
import time

# HEADERS: This is the "Mask" to look like a browser, not a bot.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def probe_coinbase(symbol="ETH"):
    url = f"https://api.coinbase.com/v2/prices/{symbol}-USD/spot"
    print(f"\n[PROBE] :: Pinging Coinbase ({url})...")
    try:
        # Try WITHOUT headers first (Baseline)
        print("   > Attempt 1 (No Headers)... ", end="")
        r = requests.get(url, timeout=5)
        print(f"Status: {r.status_code}")
        
        # Try WITH headers (The Fix)
        print("   > Attempt 2 (With Headers)... ", end="")
        r = requests.get(url, headers=HEADERS, timeout=5)
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            price = data['data']['amount']
            print(f"   > SUCCESS :: Price: ${price}")
        else:
            print(f"   > FAIL :: Response: {r.text[:100]}")
            
    except Exception as e:
        print(f"   > CRITICAL ERROR :: {str(e)}")

def probe_binance(symbol="ETH"):
    # Note: Binance.com is often blocked in US. 
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
    print(f"\n[PROBE] :: Pinging Binance Global ({url})...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        print(f"   > Status: {r.status_code}")
        if r.status_code == 200:
            print(f"   > SUCCESS :: Price: {r.json()['price']}")
        elif r.status_code == 451:
            print("   > FAIL :: Geo-Blocked (US IP Detected).")
        else:
            print(f"   > FAIL :: {r.text[:100]}")
    except Exception as e:
        print(f"   > ERROR :: {str(e)}")

def probe_coingecko(id_list=["ethereum", "pepe", "mog-coin", "degen-base", "toshi"]):
    # Fallback option
    ids = ",".join(id_list)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
    print(f"\n[PROBE] :: Pinging CoinGecko ({url})...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        print(f"   > Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            for coin in id_list:
                if coin in data:
                    print(f"   > SUCCESS :: {coin}: ${data[coin]['usd']}")
                else:
                     print(f"   > FAIL :: {coin} not in response")
    except Exception as e:
        print(f"   > ERROR :: {str(e)}")

if __name__ == "__main__":
    print("--- STARTING CEX DIAGNOSTIC (MEMECOIN EDITION) ---")
    probe_coingecko(["ethereum", "pepe", "mog-coin", "degen-base", "toshi"])
    print("\n--- DIAGNOSTIC COMPLETE ---")
