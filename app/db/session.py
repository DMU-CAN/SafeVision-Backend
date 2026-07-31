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


_PENDING_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "safety_events": [("clip_path", "VARCHAR(255)")],
    "cameras": [("location_x", "FLOAT"), ("location_y", "FLOAT")],
    # SQLite requires a DEFAULT when adding a NOT NULL column to a table that
    # already has rows.
    "zones": [("zone_type", "VARCHAR(30) NOT NULL DEFAULT 'DANGER'")],
}


def run_lightweight_migrations() -> None:
    """`Base.metadata.create_all` only creates missing tables, it never alters
    existing ones. This project has no Alembic setup, so new nullable columns
    on already-deployed tables are added here with a plain ALTER TABLE,
    guarded by an existence check so it's a no-op once applied."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    for table_name, pending_columns in _PENDING_COLUMNS.items():
        if table_name not in existing_tables:
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column_name, column_type in pending_columns:
            if column_name in existing_columns:
                continue
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
