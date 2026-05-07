from typing import Dict, List, Any
from hashing_engine import HashingEngine

class StateAssembly:
    """
    Responsible for assembling the Governing Slice (minimum metadata/flags required for policy judgment).
    """
    
    @staticmethod
    def build_governing_slice(
        workflow_identity: str,
        runtime_metadata: Dict[str, Any],
        feature_flags: Dict[str, bool],
        recent_handoffs: List[Dict[str, Any]],
        prior_evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Assembles only the minimum state needed to judge one branch and one action before execution.
        Keeps the payload within the target 4K-16K governing slice range.
        """
        
        governing_slice = {
            "workflow_identity": workflow_identity,
            "owner": runtime_metadata.get("owner", "unknown"),
            "active_flags": feature_flags,
            "recent_handoffs": recent_handoffs[-3:], # Keep only the most recent bounds
            "prior_evidence_summary": prior_evidence[-5:],
            "runtime_environment": runtime_metadata.get("environment", "local_prototype")
        }
        
        # Attach the Context Hash for ledger immutability
        governing_slice["context_hash"] = HashingEngine.generate_context_hash(governing_slice)
        
        return governing_slice
