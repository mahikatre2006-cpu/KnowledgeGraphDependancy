import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SyllabusDocument(Base):
    __tablename__ = "syllabi"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    course_code = Column(String, index=True, nullable=True)
    course_title = Column(String, nullable=False)
    units_json = Column(JSON, nullable=False)
    topics_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    concept_id = Column(String, nullable=False, index=True)
    status = Column(String, default="known", nullable=False)  # known, in_progress, blocked
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class ConceptEmbedding(Base):
    __tablename__ = "concept_embeddings"

    id = Column(String, primary_key=True, index=True)
    concept_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
