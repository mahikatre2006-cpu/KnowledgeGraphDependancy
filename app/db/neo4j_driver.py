import os
from typing import Optional, Dict, Any, List
from neo4j import GraphDatabase, Driver
from app.graph.engine import KnowledgeGraph
from app.graph.models import ConceptNode, DependencyEdge


class Neo4jService:
    """
    Neo4j Graph Database Service.
    Persists KnowledgeGraph concept nodes and prerequisite relationships using Cypher queries.
    """
    _driver: Optional[Driver] = None

    @classmethod
    def get_driver(cls) -> Optional[Driver]:
        """Returns active Neo4j driver or None if credentials unconfigured."""
        uri = os.getenv("NEO4J_URI", "")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")

        if not uri or not password:
            return None

        if cls._driver is None:
            try:
                cls._driver = GraphDatabase.driver(uri, auth=(user, password))
            except Exception:
                return None
        return cls._driver

    @classmethod
    def sync_graph_to_neo4j(cls, graph: KnowledgeGraph) -> Dict[str, Any]:
        """
        Syncs active in-memory KnowledgeGraph into Neo4j using Cypher queries.
        """
        driver = cls.get_driver()
        if not driver:
            return {
                "success": False,
                "message": "Neo4j unconfigured (NEO4J_URI and NEO4J_PASSWORD environment variables required)."
            }

        nodes = graph.get_all_nodes()
        edges = graph.get_all_edges()

        with driver.session() as session:
            # 1. Merge Concept Nodes
            for node in nodes:
                session.run(
                    """
                    MERGE (c:Concept {id: $id})
                    SET c.name = $name,
                        c.unit = $unit,
                        c.description = $description
                    """,
                    id=node.id,
                    name=node.name,
                    unit=node.unit,
                    description=node.description
                )

            # 2. Merge Prerequisite Relationships
            for edge in edges:
                session.run(
                    """
                    MATCH (src:Concept {id: $source_id})
                    MATCH (tgt:Concept {id: $target_id})
                    MERGE (src)-[r:PREREQUISITE_FOR]->(tgt)
                    SET r.relationship_type = $relationship_type,
                        r.confidence = $confidence,
                        r.reason = $reason
                    """,
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    relationship_type=edge.relationship_type,
                    confidence=edge.confidence,
                    reason=edge.reason
                )

        return {
            "success": True,
            "message": f"Successfully synced {len(nodes)} nodes and {len(edges)} edges to Neo4j.",
            "nodes_synced": len(nodes),
            "edges_synced": len(edges)
        }

    @classmethod
    def load_graph_from_neo4j(cls) -> Optional[KnowledgeGraph]:
        """
        Queries Neo4j database and reconstructs a KnowledgeGraph instance.
        """
        driver = cls.get_driver()
        if not driver:
            return None

        kg = KnowledgeGraph()

        with driver.session() as session:
            # Fetch all Concept nodes
            node_result = session.run("MATCH (c:Concept) RETURN c.id AS id, c.name AS name, c.unit AS unit, c.description AS description")
            for record in node_result:
                kg.add_concept(
                    id=record["id"],
                    name=record["name"],
                    unit=record["unit"] or "",
                    description=record["description"] or ""
                )

            # Fetch all PREREQUISITE_FOR edges
            edge_result = session.run(
                """
                MATCH (src:Concept)-[r:PREREQUISITE_FOR]->(tgt:Concept)
                RETURN src.id AS source_id, tgt.id AS target_id, r.relationship_type AS rel_type, r.confidence AS confidence, r.reason AS reason
                """
            )
            for record in edge_result:
                if kg.has_concept(record["source_id"]) and kg.has_concept(record["target_id"]):
                    kg.add_dependency(
                        source_id=record["source_id"],
                        target_id=record["target_id"],
                        relationship_type=record["rel_type"] or "prerequisite",
                        confidence=record["confidence"] or 1.0,
                        reason=record["reason"] or ""
                    )

        return kg
