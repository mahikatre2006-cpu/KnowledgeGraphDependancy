import pytest
from app.db.session import SessionLocal, Base, engine
from app.db.postgres_models import UserProgress, SyllabusDocument
from app.services.persistence_service import PersistenceService
from app.models.parser_schemas import ParsedSyllabus, ParsedUnit, ParsedTopic
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup


def test_persistence_status_api():
    response = client.get("/api/v1/persistence/status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "postgres_status" in data
    assert "neo4j_status" in data


def test_save_user_progress_service_and_api():
    # 1. API Call
    response = client.post("/api/v1/persistence/user-progress", json={
        "user_id": "test_user_999",
        "known_concept_ids": ["python", "vectors", "calculus"]
    })
    assert response.status_code == 200
    assert response.json()["saved_count"] == 3

    # 2. Database direct verification
    db = SessionLocal()
    records = db.query(UserProgress).filter(UserProgress.user_id == "test_user_999").all()
    assert len(records) == 3
    concept_ids = [r.concept_id for r in records]
    assert "python" in concept_ids
    assert "vectors" in concept_ids
    db.close()


def test_save_syllabus_to_postgres_service():
    db = SessionLocal()
    syllabus = ParsedSyllabus(
        course_title="Computer Vision",
        course_code="CV101",
        units=[
            ParsedUnit(
                unit_number=1,
                title="Image Processing",
                topics=[ParsedTopic(id="filtering", name="Image Filtering", unit_number=1, unit_title="Image Processing")]
            )
        ],
        all_topics=[ParsedTopic(id="filtering", name="Image Filtering", unit_number=1, unit_title="Image Processing")],
        total_topics_count=1
    )

    doc = PersistenceService.save_syllabus_to_postgres(db, syllabus)
    assert doc.id.startswith("syl_")
    assert doc.course_code == "CV101"
    assert len(doc.units_json) == 1
    db.close()
