from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_lightweight_migrations() -> None:
    """`Base.metadata.create_all` only creates missing tables, it never alters
    existing ones. This project has no Alembic setup, so new nullable columns
    on already-deployed tables (like safety_events.clip_path) are added here
    with a plain ALTER TABLE, guarded by an existence check so it's a no-op
    once applied."""
    inspector = inspect(engine)
    if "safety_events" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("safety_events")}
    if "clip_path" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE safety_events ADD COLUMN clip_path VARCHAR(255)"))
