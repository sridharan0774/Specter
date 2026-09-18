from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    """Dependency for providing SQLAlchemy DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables and handle schema migrations for SQLite."""
    import app.models  # Ensure all models are imported before creating tables
    Base.metadata.create_all(bind=engine)

    # Migrate idx_tx_chain_hash and ensure new columns exist in existing SQLite databases
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP INDEX IF EXISTS idx_tx_chain_hash"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tx_chain_hash ON transactions (chain, tx_hash)"))

            if engine.dialect.name == "sqlite":
                # Check vasp_records table columns
                record_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(vasp_records)")).fetchall()]
                if record_cols and "entity_role" not in record_cols:
                    conn.execute(text("ALTER TABLE vasp_records ADD COLUMN entity_role VARCHAR(64) DEFAULT 'VASP'"))

                # Check vasp_attributions table columns
                attr_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(vasp_attributions)")).fetchall()]
                if attr_cols:
                    new_cols = [
                        ("entity_role", "VARCHAR(64) DEFAULT 'VASP'"),
                        ("match_position", "VARCHAR(64) DEFAULT 'TERMINAL_ENDPOINT'"),
                        ("is_terminal_endpoint", "INTEGER DEFAULT 1"),
                        ("value_transferred", "FLOAT"),
                        ("value_retention_percent", "FLOAT"),
                        ("temporal_proximity_seconds", "FLOAT"),
                        ("path_convergence_count", "INTEGER DEFAULT 1"),
                    ]
                    for col_name, col_def in new_cols:
                        if col_name not in attr_cols:
                            conn.execute(text(f"ALTER TABLE vasp_attributions ADD COLUMN {col_name} {col_def}"))

            conn.commit()
    except Exception as e:
        pass

    # Synchronize and seed verified VASP intelligence records
    try:
        from app.vasp.repository import VASPRepository
        with SessionLocal() as session:
            repo = VASPRepository(session)
            repo.seed_known_public_vasps()
    except Exception as e:
        pass
