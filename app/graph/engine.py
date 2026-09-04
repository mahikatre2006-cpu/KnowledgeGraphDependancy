from typing import Dict, List, Set, Optional, Any
from app.graph.models import ConceptNode, DependencyEdge
from app.graph.exceptions import (
    ConceptNotFoundError,
    DuplicateConceptError,
    SelfLoopError,
    InvalidDependencyError
)


class KnowledgeGraph:
    """
    In-Memory Knowledge Graph Engine.
    Manages concepts (nodes) and directed prerequisite relationships (edges).
    Uses Adjacency Lists for efficient graph operations.
    """
    def __init__(self):
        # Map concept_id -> ConceptNode object
        self._nodes: Dict[str, ConceptNode] = {}

        # Outgoing edges: prereq_id -> Dict[dependent_id, DependencyEdge]
        self._outgoing: Dict[str, Dict[str, DependencyEdge]] = {}

        # Incoming edges: dependent_id -> Dict[prereq_id, DependencyEdge]
        self._incoming: Dict[str, Dict[str, DependencyEdge]] = {}

    def add_concept(
        self,
        id: str,
        name: str,
        unit: str = "",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConceptNode:
        """Adds a new concept node to the knowledge graph."""
        if not id or not id.strip():
            raise ValueError("Concept ID cannot be empty.")
        clean_id = id.strip()
        if clean_id in self._nodes:
            raise DuplicateConceptError(clean_id)

        node = ConceptNode(
            id=clean_id,
            name=name.strip(),
            unit=unit.strip(),
            description=description.strip(),
            metadata=metadata or {}
        )
        self._nodes[clean_id] = node
        self._outgoing[clean_id] = {}
        self._incoming[clean_id] = {}
        return node

    def get_concept(self, id: str) -> Optional[ConceptNode]:
        """Returns the concept node with the given ID, or None if not found."""
        return self._nodes.get(id.strip())

    def has_concept(self, id: str) -> bool:
        """Returns True if the concept ID exists in the graph."""
        return id.strip() in self._nodes

    def remove_concept(self, id: str) -> bool:
        """Removes a concept node and all connected incoming and outgoing edges."""
        clean_id = id.strip()
        if clean_id not in self._nodes:
            raise ConceptNotFoundError(clean_id)

        # Remove all outgoing edges from this node to dependent nodes
        for dependent_id in list(self._outgoing[clean_id].keys()):
            del self._incoming[dependent_id][clean_id]
        del self._outgoing[clean_id]

        # Remove all incoming edges to this node from prerequisite nodes
        for prereq_id in list(self._incoming[clean_id].keys()):
            del self._outgoing[prereq_id][clean_id]
        del self._incoming[clean_id]

        # Remove node itself
        del self._nodes[clean_id]
        return True

    def add_dependency(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str = "prerequisite",
        confidence: float = 1.0,
        reason: str = ""
    ) -> DependencyEdge:
        """
        Creates a directed dependency edge: source_id (prerequisite) -> target_id (dependent).
        """
        src = source_id.strip()
        tgt = target_id.strip()

        if src == tgt:
            raise SelfLoopError(src)
        if src not in self._nodes:
            raise ConceptNotFoundError(src)
        if tgt not in self._nodes:
            raise ConceptNotFoundError(tgt)

        edge = DependencyEdge(
            source_id=src,
            target_id=tgt,
            relationship_type=relationship_type,
            confidence=confidence,
            reason=reason
        )

        self._outgoing[src][tgt] = edge
        self._incoming[tgt][src] = edge
        return edge

    def has_dependency(self, source_id: str, target_id: str) -> bool:
        """Checks if a directed edge exists from source_id to target_id."""
        src = source_id.strip()
        tgt = target_id.strip()
        return src in self._outgoing and tgt in self._outgoing[src]

    def remove_dependency(self, source_id: str, target_id: str) -> bool:
        """Removes a directed dependency edge from source_id to target_id."""
        src = source_id.strip()
        tgt = target_id.strip()
        if not self.has_dependency(src, tgt):
            raise InvalidDependencyError(f"Dependency from '{src}' to '{tgt}' does not exist.")

        del self._outgoing[src][tgt]
        del self._incoming[tgt][src]
        return True

    def get_prerequisites(self, concept_id: str) -> List[ConceptNode]:
        """Returns all immediate prerequisite concept nodes for the given topic."""
        cid = concept_id.strip()
        if cid not in self._nodes:
            raise ConceptNotFoundError(cid)
        prereq_ids = self._incoming[cid].keys()
        return [self._nodes[pid] for pid in prereq_ids]

    def get_dependents(self, concept_id: str) -> List[ConceptNode]:
        """Returns all immediate downstream concept nodes that depend on the given topic."""
        cid = concept_id.strip()
        if cid not in self._nodes:
            raise ConceptNotFoundError(cid)
        dependent_ids = self._outgoing[cid].keys()
        return [self._nodes[did] for did in dependent_ids]

    def get_in_degree(self, concept_id: str) -> int:
        """Returns the number of incoming prerequisite edges for a concept."""
        cid = concept_id.strip()
        if cid not in self._nodes:
            raise ConceptNotFoundError(cid)
        return len(self._incoming[cid])

    def get_out_degree(self, concept_id: str) -> int:
        """Returns the number of outgoing dependent edges for a concept."""
        cid = concept_id.strip()
        if cid not in self._nodes:
            raise ConceptNotFoundError(cid)
        return len(self._outgoing[cid])

    def get_all_nodes(self) -> List[ConceptNode]:
        """Returns all concept nodes in the graph."""
        return list(self._nodes.values())

    def get_all_edges(self) -> List[DependencyEdge]:
        """Returns all directed dependency edges in the graph."""
        edges = []
        for src_dict in self._outgoing.values():
            edges.extend(src_dict.values())
        return edges

    def node_count(self) -> int:
        """Returns total number of nodes."""
        return len(self._nodes)

    def edge_count(self) -> int:
        """Returns total number of edges."""
        return sum(len(d) for d in self._outgoing.values())

    def clear(self):
        """Clears all nodes and edges from the graph."""
        self._nodes.clear()
        self._outgoing.clear()
        self._incoming.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes graph to a JSON-compatible dictionary."""
        return {
            "nodes": [node.model_dump() for node in self._nodes.values()],
            "edges": [edge.model_dump() for edge in self.get_all_edges()]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeGraph":
        """Instantiates a KnowledgeGraph from a serialized dictionary."""
        graph = cls()
        for node_data in data.get("nodes", []):
            graph.add_concept(**node_data)
        for edge_data in data.get("edges", []):
            graph.add_dependency(**edge_data)
        return graph
