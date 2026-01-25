import os
import json
import yaml
import pytest
from modules.learner import Learner

@pytest.fixture
def temp_paths(tmp_path):
    expertise = tmp_path / "expertise.yaml"
    vault = tmp_path / "proposals"
    vault.mkdir()
    return expertise, vault

def test_learner_extraction(temp_paths):
    exp_path, vault_path = temp_paths
    learner = Learner(expertise_path=str(exp_path), vault_path=str(vault_path))
    
    # Create a dummy failure
    failure_file = vault_path / "mutation_test_999.json"
    failure_data = {
        "id": "TEST-BOT",
        "pnl": -10,
        "event_type": "DIED",
        "traits": {"asset": "TEST", "slippage": 0.1}
    }
    with open(failure_file, 'w') as f:
        json.dump(failure_data, f)
        
    # Run learning
    result = learner.learn_from_mutation(str(failure_file))
    
    assert result is True
    
    # Verify expertise update
    with open(exp_path, 'r') as f:
        data = yaml.safe_load(f)
        
    assert "TEST" in data["assets"]
    assert len(data["assets"]["TEST"]) == 1
    assert "slippage guard 0.1" in data["assets"]["TEST"][0]["insight"]

def test_learner_no_signal(temp_paths):
    exp_path, vault_path = temp_paths
    learner = Learner(expertise_path=str(exp_path), vault_path=str(vault_path))
    
    # Create a success
    success_file = vault_path / "mutation_test_888.json"
    success_data = {
        "id": "PROFIT-BOT",
        "pnl": 100,
        "event_type": "EVOLVED",
        "traits": {"asset": "TEST", "slippage": 0.01}
    }
    with open(success_file, 'w') as f:
        json.dump(success_data, f)
        
    result = learner.learn_from_mutation(str(success_file))
    assert result is False
