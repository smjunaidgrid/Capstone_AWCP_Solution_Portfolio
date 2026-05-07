from typing import Dict, Any

from models import FailureBudgetDirective

class FailureBudgetCalculator:
    """
    Calculates dynamic thresholds for API timeouts, errors, and logic loops.
    Triggers Trace Sampling Multipliers and Conservative Mode shifts.
    """
    
    def __init__(self, error_threshold: int = 3, latency_ceiling_ms: int = 5000):
        self.error_threshold = error_threshold
        self.latency_ceiling_ms = latency_ceiling_ms

    def evaluate_budget(self, workflow_metrics: Dict[str, Any]) -> FailureBudgetDirective:
        """
        Evaluates current execution metrics against the budget. 
        Returns directives for the Policy Engine (OPA) and Orchestrator.
        """
        failed_attempts = workflow_metrics.get("failed_write_attempts", 0)
        avg_latency = workflow_metrics.get("avg_latency_ms", 0)
        has_stale_context = workflow_metrics.get("stale_context_detected", False)
        
        response: FailureBudgetDirective = {
            "budget_breached": False,
            "trace_sampling_multiplier": 1.0,
            "autonomy_mode": "active",
            "next_safe_action": "continue"
        }
        
        # Multi-signal triggers can increase trace sampling, tighten limits, switch to safer profiles, 
        # and move a branch to recommendation-only mode.
        if failed_attempts >= self.error_threshold or avg_latency > self.latency_ceiling_ms or has_stale_context:
            response["budget_breached"] = True
            response["trace_sampling_multiplier"] = 100.0  # Spike capture depth to 100%
            response["autonomy_mode"] = "conservative_mode"
            response["next_safe_action"] = "recommendation_only"
            
        return response
