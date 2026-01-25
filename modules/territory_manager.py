import asyncio
import logging
from typing import Dict

"""
INHIBITOR CHIPS (Phase 4)
========================
Prevents fratricide among autonomous clones.

Theory: In low-liquidity pairs, slippage scales non-linearly.
Two simultaneous $1,000 buy orders might incur 3x-4x the slippage
of a single order. This destroys Expected Value (EV).

Solution: Mutual Exclusion (Mutex) protocol.
Before any clone executes a trade, it must acquire territory.
"""

class TerritoryManager:
    def __init__(self):
        self._territories: Dict[str, asyncio.Lock] = {}
        self.logger = logging.getLogger("InhibitorChip")
        self.logger.setLevel(logging.INFO)

    async def acquire_territory(self, clone_id: str, token_address: str) -> bool:
        """
        Attempts to lock a specific liquidity pool for a clone's execution phase.
        Returns True if territory is secured, False if occupied.
        
        Args:
            clone_id: Unique identifier of the clone requesting access
            token_address: The token address representing the liquidity pool
            
        Returns:
            bool: True if lock acquired, False if territory occupied
        """
        # Initialize lock for this territory if first access
        if token_address not in self._territories:
            self._territories[token_address] = asyncio.Lock()
        
        lock = self._territories[token_address]
        
        # Check if territory is already occupied
        if lock.locked():
            self.logger.warning(
                f"[INHIBITOR] :: DENIED :: {clone_id} attempted breach of "
                f"occupied territory {token_address[:10]}..."
            )
            return False
        
        # Acquire the lock
        await lock.acquire()
        self.logger.info(
            f"[INHIBITOR] :: LOCKED :: {clone_id} holds territory {token_address[:10]}..."
        )
        return True

    def release_territory(self, clone_id: str, token_address: str):
        """
        Releases the lock on a liquidity pool, allowing other clones to engage.
        
        Args:
            clone_id: Unique identifier of the clone releasing the lock
            token_address: The token address representing the liquidity pool
        """
        if token_address in self._territories:
            lock = self._territories[token_address]
            if lock.locked():
                lock.release()
                self.logger.info(
                    f"[INHIBITOR] :: RELEASED :: {clone_id} vacated "
                    f"territory {token_address[:10]}..."
                )

    async def execute_with_territory(self, clone_id: str, token_address: str, trade_func):
        """
        Context manager pattern for automatic acquire/release.
        
        Usage:
            await territory_manager.execute_with_territory(
                clone_id="AERO_SCALPER_PRIME",
                token_address="0x940181a94a35A4569E4529A3CDfB74e38FD98631",
                trade_func=lambda: executor.execute_swap(...)
            )
        """
        acquired = await self.acquire_territory(clone_id, token_address)
        
        if not acquired:
            self.logger.warning(f"[INHIBITOR] :: {clone_id} ABORTED :: Territory occupied")
            return None
        
        try:
            result = await trade_func()
            return result
        finally:
            self.release_territory(clone_id, token_address)


# Singleton Instance (Imported by swarm_factory.py)
inhibitor = TerritoryManager()
