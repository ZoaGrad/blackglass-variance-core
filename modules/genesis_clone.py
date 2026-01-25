import os
import asyncio
from web3 import Web3
from eth_account import Account
import random
from .oracle_hunter import OracleHunter

class GenesisClone:
    def __init__(self, clone_id, config, web3_interface):
        self.id = clone_id
        self.config = config
        self.w3 = web3_interface
        self.hunter = OracleHunter(config) # The Warlord's Eyes
        self.traits = {
            "aggression": random.uniform(0.1, 0.9),
            "gas_tolerance": random.uniform(1.0, 1.5) # Multiplier of base fee
        }
        # [SECURITY] In a full swarm, we'd derive sub-keys here.
        # For Genesis, we observe via the main connection.

    async def pulse(self):
        """
        The Heartbeat.
        1. Reads LIVE Chain Data (Gas/Block).
        2. Queries targeted liquidity pools based on config.
        3. Decides action based on Traits.
        4. Returns outcome to Scribe.
        """
        try:
            # [SENSORY] Read the Live Chain
            latest_block = self.w3.eth.block_number
            gas_price = self.w3.eth.gas_price
            
            # [HUNTER] Get clone-specific parameters from config
            target_symbol = self.config.get('target_symbol', 'ETH')
            base_address = self.config.get('base_address')
            pair_address = self.config.get('pair_address')
            cex_symbol = self.config.get('cex_symbol', 'ETHUSD')
            threshold = self.config.get('threshold', 0.005)
            
            # Query on-chain price for THIS clone's target
            current_on_chain_price = self.hunter.get_on_chain_price(
                self.w3,
                token_in=base_address,
                token_out=pair_address
            )
            
            if current_on_chain_price > 0:
                 print(f"[{target_symbol}] :: Live Chain Price: ${current_on_chain_price:.2f}")
                 # Use targeted CEX query for this clone's symbol
                 cex_price = await self.hunter.get_cex_price(cex_symbol)
                 
                 if cex_price > 0:
                     # Calculate delta manually for this specific clone
                     delta = (cex_price - current_on_chain_price) / current_on_chain_price
                     
                     if abs(delta) > threshold:
                         hunter_signal = {
                             "signal": "LONG" if delta > 0 else "SHORT",
                             "confidence": abs(delta) * 100,
                             "reason": "CEX_PUMP_DETECTED" if delta > 0 else "CEX_CRASH_DETECTED",
                             "cex_price": cex_price,
                             "chain_price": current_on_chain_price
                         }
                     else:
                         hunter_signal = None
                 else:
                     hunter_signal = None

            # [LOGIC] The "Hunger"
            # If gas is cheap and I am aggressive -> LOOK FOR FOOD.
            action = "WAIT"
            pnl = 0.0
            
            if hunter_signal:
                 print(f"[WARLORD] :: OPPORTUNITY DETECTED :: {hunter_signal['signal']} ({hunter_signal['reason']})")
                 if self.traits['aggression'] > 0.5:
                     action = "HUNTING_ARBITRAGE"
            
            # Simple Heuristic for Genesis:
            # If Gas is low (<0.1 Gwei on Base is common, let's say <1 Gwei for safety)
            # We "simulate" a win to test the Scribe connection to real data.
            # Note: Base gas is often very low, so we check < 1 gwei
            elif gas_price < Web3.to_wei(1.0, 'gwei'):
                 if self.traits['aggression'] > 0.5:
                     action = "HUNTING_GAS"
                     # In Phase 3, this is where we execute the swap.
            
            return {
                "id": self.id,
                "gen": 1,
                "action": action,
                "pnl": pnl,
                "traits": self.traits,
                "telemetry": {
                    "block": latest_block,
                    "gas": gas_price,
                    "hunter_signal": hunter_signal
                }
            }

        except Exception as e:
            return {
                "id": self.id,
                "action": "ERROR",
                "pnl": 0,
                "error": str(e)
            }

