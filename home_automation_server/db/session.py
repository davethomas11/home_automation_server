"""
Database engine, session factory, and helpers.
"""

from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

from home_automation_server.core.config import settings

# Ensure the data directory exists
Path("data").mkdir(exist_ok=True)

connect_args = {"check_same_thread": False}
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args=connect_args,
)


def init_db() -> None:
    """Create all tables (used at startup; migrations handle schema changes)."""
    # Import models so SQLModel metadata is populated
    import home_automation_server.models.models  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency: yields a database session."""
    with Session(engine) as session:
        yield session

