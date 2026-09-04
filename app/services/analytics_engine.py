from typing import List, Dict, Set, Any
from collections import deque
from app.graph.engine import KnowledgeGraph
from app.graph.models import ConceptNode
from app.graph.exceptions import ConceptNotFoundError
from app.services.sequence_engine import SequenceEngine
from app.models.analytics_schemas import (
    MissingPrerequisitesResponse,
    BottleneckItem,
    BottlenecksResponse,
    ReadinessResponse
)


class AnalyticsEngine:
    """
    Knowledge Graph Analytics Engine.
    Implements ancestor set traversal for missing prerequisite discovery,
    reachability centrality analysis for learning bottleneck detection,
    and student readiness evaluation.
    """

    @classmethod
    def get_missing_prerequisites(
        cls,
        graph: KnowledgeGraph,
        target_concept_id: str,
        known_concept_ids: List[str]
    ) -> MissingPrerequisitesResponse:
        r"""
        Calculates missing prerequisite concepts for a student targeting a specific concept.
        Mathematical Formulation: Missing(T, K) = Ancestors(T) \ K
        """
        target_node = graph.get_concept(target_concept_id)
        if not target_node:
            raise ConceptNotFoundError(target_concept_id)

        known_set = set(cid.strip() for cid in known_concept_ids)

        # 1. Compute all ancestor prerequisite nodes of target_concept_id
        ancestor_ids = cls._get_all_ancestors(graph, target_concept_id)
        ancestor_ids.discard(target_concept_id)  # Remove target itself from prerequisites list

        total_prereqs_count = len(ancestor_ids)

        if total_prereqs_count == 0:
            return MissingPrerequisitesResponse(
                target_concept_id=target_concept_id,
                target_concept_name=target_node.name,
                progress_percentage=100.0,
                total_prerequisites_count=0,
                missing_count=0,
                missing_concepts=[],
                known_ancestors=[]
            )

        known_ancestor_ids = ancestor_ids.intersection(known_set)
        missing_ids = ancestor_ids.difference(known_set)

        # 2. Get full topological order of graph to order missing concepts logically
        topological_nodes = SequenceEngine.get_topological_sequence(graph)

        missing_concepts = [node for node in topological_nodes if node.id in missing_ids]
        known_ancestors = [node for node in topological_nodes if node.id in known_ancestor_ids]

        progress_pct = round((len(known_ancestor_ids) / total_prereqs_count) * 100.0, 1)

        return MissingPrerequisitesResponse(
            target_concept_id=target_concept_id,
            target_concept_name=target_node.name,
            progress_percentage=progress_pct,
            total_prerequisites_count=total_prereqs_count,
            missing_count=len(missing_concepts),
            missing_concepts=missing_concepts,
            known_ancestors=known_ancestors
        )

    @classmethod
    def analyze_bottlenecks(cls, graph: KnowledgeGraph, top_n: int = 10) -> BottlenecksResponse:
        """
        Ranks concepts in the graph by their downstream reachability centrality.
        Identifies learning bottlenecks (concepts that unlock the most downstream topics).
        """
        nodes = graph.get_all_nodes()
        total_concepts = len(nodes)
        if total_concepts == 0:
            return BottlenecksResponse(total_concepts=0, bottlenecks=[])

        bottleneck_items: List[BottleneckItem] = []

        max_reachability = max(1, total_concepts - 1)

        for node in nodes:
            # Compute full reachable downstream subgraph
            reachable_ids = cls._get_all_descendants(graph, node.id)
            reachable_ids.discard(node.id)

            downstream_count = len(reachable_ids)
            direct_dependents_count = graph.get_out_degree(node.id)

            # Impact score normalized between 0.0 and 1.0
            impact_score = round(downstream_count / max_reachability, 3)

            desc = f"Mastering '{node.name}' unlocks {downstream_count} downstream topics ({direct_dependents_count} immediate)."

            bottleneck_items.append(
                BottleneckItem(
                    concept=node,
                    downstream_count=downstream_count,
                    direct_dependents_count=direct_dependents_count,
                    unlocked_concept_ids=sorted(list(reachable_ids)),
                    impact_score=impact_score,
                    description=desc
                )
            )

        # Sort descending by downstream reachability count, then direct dependents
        bottleneck_items.sort(key=lambda item: (item.downstream_count, item.direct_dependents_count), reverse=True)

        return BottlenecksResponse(
            total_concepts=total_concepts,
            bottlenecks=bottleneck_items[:top_n]
        )

    @classmethod
    def check_readiness(
        cls,
        graph: KnowledgeGraph,
        concept_id: str,
        known_concept_ids: List[str]
    ) -> ReadinessResponse:
        """
        Checks whether a student has satisfied all immediate prerequisites to start learning concept_id.
        """
        concept_node = graph.get_concept(concept_id)
        if not concept_node:
            raise ConceptNotFoundError(concept_id)

        known_set = set(cid.strip() for cid in known_concept_ids)
        immediate_prereqs = graph.get_prerequisites(concept_id)

        unmet_prereqs = [node for node in immediate_prereqs if node.id not in known_set]
        is_ready = len(unmet_prereqs) == 0

        return ReadinessResponse(
            concept_id=concept_id,
            concept_name=concept_node.name,
            is_ready=is_ready,
            unmet_prerequisites=unmet_prereqs
        )

    @staticmethod
    def _get_all_ancestors(graph: KnowledgeGraph, start_node_id: str) -> Set[str]:
        """BFS backward traversal to collect all ancestor prerequisite node IDs."""
        ancestors: Set[str] = set()
        queue = deque([start_node_id])

        while queue:
            curr_id = queue.popleft()
            ancestors.add(curr_id)
            for prereq in graph.get_prerequisites(curr_id):
                if prereq.id not in ancestors:
                    ancestors.add(prereq.id)
                    queue.append(prereq.id)

        return ancestors

    @staticmethod
    def _get_all_descendants(graph: KnowledgeGraph, start_node_id: str) -> Set[str]:
        """BFS forward traversal to collect all downstream descendant node IDs."""
        descendants: Set[str] = set()
        queue = deque([start_node_id])

        while queue:
            curr_id = queue.popleft()
            descendants.add(curr_id)
            for dependent in graph.get_dependents(curr_id):
                if dependent.id not in descendants:
                    descendants.add(dependent.id)
                    queue.append(dependent.id)

        return descendants
