import hashlib
import json
from typing import Any, Dict

class HashingEngine:
    """
    Generates SHA-256 Context Hashes of agent memory and state artifacts.
    Ensures deterministic hashing for the Evidence Ledger.
    """
    
    @staticmethod
    def generate_context_hash(state_payload: Dict[str, Any]) -> str:
        """
        Creates a deterministic SHA-256 hash of the agent's current memory/state.
        """
        # Sort keys to guarantee deterministic hashing regardless of dictionary order
        serialized_state = json.dumps(state_payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(serialized_state.encode('utf-8')).hexdigest()

    @staticmethod
    def verify_freshness(current_hash: str, ledger_hash: str) -> bool:
        """
        Compares the current Context Hash against the Evidence Ledger.
        Returns False if a Stale Context is detected.
        """
        return current_hash == ledger_hash
