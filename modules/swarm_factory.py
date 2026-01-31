import asyncio
import json
import os
from pathlib import Path
from web3 import Web3
from .genesis_clone import GenesisClone

"""
SWARM FACTORY (Phase 4 - Config-Driven)
========================================
Factory Design Pattern for instantiating heterogeneous trading agents.

This refactored version reads from config.json to enable "hot-plugging"
new strategies without code deployment. Simply edit the manifest and restart.

Architecture:
- Reads config.json for clone definitions
- Spawns clones based on strategy_type
- Manages Web3 connection lifecycle
- Supports SIMULATION mode for testing
"""

class MockClone:
    """Simulation clone for testing without live capital."""
    def __init__(self, clone_id, config):
        self.id = clone_id
        self.config = config
        
    async def pulse(self):
        """Simulated heartbeat."""
        import random
        if random.random() < 0.1:
             return {
                 'id': self.id, 
                 'action': 'MUTATION_DRIFT', 
                 'pnl': round(random.uniform(-0.05, 0.15), 4),
                 'gen': 0,
                 'traits': {'aggression': 0.5, 'slippage': 0.05}
             }
        return {'id': self.id, 'action': 'WAIT', 'pnl': 0.0, 'gen': 0, 'traits': {}}


class SwarmFactory:
    """
    The Forge: Instantiates and manages the swarm.
    """
    def __init__(self, config_input="config.json"):
        # Load the Genetic Blueprint
        if isinstance(config_input, dict):
            self.config = config_input
            print(f"[FACTORY] :: CONFIG INJECTED :: {len(self.config.get('clones', [])) if 'clones' in self.config else 'Unknown'} entries")
        else:
            self.config = self._load_config(config_input)
            
        self.mode = os.getenv("MODE", "SIMULATION")  # Default to Safety
        self.w3 = None
        
        # Establish Web3 connection if LIVE
        if self.mode == "LIVE":
            self._establish_uplink()

    def _load_config(self, config_path):
        """Load and validate config.json."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"[FACTORY] :: FATAL :: Config not found at {config_path}")
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Validate required fields
        if 'clones' not in config:
            raise ValueError("[FACTORY] :: FATAL :: config.json missing 'clones' array")
        
        print(f"[FACTORY] :: CONFIG LOADED :: {len(config['clones'])} clone(s) defined")
        print(f"[FACTORY] :: SYSTEM STATUS :: {config.get('system_status', 'UNKNOWN')}")
        
        return config

    def _establish_uplink(self):
        """Establish Web3 connection to Base Mainnet."""
        rpc_url = os.getenv("BASE_RPC_URL") or self.config.get('rpc_endpoints', {}).get('base_mainnet')
        
        if not rpc_url:
            raise ValueError("[FACTORY] :: CRITICAL :: LIVE MODE requires BASE_RPC_URL in .env or config.json")
        
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not self.w3.is_connected():
            # Try fallback RPC
            fallback = self.config.get('rpc_endpoints', {}).get('fallback')
            if fallback:
                print(f"[FACTORY] :: PRIMARY RPC FAILED :: Attempting fallback...")
                self.w3 = Web3(Web3.HTTPProvider(fallback))
            
            if not self.w3.is_connected():
                raise ConnectionError("[FACTORY] :: CRITICAL :: FAILED TO CONNECT TO BASE RPC")
        
        print(f"[FACTORY] :: UPLINK ESTABLISHED :: Chain ID {self.w3.eth.chain_id}")

    def ignite_clones(self):
        """
        Instantiate clones from config.json manifest.
        Returns list of clone instances ready for activation.
        """
        clones = []
        
        for clone_config in self.config['clones']:
            clone_id = clone_config['id']
            enabled = clone_config.get('enabled', True)
            
            if not enabled:
                print(f"[FACTORY] :: SKIPPING :: {clone_id} (disabled in config)")
                continue
            
            if self.mode == "LIVE":
                # Spawn Real Clone (GenesisClone)
                clone = GenesisClone(
                    clone_id=clone_id,
                    config=clone_config,
                    web3_interface=self.w3
                )
                print(f"[FACTORY] :: SPAWNED :: {clone_id} (LIVE - {clone_config['target_symbol']})")
            else:
                # Spawn Mock Clone (Simulation)
                clone = MockClone(clone_id, clone_config)
                print(f"[FACTORY] :: SPAWNED :: {clone_id} (SIMULATION)")
            
            clones.append(clone)
        
        print(f"[FACTORY] :: IGNITION COMPLETE :: {len(clones)} active clone(s)")
        return clones
    
    def get_execution_settings(self):
        """Return execution settings from config for Auditor."""
        return self.config.get('execution_settings', {})
