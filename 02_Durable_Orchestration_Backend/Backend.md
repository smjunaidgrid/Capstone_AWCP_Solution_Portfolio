# 02 Durable Orchestration Backend

This folder contains the core orchestration and governance layer of the Agent Workforce Control Plane (AWCP). It acts as the "Front Door" and "Workflow Engine," safely receiving inbound agent requests, gating them through Zero-Trust policies, and durably executing them so no state is ever lost.

## Domain Purpose

The Backend domain focuses on:
- Normalizing inbound agent requests and tracking workflow identity.
- Enforcing Zero-Trust execution policies via Open Policy Agent (OPA).
- Orchestrating tasks using Temporal for durable, fault-tolerant execution.
- Bridging raw code-execution output to the Data Science Cognitive Shield.
- Writing immutable execution receipts to the Evidence Ledger (MinIO).

## Core Architecture Components

* **Workflow Intake Proxy (FastAPI):** Ingests workflow events, normalizes owner and identity metadata, and opens governed branches without replacing the underlying runtime stack.
* **Approval Gate Controller (OPA + FastAPI):** Evaluates risk signals against configurable rules. Blocks out-of-scope actions and enforces security boundaries *before* execution.
* **Workflow Engine (Temporal):** Runs durable workflow DAGs with retry, timeout, and saga semantics. It handles safe resume, branch isolation, and deterministic replay for fault tolerance.
* **Code Sandbox (Python Worker):** A secure execution environment where the agent's proposed code is safely run and evaluated.

## Data Flow Sequence

1. **Trigger:** An autonomous agent proposes a state-changing write action (e.g., executing Python code).
2. **Ingestion & Normalization:** The Intake Proxy (`intake_proxy.py`) receives the payload and generates a unique Workflow ID.
3. **Policy Gate:** The Proxy queries the OPA server on Port 8181. If the action violates the `agent_policy.rego` rules (e.g., attempting a system-level wipe), it is instantly blocked.
4. **Durable Handoff:** If approved, the Proxy hands the task to Temporal (`workflows.py`), which logs the task durably.
5. **Execution:** The Temporal Worker (`worker.py`) picks up the task and executes the sandboxed code.
6. **Cognitive Shield Evaluation:** The execution trace is passed to the DS layer (`backend_bridge.py`) to generate a mathematically verifiable Replay Summary.
7. **Ledger Storage:** The final assessment is pushed to the MinIO `awcp-ledger` bucket as an immutable JSON receipt.

## Setup & Execution

### 1. Start Temporal
Ensure your Temporal development server is running:
```bash
temporal server start-dev