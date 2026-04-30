# 📑 Agent Workforce Control Plane (AWCP) - Master AI Context Manifesto

## 1. Project Overview
This project builds the **Agent Workforce Control Plane (AWCP)**, a governance and orchestration layer that sits above existing autonomous agent runtimes. It is designed to safely manage, pause, and recover agents when they interact with critical business systems. 

The core mission is to implement a **Cognitive Shield**, **Memory Substrate**, and **Recovery Reasoning Engine**. The system must gracefully degrade an agent's autonomy when failures rise, enforce policy-gated write actions, and provide deterministic replayability.

---

## 2. Strict Architectural Constraints & Local Prototype Overrides
To maintain a zero-cost local development environment during the 45-day proof, the AI MUST adhere to these prototype substitutions:
* **Durable Orchestration**: We use a local **Temporal** cluster running via Docker.
* **Evidence Ledger**: We use a local **MinIO** container instead of AWS S3 for immutable logging.
* **Sandboxed Execution**: The blueprint specifies *Modal Ephemeral Containers* for the CodeAct Sandbox. **PROTOTYPE OVERRIDE**: Use highly restricted, timed-out **Python Subprocesses** locally to avoid cloud vendor costs.
* **Governance**: We use a locally hosted **Open Policy Agent (OPA)** server.
* **Feature Flags**: Simulated locally or using a free tier of **Flipt**.

---

## 3. Directory Structure & File Relationships
The project is strictly divided into five cross-functional domains. When generating code, the AI must place files in their designated domain and import cross-domain APIs accordingly.

### 📁 `01_Cognitive_Shield_DS` (Data Science & Intelligence)
**Owner:** Data Science Team (DS-1, DS-2, DS-3)
**Responsibility:** Perceiving, standardizing, and hashing agent state.
* `state_assembly.py`: Defines the **Governing Slice** (minimum metadata/flags required for policy judgment).
* `context_graph.py`: Models agent memory as a Directed Acyclic Graph (DAG) instead of flat text.
* `hashing_engine.py`: Generates the **Context Hash** (SHA-256 snapshots of agent memory).
* `rlm_compression.py`: Implements **Recursive Language Models (RLMs)** to compress large trace files into context folds.
* `failure_budget.py`: Calculates dynamic thresholds for API timeouts, errors, and logic loops.

### 📁 `02_Durable_Orchestration_Backend` (Python Backend)
**Owner:** Python Backend Team (PB-1, PB-2)
**Responsibility:** Durable orchestration, state machines, and the CodeAct sandbox.
* `intake_proxy.py`: Uses FastAPI/gRPC to convert chaotic runtime signals into a standardized **Workflow Identity**.
* `temporal_workflows/`: Directory for Temporal DAGs defining safe resume points.
* `saga_transactions.py`: Implements the Saga Pattern with compensating transactions to rollback failed cross-system writes.
* `sandbox_local.py`: Intercepts agent code and executes it in the local subprocess (Prototype override for Modal).
* `handoff_coordinator.py`: Manages cross-agent context transfers to ensure **Session Continuity**.

### 📁 `03_Risk_First_Operator_UI` (UI & Operator Surface)
**Owner:** UI/UX Team (UI-1)
**Responsibility:** Risk-First Dashboard, Evidence Viewer, and Intervention Workbenches.
* `src/App.tsx`: The main React layout.
* `src/components/LiveControlSurface.tsx`: Polls the Temporal engine; highlights **Workflows in Degraded Mode** and **Pending Branch Tokens**.
* `src/components/RecoveryWorkbench.tsx`: Visualizes chronological timelines mapping **Trace Spans** to policy decisions.
* `src/components/ApprovalGate.tsx`: Displays high-alert cards for cross-system writes with a countdown timer for **Narrow Approval Tokens**.
* `src/components/QuarantineInventory.tsx`: Catalog for under-instrumented agents displaying a strict read-only badge.

### 📁 `04_Evidence_Substrate_Infra` (DevOps & Infrastructure)
**Owner:** DevOps Team (DO-1)
**Responsibility:** Provisioning the immutable storage and execution engines.
* `docker-compose.yml`: Spins up Temporal, MinIO, and OPA sidecars.
* `otel_collector_config.yaml`: Routes high-level metrics to the UI and raw traces into the Evidence Ledger.

### 📁 `05_Governance_Policies_OPA` (Security & Governance)
**Owner:** Cross-Functional
**Responsibility:** Hard-coded security thresholds using Rego language.
* `write_scopes.rego`: Defines the pre-approved digital boundaries detailing exactly which external systems an agent is allowed to alter.
* `degradation_rules.rego`: Defines the state transition matrix for moving an agent into **Conservative Mode** or **Recommendation-Only Mode**.

---

## 4. Core Domain Vocabulary (Context Anchors)
AI must use these exact terms when defining variables, functions, or generating documentation:
* **Evidence Ledger**: The durable, append-only database (MinIO) used for audits and replays.
* **Stale Context**: A state where an agent attempts to act on memory that contradicts chronologically verified ledger data.
* **Trace Sampling Multiplier**: Logic that spikes log capture depth to 100% the moment a failure signal is detected.
* **Replay Summary**: A synthesized, human-readable breakdown showing what the agent attempted, what failed, and the Next Safe Action.
* **Idempotency Keys**: Unique, one-time identifiers attached to every tool call to prevent duplicate actions during network timeouts.
* **Artifact Ledger Fold**: Logic that parses massive JSON payloads from the sandbox, extracts state-changing variables, and writes them to the ledger.
* **Observability Hooks**: Digital markers injected into agent code to emit signals at step boundaries.

---

## 5. AI System Directives (Rules of Engagement)
When acting as a coding assistant for the AWCP project, the AI MUST obey these rules:
1. **Never Assume Cloud Compute**: If asked to build the sandbox or storage, default to `subprocess` or `MinIO/Temporal` locally.
2. **Mandatory Checkpointing**: If writing a Python function that changes state, the AI MUST wrap it in a Temporal `@workflow.defn` or `@activity.defn` to ensure durability.
3. **Risk-First UI Assumption**: If asked to design a UI component, do not build standard "task lists." Build interfaces that only highlight errors, budget breaches, or approval gates.
4. **Idempotency is Non-Negotiable**: Any generated API request logic must include an Idempotency Key header.
5. **Cross-Domain Imports**: Ensure that UI components fetch data from the `intake_proxy.py` endpoints, and `intake_proxy.py` validates requests against the OPA rules in the `05` folder.