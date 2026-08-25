import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# PostgreSQL Connection URL (can be customized via .env)
DEFAULT_PG_URL = "postgresql://postgres:postgres@localhost:5432/smartmandi"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_PG_URL)


def create_db_engine():
    """Create database engine with automatic fallback to SQLite if PostgreSQL is unreachable."""
    if DATABASE_URL.startswith("sqlite"):
        print("[DB] Using SQLite database:", DATABASE_URL)
        return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    # Try PostgreSQL first with short timeout
    try:
        pg_engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 2}
        )
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[DB] Successfully connected to PostgreSQL database!")
        return pg_engine
    except Exception as e:
        sqlite_fallback = "sqlite:///./smartmandi.db"
        print(f"[DB Notice] Could not connect to PostgreSQL ({e.__class__.__name__}).")
        print(f"[DB Notice] Using local SQLite database ({sqlite_fallback}) so the app works seamlessly.")
        return create_engine(sqlite_fallback, connect_args={"check_same_thread": False})


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency to yield a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
