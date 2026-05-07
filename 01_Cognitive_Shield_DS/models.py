from typing import Any, Dict, List, TypedDict


class FreshnessResult(TypedDict):
    is_fresh: bool
    current_context_hash: str
    ledger_context_hash: str
    stale_context_detected: bool


class ArtifactLedgerFold(TypedDict):
    attempted_actions: List[str]
    failed_tools: List[Dict[str, Any]]
    idempotency_keys_used: List[str]


class FailureBudgetDirective(TypedDict):
    budget_breached: bool
    trace_sampling_multiplier: float
    autonomy_mode: str
    next_safe_action: str


class ReplaySummary(TypedDict):
    attempted_actions: List[str]
    failed_tools: List[Dict[str, Any]]
    failure_reasons: List[str]
    context_lineage: List[str]
    next_safe_action: str
    summary: str


class CognitiveShieldAssessment(TypedDict):
    workflow_identity: str
    governing_slice: Dict[str, Any]
    context_hash: str
    freshness: FreshnessResult
    artifact_ledger_fold: ArtifactLedgerFold
    failure_budget: FailureBudgetDirective
    replay_summary: ReplaySummary

