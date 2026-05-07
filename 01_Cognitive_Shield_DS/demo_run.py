from hashing_engine import HashingEngine
from state_assembly import StateAssembly
from context_graph import ContextGraphManager
from rlm_compression import RLMCompressionEngine
from failure_budget import FailureBudgetCalculator
from replay_summary import ReplaySummaryGenerator
from cognitive_shield import CognitiveShield
from scenario_runner import build_console_summary, run_all_scenarios


def run_demo():
    payload = {"agent": "planner", "step": 1}
    context_hash = HashingEngine.generate_context_hash(payload)

    print("Context hash:", context_hash)
    print("Freshness check:", HashingEngine.verify_freshness(context_hash, context_hash))

    slice_payload = StateAssembly.build_governing_slice(
        "awcp-demo",
        {"owner": "local-user", "environment": "local_prototype"},
        {"stale_context_guard": True},
        [{"from": "agent_a", "to": "agent_b"}],
        [{"event": "hash_created"}]
    )

    print("Governing slice context hash:", slice_payload["context_hash"])

    graph = ContextGraphManager()
    graph.add_context_node("node_1", context_hash, {"timestamp": "2026-04-30T00:00:00Z"})
    graph.add_context_node("node_2", slice_payload["context_hash"], {"timestamp": "2026-04-30T00:01:00Z"})
    graph.link_handoff("node_1", "node_2")

    print("Context lineage:", graph.get_lineage("node_2"))

    compressor = RLMCompressionEngine()
    fold = compressor.generate_artifact_ledger_fold([
        {"type": "tool_call", "tool_name": "write_file", "status": "success", "idempotency_key": "abc-123"},
        {"type": "tool_call", "tool_name": "run_tests", "status": "error", "error_message": "timeout"}
    ])

    print("Artifact ledger fold:", fold)

    budget = FailureBudgetCalculator()
    healthy_budget = budget.evaluate_budget({"failed_write_attempts": 0, "avg_latency_ms": 100})
    breached_budget = budget.evaluate_budget({"failed_write_attempts": 3, "avg_latency_ms": 100})
    print("Healthy budget:", healthy_budget)
    print("Breached budget:", breached_budget)

    replay_summary = ReplaySummaryGenerator.generate_summary(
        artifact_ledger_fold=fold,
        failure_budget_directive=breached_budget,
        freshness={
            "is_fresh": False,
            "current_context_hash": slice_payload["context_hash"],
            "ledger_context_hash": context_hash,
            "stale_context_detected": True,
        },
        context_lineage=graph.get_lineage("node_2"),
    )
    print("Replay summary:", replay_summary)

    shield = CognitiveShield(graph_manager=graph)
    assessment = shield.evaluate_workflow_state(
        workflow_identity="awcp-demo",
        runtime_metadata={
            "owner": "local-user",
            "environment": "local_prototype",
            "timestamp": "2026-04-30T00:02:00Z",
        },
        feature_flags={"stale_context_guard": True},
        recent_handoffs=[
            {"from": "agent_a", "to": "agent_b"},
            {"from": "agent_b", "to": "agent_c"},
        ],
        prior_evidence=[{"event": "hash_created"}, {"event": "write_failed"}],
        raw_sandbox_traces=[
            {"type": "tool_call", "tool_name": "write_file", "status": "success", "idempotency_key": "abc-123"},
            {"type": "tool_call", "tool_name": "run_tests", "status": "error", "error_message": "timeout"},
        ],
        workflow_metrics={"failed_write_attempts": 1, "avg_latency_ms": 200},
        ledger_context_hash=context_hash,
        parent_context_node_id="node_2",
        context_node_id="node_3",
    )
    print("Cognitive Shield assessment:", assessment)

    print("\nFixture scenario summaries:")
    for scenario_result in run_all_scenarios():
        print("-", build_console_summary(scenario_result))


if __name__ == "__main__":
    run_demo()
