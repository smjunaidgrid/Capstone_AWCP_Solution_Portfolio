import json
from pathlib import Path
from typing import Any, Dict, List

from cognitive_shield import CognitiveShield
from context_graph import ContextGraphManager
from hashing_engine import HashingEngine
from models import CognitiveShieldAssessment


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def load_scenario(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def list_scenario_paths(fixture_dir: Path = FIXTURE_DIR) -> List[Path]:
    return sorted(fixture_dir.glob("*.json"))


def run_scenario(scenario: Dict[str, Any]) -> CognitiveShieldAssessment:
    graph_manager = ContextGraphManager()

    for node in scenario.get("graph_seed_nodes", []):
        graph_manager.add_context_node(
            node["node_id"],
            node.get("context_hash", ""),
            node.get("payload", {}),
        )

    for edge in scenario.get("graph_seed_edges", []):
        graph_manager.link_handoff(
            edge["source"],
            edge["target"],
            edge.get("relationship", "governed_handoff"),
        )

    ledger_context_hash = scenario.get("ledger_context_hash")
    if ledger_context_hash is None and "ledger_context_payload" in scenario:
        ledger_context_hash = HashingEngine.generate_context_hash(
            scenario["ledger_context_payload"]
        )

    shield = CognitiveShield(graph_manager=graph_manager)
    return shield.evaluate_workflow_state(
        workflow_identity=scenario["workflow_identity"],
        runtime_metadata=scenario.get("runtime_metadata", {}),
        feature_flags=scenario.get("feature_flags", {}),
        recent_handoffs=scenario.get("recent_handoffs", []),
        prior_evidence=scenario.get("prior_evidence", []),
        raw_sandbox_traces=scenario.get("raw_sandbox_traces", []),
        workflow_metrics=scenario.get("workflow_metrics", {}),
        ledger_context_hash=ledger_context_hash,
        context_node_id=scenario.get("context_node_id"),
        parent_context_node_id=scenario.get("parent_context_node_id"),
    )


def run_all_scenarios(fixture_dir: Path = FIXTURE_DIR) -> List[Dict[str, Any]]:
    results = []

    for path in list_scenario_paths(fixture_dir):
        scenario = load_scenario(path)
        assessment = run_scenario(scenario)
        results.append(
            {
                "scenario_id": scenario.get("scenario_id", path.stem),
                "title": scenario.get("title", path.stem),
                "description": scenario.get("description", ""),
                "assessment": assessment,
            }
        )

    return results


def build_console_summary(result: Dict[str, Any]) -> str:
    assessment = result["assessment"]
    failure_budget = assessment["failure_budget"]
    freshness = assessment["freshness"]
    replay_summary = assessment["replay_summary"]

    return (
        f"{result['title']}: "
        f"fresh={freshness['is_fresh']} | "
        f"mode={failure_budget['autonomy_mode']} | "
        f"next={failure_budget['next_safe_action']} | "
        f"lineage={replay_summary['context_lineage']}"
    )


if __name__ == "__main__":
    for scenario_result in run_all_scenarios():
        print(build_console_summary(scenario_result))
