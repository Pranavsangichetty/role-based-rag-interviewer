from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings

# If sqlite URL, ensure the parent directory exists
if settings.database_url.startswith("sqlite"):
    # Strip sqlite:/// prefix and resolve parent
    db_file_path = settings.database_url.replace("sqlite:///", "")
    if db_file_path and db_file_path != ":memory:":
        Path(db_file_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

