# 01 Cognitive Shield DS

This folder contains the data science and intelligence layer for the AWCP local prototype. Its purpose is to perceive, standardize, hash, compress, and evaluate agent state so the workflow can build a Governing Slice, maintain a Context Graph, and avoid Stale Context execution.

## Domain Purpose

The Cognitive Shield DS domain focuses on:

- Generating deterministic Context Hashes for agent memory and state artifacts.
- Building the Governing Slice used for policy judgment before execution.
- Modeling context transitions as a deterministic directed graph of governed handoffs.
- Compressing sandbox traces into replayable Artifact Ledger Folds.
- Evaluating failure signals to shift autonomy into safer operating modes.
- Producing Replay Summaries that explain what happened and the Next Safe Action.
- Running repeatable fixture scenarios and rendering a DS-only visual report.

## DS Assessment Pipeline

The preferred entrypoint is `cognitive_shield.py`.

`CognitiveShield.evaluate_workflow_state(...)` accepts workflow identity, runtime metadata, feature flags, recent handoffs, prior evidence, raw sandbox traces, workflow metrics, and optional Evidence Ledger context hash data. It returns a complete Cognitive Shield assessment:

- `governing_slice`
- `context_hash`
- `freshness`
- `artifact_ledger_fold`
- `failure_budget`
- `replay_summary`

This keeps the DS work usable as a standalone intelligence layer while preserving the exact AWCP concepts needed later by orchestration, governance, and evidence storage.

## Files

`models.py`

Defines typed DS contracts for Freshness Results, Artifact Ledger Folds, Failure Budget Directives, Replay Summaries, and full Cognitive Shield Assessments.

`cognitive_shield.py`

Runs the unified Cognitive Shield DS pipeline across state assembly, hashing, freshness verification, trace compression, failure-budget evaluation, Context Graph lineage, and Replay Summary generation.

`scenario_runner.py`

Loads JSON workflow fixtures, runs them through the Cognitive Shield, and prints compact scenario summaries.

`visual_report.py`

Generates `visual_report.html`, a static browser report for visually checking scenario health, Stale Context detection, Failure Budget directives, Context Graph lineage, failed tools, and Replay Summaries.

`fixtures/`

Contains repeatable DS scenarios for healthy execution, Stale Context, failed writes, latency breach, and branching handoffs.

`hashing_engine.py`

Generates SHA-256 Context Hashes from state payloads and verifies freshness against ledger hashes.

`state_assembly.py`

Builds the Governing Slice from workflow identity, runtime metadata, feature flags, recent handoffs, and prior evidence entries. It attaches a Context Hash to the assembled slice.

`context_graph.py`

Maintains the Context Graph as a directed acyclic graph of context artifacts, hashes, payloads, timestamps, and governed handoff edges. It rejects cycles and returns deterministic lineage using lexicographical topological ordering.

`rlm_compression.py`

Compresses raw sandbox traces into an Artifact Ledger Fold containing attempted actions, failed tools, and idempotency keys.

`failure_budget.py`

Evaluates workflow metrics such as failed write attempts, latency, and stale context detection. It returns directives for autonomy mode, trace sampling, and the next safe action.

`replay_summary.py`

Generates a Replay Summary from the Artifact Ledger Fold, freshness result, failure-budget directive, and Context Graph lineage.

`demo_run.py`

Runs an end-to-end local demonstration of the full Cognitive Shield DS flow.

## Setup

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run The Demo

From the project root:

```bash
python3 01_Cognitive_Shield_DS/demo_run.py
```

Or from inside this folder:

```bash
python3 demo_run.py
```

## Generate The Visual Report

From the project root:

```bash
python3 01_Cognitive_Shield_DS/visual_report.py
```

Then open:

```text
01_Cognitive_Shield_DS/visual_report.html
```

## Expected Demo Checks

The demo should confirm:

- A Context Hash is generated.
- Freshness verification returns `True` for matching hashes.
- A Governing Slice Context Hash is attached.
- Context lineage returns `['node_1', 'node_2']`.
- The Artifact Ledger Fold captures attempted actions, failed tools, and idempotency keys.
- Healthy metrics keep autonomy in `active` mode.
- Breached metrics shift autonomy into `conservative_mode` with `recommendation_only` as the next safe action.
- A Replay Summary reports attempted actions, failure reasons, lineage, and the Next Safe Action.
- The unified Cognitive Shield assessment includes freshness, Artifact Ledger Fold, failure-budget, and Replay Summary outputs.
- Fixture scenario summaries show healthy, stale, failed-write, latency-breach, and branching-handoff behavior.
- The visual report renders scenario cards with status chips, context hashes, lineage, actions, failed tools, and Replay Summary text.

## AWCP Vocabulary

This domain uses the following AWCP concepts:

- `Context Hash`
- `Evidence Ledger`
- `Governing Slice`
- `Context Graph`
- `governed_handoff`
- `Artifact Ledger Fold`
- `Stale Context`
- `Trace Sampling Multiplier`
- `Replay Summary`
- `Conservative Mode`
- `recommendation_only`
