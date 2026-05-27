import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

PROJECTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)

_active_db_path: str | None = None
_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    pass


def _build_engine(db_path: str):
    return create_engine(f"sqlite:///{db_path}", echo=False, connect_args={"check_same_thread": False})


def init_db():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = _build_engine(":memory:")
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(bind=_engine)


def switch_database(db_path: str):
    global _engine, _SessionLocal, _active_db_path
    _engine = _build_engine(db_path)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(bind=_engine)
    _active_db_path = db_path


def get_active_db_path() -> str | None:
    return _active_db_path


def get_db():
    if _SessionLocal is None:
        init_db()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
