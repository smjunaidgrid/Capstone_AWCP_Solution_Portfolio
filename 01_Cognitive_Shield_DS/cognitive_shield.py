from typing import Any, Dict, List

from context_graph import ContextGraphManager
from failure_budget import FailureBudgetCalculator
from hashing_engine import HashingEngine
from models import CognitiveShieldAssessment, FreshnessResult
from replay_summary import ReplaySummaryGenerator
from rlm_compression import RLMCompressionEngine
from state_assembly import StateAssembly


class CognitiveShield:
    """
    Unified DS pipeline for evaluating workflow state before execution continues.
    """

    def __init__(
        self,
        graph_manager: ContextGraphManager | None = None,
        budget_calculator: FailureBudgetCalculator | None = None,
        compression_engine: RLMCompressionEngine | None = None,
        replay_summary_generator: ReplaySummaryGenerator | None = None,
    ):
        self.graph_manager = graph_manager or ContextGraphManager()
        self.budget_calculator = budget_calculator or FailureBudgetCalculator()
        self.compression_engine = compression_engine or RLMCompressionEngine()
        self.replay_summary_generator = replay_summary_generator or ReplaySummaryGenerator()

    def evaluate_workflow_state(
        self,
        workflow_identity: str,
        runtime_metadata: Dict[str, Any],
        feature_flags: Dict[str, bool],
        recent_handoffs: List[Dict[str, Any]],
        prior_evidence: List[Dict[str, Any]],
        raw_sandbox_traces: List[Dict[str, Any]],
        workflow_metrics: Dict[str, Any],
        ledger_context_hash: str | None = None,
        context_node_id: str | None = None,
        parent_context_node_id: str | None = None,
    ) -> CognitiveShieldAssessment:
        governing_slice = StateAssembly.build_governing_slice(
            workflow_identity=workflow_identity,
            runtime_metadata=runtime_metadata,
            feature_flags=feature_flags,
            recent_handoffs=recent_handoffs,
            prior_evidence=prior_evidence,
        )

        context_hash = governing_slice["context_hash"]
        expected_hash = ledger_context_hash or context_hash
        is_fresh = HashingEngine.verify_freshness(context_hash, expected_hash)
        freshness: FreshnessResult = {
            "is_fresh": is_fresh,
            "current_context_hash": context_hash,
            "ledger_context_hash": expected_hash,
            "stale_context_detected": not is_fresh,
        }

        metrics_with_freshness = {
            **workflow_metrics,
            "stale_context_detected": workflow_metrics.get(
                "stale_context_detected",
                freshness["stale_context_detected"],
            ),
        }

        artifact_ledger_fold = self.compression_engine.generate_artifact_ledger_fold(
            raw_sandbox_traces
        )
        failure_budget = self.budget_calculator.evaluate_budget(metrics_with_freshness)

        context_lineage: List[str] = []
        if context_node_id:
            self.graph_manager.add_context_node(
                context_node_id,
                context_hash,
                {
                    "timestamp": runtime_metadata.get("timestamp"),
                    "workflow_identity": workflow_identity,
                },
            )
            if parent_context_node_id:
                self.graph_manager.link_handoff(parent_context_node_id, context_node_id)
            context_lineage = self.graph_manager.get_lineage(context_node_id)

        replay_summary = self.replay_summary_generator.generate_summary(
            artifact_ledger_fold=artifact_ledger_fold,
            failure_budget_directive=failure_budget,
            freshness=freshness,
            context_lineage=context_lineage,
        )

        return {
            "workflow_identity": workflow_identity,
            "governing_slice": governing_slice,
            "context_hash": context_hash,
            "freshness": freshness,
            "artifact_ledger_fold": artifact_ledger_fold,
            "failure_budget": failure_budget,
            "replay_summary": replay_summary,
        }
