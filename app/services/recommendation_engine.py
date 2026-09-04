from typing import List, Dict, Set, Optional, Tuple
from app.graph.engine import KnowledgeGraph
from app.graph.models import ConceptNode
from app.graph.exceptions import ConceptNotFoundError
from app.services.analytics_engine import AnalyticsEngine
from app.models.recommendation_schemas import (
    RecommendedTopic,
    RecommendationResult
)


class RecommendationEngine:
    """
    Intelligent Dynamic Learning Path Recommendation Engine.
    Combines prerequisite readiness, bottleneck unlock impact, target proximity,
    and student mastery to generate practical, personalized study sequences.
    """

    @classmethod
    def generate_recommendations(
        cls,
        graph: KnowledgeGraph,
        known_concept_ids: List[str],
        target_concept_id: Optional[str] = None,
        max_recommendations: int = 5
    ) -> RecommendationResult:
        """
        Generates a personalized, prioritized learning path for a student based on current knowledge.
        """
        all_nodes = graph.get_all_nodes()
        total_concepts = len(all_nodes)

        if total_concepts == 0:
            return RecommendationResult(
                target_concept_id=target_concept_id,
                student_mastery_percentage=0.0,
                total_concepts_in_curriculum=0,
                known_concepts_count=0,
                ready_now_count=0,
                recommended_path=[],
                upcoming_next=[]
            )

        known_set = set(cid.strip() for cid in known_concept_ids if graph.has_concept(cid.strip()))
        known_count = len(known_set)

        mastery_pct = round((known_count / total_concepts) * 100.0, 1)

        # Validate target concept if specified
        target_ancestors: Set[str] = set()
        if target_concept_id:
            target_node = graph.get_concept(target_concept_id)
            if not target_node:
                raise ConceptNotFoundError(target_concept_id)
            target_ancestors = AnalyticsEngine._get_all_ancestors(graph, target_concept_id)

        # Evaluate all unmastered candidate concepts
        unmastered_nodes = [node for node in all_nodes if node.id not in known_set]

        recommended_now: List[RecommendedTopic] = []
        upcoming_next: List[RecommendedTopic] = []

        max_downstream = max(1, total_concepts - 1)

        for candidate in unmastered_nodes:
            prereqs = graph.get_prerequisites(candidate.id)
            total_prereqs = len(prereqs)

            if total_prereqs == 0:
                satisfied_prereqs = 0
                readiness_ratio = 1.0
                unmet_count = 0
            else:
                satisfied_prereqs = sum(1 for p in prereqs if p.id in known_set)
                readiness_ratio = satisfied_prereqs / total_prereqs
                unmet_count = total_prereqs - satisfied_prereqs

            readiness_pct = round(readiness_ratio * 100.0, 1)

            # Downstream unlock impact among unmastered concepts
            descendants = AnalyticsEngine._get_all_descendants(graph, candidate.id)
            unmastered_descendants = descendants.difference(known_set)
            unmastered_descendants.discard(candidate.id)
            downstream_unlocked = len(unmastered_descendants)

            unlock_ratio = min(1.0, downstream_unlocked / max_downstream)

            # Target Proximity
            target_proximity_score = 0.2
            if target_concept_id:
                if candidate.id == target_concept_id:
                    target_proximity_score = 1.0
                elif candidate.id in target_ancestors:
                    target_proximity_score = 0.8

            # Combined Score Formula
            final_score = (
                0.45 * readiness_ratio +
                0.30 * unlock_ratio +
                0.15 * target_proximity_score +
                0.10 * (1.0 - (candidate.metadata.get("unit_number", 1) / 20.0))
            )
            final_score = round(min(1.0, max(0.0, final_score)), 3)

            # Classification & Reasoning
            if readiness_ratio == 1.0:
                status = "NOW"
                reason = cls._generate_reason_now(candidate, downstream_unlocked, target_concept_id, candidate.id in target_ancestors)
                item = RecommendedTopic(
                    concept=candidate,
                    score=final_score,
                    status=status,
                    readiness_percentage=readiness_pct,
                    downstream_unlocked_count=downstream_unlocked,
                    unmet_prerequisites_count=unmet_count,
                    recommendation_reason=reason
                )
                recommended_now.append(item)

            elif readiness_ratio >= 0.50:
                status = "NEXT"
                reason = f"Almost ready! Requires only {unmet_count} more prerequisite topic to unlock."
                item = RecommendedTopic(
                    concept=candidate,
                    score=final_score,
                    status=status,
                    readiness_percentage=readiness_pct,
                    downstream_unlocked_count=downstream_unlocked,
                    unmet_prerequisites_count=unmet_count,
                    recommendation_reason=reason
                )
                upcoming_next.append(item)

        # Sort recommendations by final score descending
        recommended_now.sort(key=lambda x: x.score, reverse=True)
        upcoming_next.sort(key=lambda x: x.score, reverse=True)

        return RecommendationResult(
            target_concept_id=target_concept_id,
            student_mastery_percentage=mastery_pct,
            total_concepts_in_curriculum=total_concepts,
            known_concepts_count=known_count,
            ready_now_count=len(recommended_now),
            recommended_path=recommended_now[:max_recommendations],
            upcoming_next=upcoming_next[:max_recommendations]
        )

    @staticmethod
    def _generate_reason_now(
        node: ConceptNode,
        downstream_unlocked: int,
        target_concept_id: Optional[str],
        is_target_ancestor: bool
    ) -> str:
        """Generates clear, practical, non-jargon recommendation reasons."""
        if target_concept_id and node.id == target_concept_id:
            return f"You are 100% ready to study your target goal: '{node.name}'!"

        if is_target_ancestor:
            return f"You are 100% ready for '{node.name}'. This is a direct prerequisite required to reach your target goal."

        if downstream_unlocked >= 3:
            return f"You are 100% ready for '{node.name}'. Mastering this key topic unlocks {downstream_unlocked} downstream concepts!"

        if downstream_unlocked > 0:
            return f"You are 100% ready for '{node.name}', which unlocks {downstream_unlocked} next topics in your study path."

        return f"You have satisfied all prerequisites for '{node.name}'. Ready to learn!"
