import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.graph.engine import KnowledgeGraph
from app.db.postgres_models import SyllabusDocument, UserProgress
from app.db.neo4j_driver import Neo4jService
from app.models.parser_schemas import ParsedSyllabus


class PersistenceService:
    """
    Unified Persistence Layer.
    Coordinates syncing data across in-memory KnowledgeGraph, Supabase PostgreSQL, and Neo4j Graph DB.
    """

    @classmethod
    def save_syllabus_to_postgres(
        cls,
        db: Session,
        syllabus: ParsedSyllabus,
        user_id: Optional[str] = None
    ) -> SyllabusDocument:
        """Saves a parsed syllabus record to PostgreSQL (Supabase)."""
        doc_id = f"syl_{uuid.uuid4().hex[:12]}"
        doc = SyllabusDocument(
            id=doc_id,
            user_id=user_id,
            course_code=syllabus.course_code,
            course_title=syllabus.course_title,
            units_json=[unit.model_dump() for unit in syllabus.units],
            topics_json=[topic.model_dump() for topic in syllabus.all_topics]
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @classmethod
    def save_user_progress_to_postgres(
        cls,
        db: Session,
        user_id: str,
        known_concept_ids: List[str]
    ) -> int:
        """Saves a student's mastered concepts to PostgreSQL (Supabase)."""
        # Delete existing progress for user
        db.query(UserProgress).filter(UserProgress.user_id == user_id).delete()

        records = [
            UserProgress(
                id=f"prog_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                concept_id=cid.strip(),
                status="known"
            )
            for cid in known_concept_ids
        ]
        db.add_all(records)
        db.commit()
        return len(records)

    @classmethod
    def sync_to_neo4j(cls, graph: KnowledgeGraph) -> Dict[str, Any]:
        """Syncs active in-memory KnowledgeGraph into Neo4j."""
        return Neo4jService.sync_graph_to_neo4j(graph)
