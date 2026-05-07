from typing import Any, Dict

from cognitive_shield import CognitiveShield


def build_assessment_from_backend_signal(
    workflow_identity: str,
    agent_id: str,
    runtime_type: str,
    code_to_run: str,
    idempotency_key: str,
    sandbox_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Adapts backend sandbox output into the Cognitive Shield DS assessment contract.
    """
    status = sandbox_result.get("status", "failed")
    failed = status != "success"
    duration_ms = sandbox_result.get("duration_ms", 0)
    tool_name = _infer_tool_name(code_to_run)

    raw_sandbox_traces = [
        {
            "type": "tool_call",
            "tool_name": tool_name,
            "status": "error" if failed else "success",
            "error_message": sandbox_result.get("error", ""),
            "idempotency_key": idempotency_key,
        }
    ]

    shield = CognitiveShield()
    return shield.evaluate_workflow_state(
        workflow_identity=workflow_identity,
        runtime_metadata={
            "owner": agent_id,
            "environment": runtime_type,
            "duration_ms": duration_ms,
        },
        feature_flags={
            "stale_context_guard": True,
            "trace_sampling": True,
        },
        recent_handoffs=[],
        prior_evidence=[
            {
                "event": "sandbox_execution_completed",
                "status": status,
            }
        ],
        raw_sandbox_traces=raw_sandbox_traces,
        workflow_metrics={
            "failed_write_attempts": 1 if failed and tool_name.startswith("write") else 0,
            "avg_latency_ms": duration_ms,
        },
        context_node_id=f"{workflow_identity}-cognitive-shield",
    )


def _infer_tool_name(code_to_run: str) -> str:
    lowered_code = code_to_run.lower()
    if "open(" in lowered_code or "write" in lowered_code:
        return "write_codeact_sandbox"
    return "run_codeact_sandbox"
