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
    """Initialize database tables and handle index migrations."""
    import app.models  # Ensure all models are imported before creating tables
    Base.metadata.create_all(bind=engine)

    # Migrate idx_tx_chain_hash if it was created with UNIQUE constraint in existing SQLite database
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP INDEX IF EXISTS idx_tx_chain_hash"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tx_chain_hash ON transactions (chain, tx_hash)"))
            conn.commit()
    except Exception as e:
        pass
