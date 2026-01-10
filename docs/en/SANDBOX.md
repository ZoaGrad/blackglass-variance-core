# Sandbox Code Execution

## Overview

The sandbox module provides safe, configurable code execution environments for the Antigravity agent. It enables the agent to run generated Python code with different levels of isolation and resource control.

**Key principle:** Zero-Config by default (local execution), with opt-in Docker for stronger isolation.

## Quick Start

### Local Execution (Default)

No setup required. Code runs in an isolated subprocess on your machine:

```bash
python src/agent.py "Write and execute Python code to calculate 2 + 2"
```

The agent will:
- Generate Python code
- Execute it safely in an isolated subprocess
- Return the result

### Docker Execution (Opt-In)

For stronger isolation (filesystem, network, resources):

```bash
export SANDBOX_TYPE=docker
export DOCKER_IMAGE=antigravity-sandbox:latest

# First, build the sandbox image (optional; uses python:3.11-slim by default)
docker build -f Dockerfile.sandbox -t antigravity-sandbox:latest .

# Then run your agent
python src/agent.py "Your code generation task"
```

## Configuration

All sandbox behavior is controlled via environment variables.

### Core Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SANDBOX_TYPE` | `local` | Execution environment: `local`, `docker`, or `e2b` (future) |
| `SANDBOX_TIMEOUT_SEC` | `30` | Maximum code execution time (seconds) |
| `SANDBOX_MAX_OUTPUT_KB` | `10` | Maximum stdout/stderr size before truncation (KB) |

### Local-Specific Variables

The local sandbox uses your system's Python interpreter inside a temporary working directory.

- No extra variables required
- Works immediately after `pip install -r requirements.txt`

### Docker-Specific Variables

These are only used when `SANDBOX_TYPE=docker`.

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCKER_IMAGE` | `python:3.11-slim` | Base Docker image to use |
| `DOCKER_NETWORK_ENABLED` | `false` | Allow container network access |
| `DOCKER_CPU_LIMIT` | `0.5` | CPU limit (cores) |
| `DOCKER_MEMORY_LIMIT` | `256m` | Memory limit |

### Example Configuration Files

#### Local (Default)

```bash
# .env or shell export
SANDBOX_TYPE=local
SANDBOX_TIMEOUT_SEC=30
SANDBOX_MAX_OUTPUT_KB=10
```

#### Docker (Isolated)

```bash
SANDBOX_TYPE=docker
DOCKER_IMAGE=antigravity-sandbox:latest
DOCKER_NETWORK_ENABLED=false
DOCKER_CPU_LIMIT=0.5
DOCKER_MEMORY_LIMIT=256m
SANDBOX_TIMEOUT_SEC=60
SANDBOX_MAX_OUTPUT_KB=100
```

## Security Model

### Local Sandbox

**Isolation Level:** Process-level (subprocess)

**Intended Use:**
- Development and local testing
- Trusted code from LLMs in controlled environments
- Quick iteration with fast execution

**Security Properties:**
- Code runs with the same user and privileges as the agent
- No filesystem isolation (runs in temp directory but accessible to user)
- Network access available (unless filtered elsewhere)
- Resource limits: timeout, output size

**What It Protects Against:**
- Runaway processes (timeout enforcement)
- Resource exhaustion (output truncation)
- Working directory pollution (temp directory isolation)

**What It Does NOT Protect Against:**
- Malicious LLM-generated code with OS access (e.g., `rm -rf`, network attacks)
- **Recommendation:** Use Docker mode for untrusted code sources

### Docker Sandbox

**Isolation Level:** Container-level (Linux namespaces, cgroups)

**Intended Use:**
- Production environments
- Untrusted or semi-trusted code
- Multi-user systems

**Security Properties:**
- Filesystem isolation (container has independent rootfs)
- Network isolation (`--network=none` by default)
- Capability dropping (minimal privileges)
- Resource limits (CPU, memory)
- Process killing on timeout

**What It Protects Against:**
- Filesystem access beyond `/work` mount (read-only in most cases)
- Network-based attacks (network disabled)
- Resource exhaustion (CPU/memory caps)
- Privilege escalation (non-root user by default)

**What It Does NOT Protect Against:**
- Container escape (possible but rare; depends on kernel version and Docker version)
- **Recommendation:** Keep Docker and kernel up-to-date; treat as "defense in depth" not absolute isolation

### Future: Cloud Sandbox (E2B)

**Coming in Phase 9C** — Full multi-tenant isolation via remote VMs or Firecracker microVMs.

## Using the Sandbox in Code

### Direct API

```python
from src.sandbox.factory import get_sandbox

sandbox = get_sandbox()  # Returns configured sandbox (local or docker)

result = sandbox.execute(
    code="print('Hello')",
    language="python",
    timeout=30
)

print(f"Exit code: {result.exit_code}")
print(f"Output: {result.stdout}")
print(f"Duration: {result.duration:.2f}s")
print(f"Metadata: {result.meta}")
```

### Via Agent Tool

The agent can access the sandbox through the `run_python_code` tool:

```python
from src.tools.execution_tool import run_python_code

result = run_python_code(
    code="print('Executed by agent')",
    timeout=30
)
print(result)  # Compact string output or error message
```

## Building Custom Sandbox Images

If `DOCKER_IMAGE` points to a custom image, you can build it with:

```bash
docker build -f Dockerfile.sandbox -t my-sandbox:latest .
```

The included `Dockerfile.sandbox` provides:
- `python:3.11-slim` base
- Common packages: `numpy`, `pandas`, `requests`, `matplotlib`, `scipy`
- Non-root `sandbox` user for security
- `/work` as execution directory

### Customize for Your Needs

```dockerfile
# Dockerfile.sandbox.custom
FROM python:3.11-slim

# Add your packages
RUN pip install --no-cache-dir \
    tensorflow \
    torch \
    scikit-learn

# ... rest of original Dockerfile.sandbox
```

Then:

```bash
export DOCKER_IMAGE=my-sandbox:latest
docker build -f Dockerfile.sandbox.custom -t my-sandbox:latest .
python src/agent.py "Your task"
```

## Troubleshooting

### "Docker daemon not available"

**Problem:** You've set `SANDBOX_TYPE=docker` but Docker isn't running.

**Solution:**
```bash
# Start Docker daemon
sudo systemctl start docker  # Linux
# or use Docker Desktop (macOS/Windows)

# Verify
docker ps
```

### "Docker permission denied"

**Problem:** Your user isn't in the `docker` group.

**Solution:**
```bash
# Add user to docker group (requires sudo)
sudo usermod -aG docker $USER

# Activate group (or logout/login)
newgrp docker

# Test
docker ps
```

### Timeout on Local Sandbox

**Problem:** Code takes longer than `SANDBOX_TIMEOUT_SEC`.

**Solution:**
```bash
# Increase timeout
export SANDBOX_TIMEOUT_SEC=120

# Or make code more efficient
```

### Output Truncated

**Problem:** Execution output exceeds `SANDBOX_MAX_OUTPUT_KB`.

**Solution:**
```bash
# Increase limit
export SANDBOX_MAX_OUTPUT_KB=100

# Or reduce logging in generated code
```

## Performance

### Typical Latencies

| Mode | First Run | Warm Run | Timeout (5s) |
|------|-----------|----------|--------------|
| Local | <50ms | <50ms | <5.1s |
| Docker | 1-3s | <100ms | <5.1s |

Docker's first run is slower due to image pull and container startup. Subsequent runs use cached layers.

## Examples

### Example 1: Simple Calculation

```bash
python src/agent.py "Calculate the sum of numbers 1 to 100"
```

Agent generates and executes:
```python
print(sum(range(1, 101)))
```

Local sandbox output: `5050` (instantaneous)

### Example 2: Data Analysis

```bash
export SANDBOX_TYPE=docker
python src/agent.py "Analyze a sample CSV and show mean of values"
```

Agent generates and executes in Docker:
```python
import pandas as pd
data = pd.read_csv("data.csv")
print(data.mean())
```

Output: Formatted statistics

### Example 3: Long-Running Task

```bash
export SANDBOX_TIMEOUT_SEC=300
python src/agent.py "Train a simple model on sample data"
```

Timeout set to 5 minutes for training.

## Testing

Run the sandbox test suite:

```bash
pytest tests/test_local_sandbox.py tests/test_docker_sandbox.py tests/test_factory.py -v
```

- **Local tests** always run
- **Docker tests** skip automatically if daemon unavailable
- All tests validate data contracts and error paths

## Contributing

To add a new sandbox type (e.g., Kubernetes, E2B):

1. Create `src/sandbox/your_runtime.py` with a `YourSandbox` class
2. Implement the `CodeSandbox` Protocol (see `base.py`)
3. Update `factory.py` to recognize your type via env var
4. Add tests in `tests/test_your_runtime.py`
5. Update this documentation

See `src/sandbox/docker_exec.py` for a complete example.

## References

- [Sandbox Code Execution Spec](../../openspec/changes/2026-01-09-add-sandbox-execution/specs/sandbox/spec.md)
- [OpenSpec Proposal](../../openspec/changes/2026-01-09-add-sandbox-execution/proposal.md)
- [Roadmap Phase 9A](../ROADMAP.md#phase-9a-sandbox-environment-)
