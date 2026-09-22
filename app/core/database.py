import logging
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings


logger = logging.getLogger("specter.database")


def _get_database_url() -> str:
    """Normalize PostgreSQL URLs for SQLAlchemy + psycopg."""
    url = settings.DATABASE_URL.strip()

    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]

    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]

    return url


DATABASE_URL = _get_database_url()

connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db() -> Generator:
    """Dependency for providing SQLAlchemy DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables and apply SQLite compatibility migrations."""
    import app.models

    logger.info(
        "Initializing database using %s",
        engine.dialect.name,
    )

    # Create all declared tables and indexes.
    Base.metadata.create_all(bind=engine)

    # SQLite-only compatibility migrations.
    if engine.dialect.name == "sqlite":
        try:
            with engine.begin() as conn:
                record_cols = [
                    row[1]
                    for row in conn.execute(
                        text("PRAGMA table_info(vasp_records)")
                    ).fetchall()
                ]

                if record_cols and "entity_role" not in record_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE vasp_records "
                            "ADD COLUMN entity_role VARCHAR(64) DEFAULT 'VASP'"
                        )
                    )

                attr_cols = [
                    row[1]
                    for row in conn.execute(
                        text("PRAGMA table_info(vasp_attributions)")
                    ).fetchall()
                ]

                if attr_cols:
                    new_cols = [
                        ("entity_role", "VARCHAR(64) DEFAULT 'VASP'"),
                        (
                            "match_position",
                            "VARCHAR(64) DEFAULT 'TERMINAL_ENDPOINT'",
                        ),
                        ("is_terminal_endpoint", "INTEGER DEFAULT 1"),
                        ("value_transferred", "FLOAT"),
                        ("value_retention_percent", "FLOAT"),
                        ("temporal_proximity_seconds", "FLOAT"),
                        ("path_convergence_count", "INTEGER DEFAULT 1"),
                    ]

                    for col_name, col_def in new_cols:
                        if col_name not in attr_cols:
                            conn.execute(
                                text(
                                    f"ALTER TABLE vasp_attributions "
                                    f"ADD COLUMN {col_name} {col_def}"
                                )
                            )

        except Exception:
            logger.exception("SQLite compatibility migration failed.")
            raise

    # Synchronize and seed VASP intelligence records.
    try:
        from app.vasp.repository import VASPRepository

        with SessionLocal() as session:
            repo = VASPRepository(session)
            repo.seed_known_public_vasps()

    except Exception:
        logger.exception("VASP intelligence initialization failed.")
        raise

    logger.info("Database initialization completed successfully.")