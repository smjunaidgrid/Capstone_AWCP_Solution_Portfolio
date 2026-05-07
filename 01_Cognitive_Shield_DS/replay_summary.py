from typing import Any, Dict, List

from models import ReplaySummary


class ReplaySummaryGenerator:
    """
    Builds a human-readable Replay Summary from DS signals.
    """

    @staticmethod
    def generate_summary(
        artifact_ledger_fold: Dict[str, Any],
        failure_budget_directive: Dict[str, Any],
        freshness: Dict[str, Any],
        context_lineage: List[str] | None = None,
    ) -> ReplaySummary:
        attempted_actions = artifact_ledger_fold.get("attempted_actions", [])
        failed_tools = artifact_ledger_fold.get("failed_tools", [])
        next_safe_action = failure_budget_directive.get("next_safe_action", "continue")

        stale_context_detected = not freshness.get("is_fresh", True)
        failure_reasons = []

        if stale_context_detected:
            failure_reasons.append("Stale Context detected against the Evidence Ledger")
        if failed_tools:
            failure_reasons.append("One or more tool calls failed")
        if failure_budget_directive.get("budget_breached", False):
            failure_reasons.append("Failure budget breached")

        summary_text = ReplaySummaryGenerator._build_summary_text(
            attempted_actions=attempted_actions,
            failed_tools=failed_tools,
            next_safe_action=next_safe_action,
            failure_reasons=failure_reasons,
        )

        return {
            "attempted_actions": attempted_actions,
            "failed_tools": failed_tools,
            "failure_reasons": failure_reasons,
            "context_lineage": context_lineage or [],
            "next_safe_action": next_safe_action,
            "summary": summary_text,
        }

    @staticmethod
    def _build_summary_text(
        attempted_actions: List[str],
        failed_tools: List[Dict[str, Any]],
        next_safe_action: str,
        failure_reasons: List[str],
    ) -> str:
        action_text = ", ".join(attempted_actions) if attempted_actions else "no tool actions"
        failed_text = ", ".join(item.get("tool", "unknown_tool") for item in failed_tools)

        if not failure_reasons:
            return (
                f"The agent attempted {action_text}. No blocking failures were detected. "
                f"Next Safe Action: {next_safe_action}."
            )

        failure_text = "; ".join(failure_reasons)
        tool_text = f" Failed tools: {failed_text}." if failed_text else ""
        return (
            f"The agent attempted {action_text}. {failure_text}.{tool_text} "
            f"Next Safe Action: {next_safe_action}."
        )
