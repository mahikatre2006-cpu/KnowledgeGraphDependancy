from typing import List, Dict, Set, Optional
from collections import deque
from app.graph.engine import KnowledgeGraph
from app.graph.models import ConceptNode
from app.graph.exceptions import ConceptNotFoundError, CycleDetectedError


class SequenceEngine:
    """
    Learning Sequence Engine.
    Handles graph traversal, cycle detection, topological sorting,
    and prerequisite chain resolution for the Knowledge Graph.
    """

    @staticmethod
    def find_cycle(graph: KnowledgeGraph) -> Optional[List[str]]:
        """
        Detects circular dependencies in the graph using DFS Graph Coloring.
        States:
            0 (WHITE) = Unvisited
            1 (GRAY)  = Currently visiting (in recursion stack)
            2 (BLACK) = Visited & completed

        Returns:
            List[str] representing the cycle path (e.g. ['A', 'B', 'C', 'A']),
            or None if the graph is a valid Directed Acyclic Graph (DAG).
        """
        nodes = graph.get_all_nodes()
        if not nodes:
            return None

        state: Dict[str, int] = {node.id: 0 for node in nodes}
        parent: Dict[str, Optional[str]] = {node.id: None for node in nodes}
        cycle_path: List[str] = []

        def dfs(node_id: str) -> bool:
            state[node_id] = 1  # Mark GRAY (visiting)

            for dependent_node in graph.get_dependents(node_id):
                dep_id = dependent_node.id
                if state[dep_id] == 1:
                    # Found a back-edge! Reconstruct cycle path
                    cycle_nodes = [dep_id]
                    curr = node_id
                    while curr and curr != dep_id:
                        cycle_nodes.append(curr)
                        curr = parent.get(curr)
                    cycle_nodes.append(dep_id)
                    cycle_nodes.reverse()
                    nonlocal cycle_path
                    cycle_path = cycle_nodes
                    return True
                elif state[dep_id] == 0:
                    parent[dep_id] = node_id
                    if dfs(dep_id):
                        return True

            state[node_id] = 2  # Mark BLACK (completed)
            return False

        for node in nodes:
            if state[node.id] == 0:
                if dfs(node.id):
                    return cycle_path

        return None

    @classmethod
    def get_topological_sequence(cls, graph: KnowledgeGraph) -> List[ConceptNode]:
        """
        Computes a valid prerequisite-first learning order for all concepts in the graph
        using Kahn's Algorithm (In-Degree BFS).

        Raises:
            CycleDetectedError: If the graph contains circular dependencies.
        """
        cycle = cls.find_cycle(graph)
        if cycle:
            raise CycleDetectedError(cycle)

        all_nodes = graph.get_all_nodes()
        if not all_nodes:
            return []

        # Calculate in-degree for every concept node
        in_degree: Dict[str, int] = {node.id: graph.get_in_degree(node.id) for node in all_nodes}

        # Queue nodes with in-degree 0 (no prerequisites required)
        queue = deque([node.id for node in all_nodes if in_degree[node.id] == 0])

        topological_order: List[ConceptNode] = []

        while queue:
            curr_id = queue.popleft()
            curr_node = graph.get_concept(curr_id)
            if curr_node:
                topological_order.append(curr_node)

            for dependent in graph.get_dependents(curr_id):
                in_degree[dependent.id] -= 1
                if in_degree[dependent.id] == 0:
                    queue.append(dependent.id)

        if len(topological_order) != len(all_nodes):
            # Fallback cycle check
            remaining_cycle = cls.find_cycle(graph) or list(in_degree.keys())
            raise CycleDetectedError(remaining_cycle)

        return topological_order

    @classmethod
    def get_prerequisite_chain(cls, graph: KnowledgeGraph, target_concept_id: str) -> List[ConceptNode]:
        """
        Computes the complete topologically sorted list of prerequisite concepts
        required to reach and master a specific target concept.

        Raises:
            ConceptNotFoundError: If target_concept_id does not exist.
            CycleDetectedError: If the graph contains circular dependencies.
        """
        target_node = graph.get_concept(target_concept_id)
        if not target_node:
            raise ConceptNotFoundError(target_concept_id)

        cycle = cls.find_cycle(graph)
        if cycle:
            raise CycleDetectedError(cycle)

        # Collect all ancestor nodes using BFS/DFS backwards on incoming edges
        ancestors: Set[str] = set()
        queue = deque([target_concept_id])

        while queue:
            curr_id = queue.popleft()
            ancestors.add(curr_id)
            for prereq in graph.get_prerequisites(curr_id):
                if prereq.id not in ancestors:
                    ancestors.add(prereq.id)
                    queue.append(prereq.id)

        # Filter topological sort of the full graph to keep only ancestors & target node
        full_topological = cls.get_topological_sequence(graph)
        return [node for node in full_topological if node.id in ancestors]
