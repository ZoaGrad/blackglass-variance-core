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

## 🚀 Quick Run

You can verify the system's logic on your own machine in 60 seconds:

```powershell
# Run a single deterministic cycle
venv\Scripts\python src\agent.py "Run a simulation for 60 seconds, analyze it, and write mitigation output."
```

## 🛡️ Reliability Engineering Features

*   **Singleton Enforcement**: Uses `.watchtower.lock` with stale-lock recovery (>5m) to prevent race conditions.
*   **Log Rotation**: Automatically rotates logs at 10MB to prevent disk exhaustion.
*   **Heartbeat Telemetry**: Writes `watchtower_runtime.json` every cycle for external monitoring.
*   **Deployment Ready**: Includes scripts for [Admin Service](scripts/install_watchtower_task.ps1) and [User-Level](scripts/install_watchtower_task_user.ps1) persistence.

---
*Built with Google Antigravity. Capable of being deployed as a standalone agent or integrated into existing observability stacks.*
