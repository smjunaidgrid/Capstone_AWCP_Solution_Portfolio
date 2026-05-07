# 04 Evidence Substrate & Infrastructure (DevOps)

This folder contains the Dockerized infrastructure required to run the Agent Workforce Control Plane's zero-trust governance and immutable storage layers. By isolating these into containers, the AWCP ensures that policy decisions and evidence ledgers remain decoupled from the execution backend.

## Domain Purpose

The Infrastructure domain focuses on:
- Providing an immutable object storage vault for cryptographic execution receipts.
- Hosting the Zero-Trust policy engine to evaluate autonomous agent actions.
- Ensuring easy, reproducible local deployment via Docker Compose.

## Core Architecture Components

### 1. The Evidence Ledger (MinIO)
MinIO acts as our S3-compatible cryptographic vault. When the Cognitive Shield evaluates an agent's execution, the resulting assessment (containing Context Hashes, Artifact Folds, and Replay Summaries) is locked in the `awcp-ledger` bucket.
* **API Port:** `9000`
* **Console Port:** `9001` (Operator UI for inspecting the vault)
* **Credentials:** `admin` / `password`

### 2. The Governance Engine (Open Policy Agent - OPA)
OPA serves as the strict "Bouncer" for the control plane. Before the Temporal orchestrator executes any state-changing code, the Intake Proxy queries OPA. OPA evaluates the request against our strict `agent_policy.rego` rules.
* **API Port:** `8181`
* **Policy Language:** Rego
* **Key Function:** Blocks out-of-scope actions and enforces security boundaries before any compute resources are spent.

## Setup & Execution

### Prerequisites
* Docker and Docker Compose must be installed and running on your machine.

### Booting the Infrastructure
From this directory (`04_Evidence_Substrate_Infra`), run the following command to download the images and start the containers in the background:

```bash
docker-compose up -d