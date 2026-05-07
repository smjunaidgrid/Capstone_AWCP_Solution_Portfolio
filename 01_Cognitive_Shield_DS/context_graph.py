from typing import Any, Dict, List, Set, Tuple

class ContextGraphManager:
    """
    Models agent memory and state transitions as a Directed Acyclic Graph (DAG).
    Maintains a DAG of context artifacts, hashes, and checkpoints across a workflow.
    """
    
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: Dict[Tuple[str, str], Dict[str, str]] = {}
        self.parents: Dict[str, Set[str]] = {}
        self.children: Dict[str, Set[str]] = {}

    def add_context_node(self, node_id: str, context_hash: str, payload: Dict[str, Any]):
        """
        Adds a new state artifact to the DAG.
        """
        self.nodes[node_id] = {
            "context_hash": context_hash,
            "payload": payload,
            "timestamp": payload.get("timestamp"),
        }
        self.parents.setdefault(node_id, set())
        self.children.setdefault(node_id, set())

    def link_handoff(self, source_node_id: str, target_node_id: str, relationship: str = "governed_handoff"):
        """
        Creates an edge representing a transition or handoff between agents/states.
        """
        self._ensure_node_exists(source_node_id)
        self._ensure_node_exists(target_node_id)

        self.edges[(source_node_id, target_node_id)] = {"type": relationship}
        self.parents[target_node_id].add(source_node_id)
        self.children[source_node_id].add(target_node_id)

        if self._path_exists(target_node_id, source_node_id):
            self.edges.pop((source_node_id, target_node_id), None)
            self.parents[target_node_id].discard(source_node_id)
            self.children[source_node_id].discard(target_node_id)
            raise ValueError("Context Graph must remain a Directed Acyclic Graph")

    def get_lineage(self, node_id: str) -> List[str]:
        """
        Retrieves the deterministic path of execution leading to a specific context node.
        Crucial for generating Replay Summaries.
        """
        if node_id not in self.nodes:
            return []

        lineage_node_ids = self._collect_ancestors(node_id) | {node_id}
        in_degree = {
            candidate_id: len(self.parents[candidate_id] & lineage_node_ids)
            for candidate_id in lineage_node_ids
        }
        ready = sorted(
            candidate_id
            for candidate_id, degree in in_degree.items()
            if degree == 0
        )

        ordered_lineage = []
        while ready:
            current_id = ready.pop(0)
            ordered_lineage.append(current_id)

            for child_id in sorted(self.children[current_id] & lineage_node_ids):
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    ready.append(child_id)
                    ready.sort()

        return ordered_lineage

    def get_edge(self, source_node_id: str, target_node_id: str) -> Dict[str, str]:
        """
        Returns metadata for a governed handoff edge.
        """
        return self.edges[(source_node_id, target_node_id)]

    def _ensure_node_exists(self, node_id: str):
        if node_id not in self.nodes:
            self.add_context_node(node_id, "", {})

    def _collect_ancestors(self, node_id: str) -> Set[str]:
        ancestors: Set[str] = set()
        pending = list(self.parents.get(node_id, set()))

        while pending:
            current_id = pending.pop()
            if current_id in ancestors:
                continue
            ancestors.add(current_id)
            pending.extend(self.parents.get(current_id, set()))

        return ancestors

    def _path_exists(self, source_node_id: str, target_node_id: str) -> bool:
        pending = [source_node_id]
        visited = set()

        while pending:
            current_id = pending.pop()
            if current_id == target_node_id:
                return True
            if current_id in visited:
                continue
            visited.add(current_id)
            pending.extend(self.children.get(current_id, set()))

        return False
