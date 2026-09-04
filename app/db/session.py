import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# PostgreSQL / Supabase Connection URI from environment variable
# Format: postgresql://postgres.xxxx:[PASSWORD]@aws-0-region.pooler.supabase.com:6543/postgres
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./kdg_local.db"  # Fallback to local SQLite database if DATABASE_URL is unconfigured
)

# Convert postgres:// to postgresql:// if needed for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency generator for API routes requiring a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
