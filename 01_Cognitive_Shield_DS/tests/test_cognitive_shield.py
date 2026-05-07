import sys
from pathlib import Path


DOMAIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DOMAIN_ROOT))

from context_graph import ContextGraphManager
from cognitive_shield import CognitiveShield
from failure_budget import FailureBudgetCalculator
from hashing_engine import HashingEngine
from replay_summary import ReplaySummaryGenerator
from rlm_compression import RLMCompressionEngine
from scenario_runner import load_scenario, run_all_scenarios, run_scenario
from state_assembly import StateAssembly
from visual_report import build_report


def test_generate_context_hash_is_deterministic():
    first_payload = {"agent": "planner", "step": 1}
    second_payload = {"step": 1, "agent": "planner"}

    first_hash = HashingEngine.generate_context_hash(first_payload)
    second_hash = HashingEngine.generate_context_hash(second_payload)

    assert first_hash == second_hash
    assert len(first_hash) == 64


def test_verify_freshness_detects_matching_and_stale_context():
    current_hash = HashingEngine.generate_context_hash({"state": "current"})
    stale_hash = HashingEngine.generate_context_hash({"state": "stale"})

    assert HashingEngine.verify_freshness(current_hash, current_hash) is True
    assert HashingEngine.verify_freshness(current_hash, stale_hash) is False


def test_build_governing_slice_attaches_context_hash_and_bounds_history():
    recent_handoffs = [
        {"handoff": "one"},
        {"handoff": "two"},
        {"handoff": "three"},
        {"handoff": "four"}
    ]
    prior_evidence = [
        {"event": "one"},
        {"event": "two"},
        {"event": "three"},
        {"event": "four"},
        {"event": "five"},
        {"event": "six"}
    ]

    governing_slice = StateAssembly.build_governing_slice(
        workflow_identity="awcp-demo",
        runtime_metadata={"owner": "local-user", "environment": "local_prototype"},
        feature_flags={"stale_context_guard": True},
        recent_handoffs=recent_handoffs,
        prior_evidence=prior_evidence
    )

    context_hash = governing_slice.pop("context_hash")

    assert governing_slice["workflow_identity"] == "awcp-demo"
    assert governing_slice["owner"] == "local-user"
    assert governing_slice["active_flags"] == {"stale_context_guard": True}
    assert governing_slice["recent_handoffs"] == recent_handoffs[-3:]
    assert governing_slice["prior_evidence_summary"] == prior_evidence[-5:]
    assert context_hash == HashingEngine.generate_context_hash(governing_slice)


def test_context_graph_tracks_governed_handoff_lineage():
    graph = ContextGraphManager()

    graph.add_context_node("node_1", "hash_1", {"timestamp": "2026-04-30T00:00:00Z"})
    graph.add_context_node("node_2", "hash_2", {"timestamp": "2026-04-30T00:01:00Z"})
    graph.link_handoff("node_1", "node_2")

    assert graph.get_lineage("node_2") == ["node_1", "node_2"]
    assert graph.get_edge("node_1", "node_2")["type"] == "governed_handoff"


def test_context_graph_returns_deterministic_lineage_for_branching_dag():
    graph = ContextGraphManager()

    graph.add_context_node("root", "hash_root", {"timestamp": "2026-04-30T00:00:00Z"})
    graph.add_context_node("branch_b", "hash_b", {"timestamp": "2026-04-30T00:01:00Z"})
    graph.add_context_node("branch_a", "hash_a", {"timestamp": "2026-04-30T00:01:00Z"})
    graph.add_context_node("merge", "hash_merge", {"timestamp": "2026-04-30T00:02:00Z"})
    graph.link_handoff("root", "branch_b")
    graph.link_handoff("root", "branch_a")
    graph.link_handoff("branch_b", "merge")
    graph.link_handoff("branch_a", "merge")

    assert graph.get_lineage("merge") == ["root", "branch_a", "branch_b", "merge"]


def test_context_graph_rejects_cycles():
    graph = ContextGraphManager()

    graph.add_context_node("node_1", "hash_1", {})
    graph.add_context_node("node_2", "hash_2", {})
    graph.link_handoff("node_1", "node_2")

    try:
        graph.link_handoff("node_2", "node_1")
    except ValueError as exc:
        assert "Directed Acyclic Graph" in str(exc)
    else:
        raise AssertionError("Expected cycle creation to fail")


def test_rlm_compression_generates_artifact_ledger_fold():
    compressor = RLMCompressionEngine()

    fold = compressor.generate_artifact_ledger_fold([
        {
            "type": "tool_call",
            "tool_name": "write_file",
            "status": "success",
            "idempotency_key": "abc-123"
        },
        {
            "type": "tool_call",
            "tool_name": "run_tests",
            "status": "error",
            "error_message": "timeout"
        }
    ])

    assert fold["attempted_actions"] == ["write_file", "run_tests"]
    assert fold["failed_tools"] == [{"tool": "run_tests", "error": "timeout"}]
    assert fold["idempotency_keys_used"] == ["abc-123"]


def test_failure_budget_keeps_active_mode_for_healthy_metrics():
    calculator = FailureBudgetCalculator()

    response = calculator.evaluate_budget({
        "failed_write_attempts": 0,
        "avg_latency_ms": 100,
        "stale_context_detected": False
    })

    assert response == {
        "budget_breached": False,
        "trace_sampling_multiplier": 1.0,
        "autonomy_mode": "active",
        "next_safe_action": "continue"
    }


def test_failure_budget_shifts_to_conservative_mode_on_breach():
    calculator = FailureBudgetCalculator()

    response = calculator.evaluate_budget({
        "failed_write_attempts": 3,
        "avg_latency_ms": 100,
        "stale_context_detected": False
    })

    assert response == {
        "budget_breached": True,
        "trace_sampling_multiplier": 100.0,
        "autonomy_mode": "conservative_mode",
        "next_safe_action": "recommendation_only"
    }


def test_replay_summary_reports_healthy_workflow():
    summary = ReplaySummaryGenerator.generate_summary(
        artifact_ledger_fold={
            "attempted_actions": ["read_state"],
            "failed_tools": [],
            "idempotency_keys_used": []
        },
        failure_budget_directive={
            "budget_breached": False,
            "next_safe_action": "continue"
        },
        freshness={
            "is_fresh": True,
            "stale_context_detected": False
        },
        context_lineage=["node_1"]
    )

    assert summary["failure_reasons"] == []
    assert summary["next_safe_action"] == "continue"
    assert "No blocking failures" in summary["summary"]


def test_replay_summary_reports_stale_context_failed_write_and_latency_breach():
    summary = ReplaySummaryGenerator.generate_summary(
        artifact_ledger_fold={
            "attempted_actions": ["write_file", "run_tests"],
            "failed_tools": [{"tool": "write_file", "error": "permission denied"}],
            "idempotency_keys_used": ["abc-123"]
        },
        failure_budget_directive={
            "budget_breached": True,
            "next_safe_action": "recommendation_only"
        },
        freshness={
            "is_fresh": False,
            "stale_context_detected": True
        },
        context_lineage=["node_1", "node_2"]
    )

    assert summary["attempted_actions"] == ["write_file", "run_tests"]
    assert "Stale Context detected against the Evidence Ledger" in summary["failure_reasons"]
    assert "One or more tool calls failed" in summary["failure_reasons"]
    assert "Failure budget breached" in summary["failure_reasons"]
    assert summary["next_safe_action"] == "recommendation_only"


def test_cognitive_shield_pipeline_returns_healthy_assessment():
    shield = CognitiveShield()

    assessment = shield.evaluate_workflow_state(
        workflow_identity="awcp-demo",
        runtime_metadata={
            "owner": "local-user",
            "environment": "local_prototype",
            "timestamp": "2026-04-30T00:00:00Z"
        },
        feature_flags={"stale_context_guard": True},
        recent_handoffs=[],
        prior_evidence=[],
        raw_sandbox_traces=[
            {
                "type": "tool_call",
                "tool_name": "read_state",
                "status": "success",
                "idempotency_key": "read-123"
            }
        ],
        workflow_metrics={
            "failed_write_attempts": 0,
            "avg_latency_ms": 100
        },
        context_node_id="node_1"
    )

    assert assessment["workflow_identity"] == "awcp-demo"
    assert assessment["freshness"]["is_fresh"] is True
    assert assessment["failure_budget"]["autonomy_mode"] == "active"
    assert assessment["artifact_ledger_fold"]["idempotency_keys_used"] == ["read-123"]
    assert assessment["replay_summary"]["next_safe_action"] == "continue"


def test_cognitive_shield_pipeline_detects_stale_context_and_failed_write():
    shield = CognitiveShield()
    stale_ledger_hash = HashingEngine.generate_context_hash({"state": "older"})

    assessment = shield.evaluate_workflow_state(
        workflow_identity="awcp-demo",
        runtime_metadata={
            "owner": "local-user",
            "environment": "local_prototype",
            "timestamp": "2026-04-30T00:00:00Z"
        },
        feature_flags={"stale_context_guard": True},
        recent_handoffs=[{"from": "agent_a", "to": "agent_b"}],
        prior_evidence=[{"event": "previous_hash"}],
        raw_sandbox_traces=[
            {
                "type": "tool_call",
                "tool_name": "write_file",
                "status": "error",
                "error_message": "timeout",
                "idempotency_key": "write-123"
            }
        ],
        workflow_metrics={
            "failed_write_attempts": 1,
            "avg_latency_ms": 100
        },
        ledger_context_hash=stale_ledger_hash,
        context_node_id="node_1"
    )

    assert assessment["freshness"]["is_fresh"] is False
    assert assessment["freshness"]["stale_context_detected"] is True
    assert assessment["failure_budget"]["autonomy_mode"] == "conservative_mode"
    assert assessment["failure_budget"]["next_safe_action"] == "recommendation_only"
    assert assessment["artifact_ledger_fold"]["failed_tools"] == [
        {"tool": "write_file", "error": "timeout"}
    ]


def test_cognitive_shield_pipeline_detects_latency_breach():
    shield = CognitiveShield()

    assessment = shield.evaluate_workflow_state(
        workflow_identity="awcp-demo",
        runtime_metadata={"owner": "local-user", "environment": "local_prototype"},
        feature_flags={},
        recent_handoffs=[],
        prior_evidence=[],
        raw_sandbox_traces=[],
        workflow_metrics={
            "failed_write_attempts": 0,
            "avg_latency_ms": 6000
        }
    )

    assert assessment["failure_budget"]["budget_breached"] is True
    assert assessment["failure_budget"]["trace_sampling_multiplier"] == 100.0


def test_fixture_scenarios_generate_expected_assessment_modes():
    results = {
        result["scenario_id"]: result["assessment"]
        for result in run_all_scenarios()
    }

    assert results["healthy_workflow"]["failure_budget"]["autonomy_mode"] == "active"
    assert results["healthy_workflow"]["freshness"]["is_fresh"] is True
    assert results["stale_context_workflow"]["freshness"]["is_fresh"] is False
    assert results["stale_context_workflow"]["failure_budget"]["autonomy_mode"] == "conservative_mode"
    assert results["failed_write_workflow"]["artifact_ledger_fold"]["failed_tools"] == [
        {"tool": "write_file", "error": "permission denied"},
        {"tool": "write_file", "error": "timeout"}
    ]
    assert results["latency_breach_workflow"]["failure_budget"]["budget_breached"] is True


def test_branching_fixture_reports_deterministic_lineage():
    scenario_path = DOMAIN_ROOT / "fixtures" / "branching_handoff_workflow.json"
    assessment = run_scenario(load_scenario(scenario_path))

    assert assessment["replay_summary"]["context_lineage"] == [
        "root",
        "branch_a",
        "branch_b",
        "merge"
    ]


def test_visual_report_contains_core_ds_sections():
    report = build_report(run_all_scenarios())

    assert "Cognitive Shield DS Visual Report" in report
    assert "Healthy Workflow" in report
    assert "Stale Context Workflow" in report
    assert "Context Hashes" in report
    assert "Replay Summary" in report
