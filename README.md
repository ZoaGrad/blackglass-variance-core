# Blackglass Watchtower — Predictive Reliability System

> **"Most downtime happens because systems wait for failure to trigger alerts. Watchtower inverts this by acting on variance before thresholds break."**

---

## 🎯 The Mission

Blackglass Watchtower is an **autonomous reliability agent** designed to demonstrate a closed-loop SRE control plane.

Instead of passive dashboards, it implements **Predictive Interdiction**:
1.  **Detects Variance**: Analyzes statistical drift in queue depth and latency.
2.  **Predicts Saturation**: Identifies when a system is *about* to fail, not just when it has.
3.  **Autonomous Interdiction**: Triggers mitigation plans (scaling/throttling) instantly.
4.  **Evidence-First**: Every decision is cryptographically linked to raw telemetry artifacts.

## 🏗️ System Architecture

The system is split into two distinct layers (see [ARCHITECTURE.md](ARCHITECTURE.md)):

*   **Variance Core ("Physics")**: A signal generator that simulates complex failure modes (drift, latency spikes, queue saturation).
*   **Watchtower ("Intelligence")**: An always-on loop that ingests artifacts, applies statistical thresholds, and enforces stability.

## 📦 Proof of Life

We do not rely on "demo screenshots." This repository contains a detailed, reproducible artifact chain from a real autonomous run.

See: **[evidence/demo_run/](evidence/demo_run/)**

*   **Signals**: `metrics.json` showing queue saturation (>50) at 13:58.
*   **Intelligence**: `analysis.json` predicting failure with 0.9 confidence.
*   **Action**: `mitigation_plan.json` triggering `SCALE_WORKERS` before the drop.

## ✅ Verification & Proof

- **Architecture**: `ARCHITECTURE.md`
- **Proof-of-Life**: `evidence/demo_run/`
- **Visual Evidence**: `assets/dashboard_evidence.png`, `assets/log_evidence.png`
- **Trace**: `WALKTHROUGH.md`

## 🚀 Quick Run

You can verify the system's logic on your own machine in 60 seconds:

```powershell
# Run a Verifiable Simulation (Metrics Only)
python -m src.agent simulate

# Run the Full Autonomous Control Loop (Simulate -> Analyze -> Mitigate)
python -m src.agent watch
```

## 🗺️ Integration Map

Watchtower is designed as a composable primitive.

| Integration Point | Artifact | Role |
| :--- | :--- | :--- |
| **Telemetry In** | `metrics.json` | The only truth the system sees. Feed this from Prometheus/Datadog. |
| **Decisions Out** | `cycle_summary.json` | High-level audit log. 1 row per cycle. |
| **Actuation** | `mitigation_plan.json` | Machine-readable instructions for scaling/throttling. |

## 🛠️ Advanced Usage

Full control over the loop via CLI flags:

```bash
# Run 10 cycles, output to specific build folder
python -m src.agent watch --cycles 10 --output-dir build/evidence

# Simulate a specific drift scenario (0.0 - 1.0)
python -m src.agent simulate --drift 0.8 --duration 60 --output-dir runs/test_drift

# Integration Adapters (Prometheus Stub + K8s Stub)
python -m src.agent watch --telemetry prometheus --actuation k8s
```

## 🛡️ Field Reports
Real-world validation of the Blackglass Variance Engine against sovereign-grade targets.

*   **[SECTOR ANALYSIS Q1: OpenBB vs. Nautilus Trader](docs/SECTOR_ANALYSIS_Q1.md)**
    *   *A comparative audit of Hydrostatic Integrity.*
    *   **OpenBB:** Score 1602 (Critical Variance / Blocking I/O).
    *   **Nautilus:** Score 99 (Stable / Async Rust).
*   **[CASE STUDY: OpenBB Audit](docs/CASE_STUDY_OPENBB.md)**
    *   *Deep dive into 306 blocking call sites and reliability interdiction.*

## 🛡️ Reliability Engineering Features

*   **Singleton Enforcement**: Uses `.watchtower.lock` with stale-lock recovery (>5m) to prevent race conditions.
*   **Log Rotation**: Automatically rotates logs at 10MB to prevent disk exhaustion.
*   **Heartbeat Telemetry**: Writes `watchtower_runtime.json` every cycle for external monitoring.
*   **Deployment Ready**: Includes scripts for [Admin Service](scripts/install_watchtower_task.ps1) and [User-Level](scripts/install_watchtower_task_user.ps1) persistence.

---
*Built with Google Antigravity. Capable of being deployed as a standalone agent or integrated into existing observability stacks.*
