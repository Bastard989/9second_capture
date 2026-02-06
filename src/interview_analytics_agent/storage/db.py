"""
Инициализация базы данных и сессий SQLAlchemy.

Назначение:
- Создание engine
- Контекстный менеджер для сессий
- Единая точка доступа к БД для всех сервисов
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from interview_analytics_agent.common.config import get_settings

# =============================================================================
# ENGINE / SESSION FACTORY
# =============================================================================
_settings = get_settings()

if _settings.postgres_dsn.startswith("sqlite"):
    if _settings.postgres_dsn != "sqlite:///:memory:":
        path = _settings.postgres_dsn.replace("sqlite:///", "", 1)
        db_path = Path(path)
        if not db_path.is_absolute():
            db_path = (Path.cwd() / db_path).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        _settings.postgres_dsn,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        _settings.postgres_dsn,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

if _settings.postgres_dsn.startswith("sqlite"):
    # для локального режима создаём таблицы автоматически
    from interview_analytics_agent.storage.models import Base

    Base.metadata.create_all(bind=engine)


# =============================================================================
# CONTEXT MANAGER
# =============================================================================
@contextmanager
def db_session() -> Session:
    """
    Контекстный менеджер для работы с БД.

    Использование:
        with db_session() as session:
            session.add(...)
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
