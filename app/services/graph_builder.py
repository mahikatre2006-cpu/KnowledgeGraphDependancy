from typing import Dict, Any
from app.graph.engine import KnowledgeGraph
from app.models.parser_schemas import ParsedSyllabus


class GraphBuilder:
    """
    Syllabus-to-Graph Connector Service.
    Transforms structured ParsedSyllabus data directly into KnowledgeGraph concept nodes and edges.
    """

    @classmethod
    def build_from_syllabus(
        cls,
        syllabus: ParsedSyllabus,
        graph: KnowledgeGraph,
        clear_existing: bool = True,
        add_unit_sequential_edges: bool = False
    ) -> Dict[str, Any]:
        """
        Populates a KnowledgeGraph instance from a ParsedSyllabus object.

        Args:
            syllabus: Structured parsed syllabus containing units and topics.
            graph: KnowledgeGraph instance to populate.
            clear_existing: If True, clears existing graph contents first.
            add_unit_sequential_edges: If True, adds baseline prerequisite links between consecutive topics in each unit.

        Returns:
            Dict containing build statistics.
        """
        if clear_existing:
            graph.clear()

        nodes_added = 0
        edges_added = 0

        for unit in syllabus.units:
            unit_label = f"Unit {unit.unit_number}: {unit.title}" if unit.title else f"Unit {unit.unit_number}"
            previous_topic_id = None

            for topic in unit.topics:
                # Add concept node if not already present
                if not graph.has_concept(topic.id):
                    graph.add_concept(
                        id=topic.id,
                        name=topic.name,
                        unit=unit_label,
                        description=f"Concept extracted from {syllabus.course_title}",
                        metadata={
                            "unit_number": topic.unit_number,
                            "unit_title": topic.unit_title,
                            "course_code": syllabus.course_code,
                            "course_title": syllabus.course_title
                        }
                    )
                    nodes_added += 1

                # Optionally connect sequential topics within the same unit
                if add_unit_sequential_edges and previous_topic_id and previous_topic_id != topic.id:
                    if not graph.has_dependency(previous_topic_id, topic.id):
                        graph.add_dependency(
                            source_id=previous_topic_id,
                            target_id=topic.id,
                            relationship_type="unit_sequence",
                            confidence=0.8,
                            reason=f"Sequential topic order within {unit_label}"
                        )
                        edges_added += 1

                previous_topic_id = topic.id

        return {
            "course_title": syllabus.course_title,
            "course_code": syllabus.course_code,
            "nodes_added": nodes_added,
            "edges_added": edges_added,
            "units_processed": len(syllabus.units)
        }
