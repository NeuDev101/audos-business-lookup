"""
Database engine and session management.

Reads DATABASE_URL from environment and provides SQLAlchemy session factory.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Default to SQLite for development/testing if DATABASE_URL not set
# Production should set DATABASE_URL to postgres://user:pass@host:port/dbname
_DEFAULT_DATABASE_URL = "sqlite:///./audos_invoices.db"

_engine = None
_session_factory = None


def get_database_url() -> str:
    """
    Get DATABASE_URL from environment or return default.
    
    Raises:
        ValueError: If DATABASE_URL is explicitly set but empty.
    """
    url = os.environ.get("DATABASE_URL", _DEFAULT_DATABASE_URL)
    if url == "":
        raise ValueError(
            "DATABASE_URL is set but empty. "
            "Either unset it to use default SQLite, or provide a valid database URL."
        )
    return url


def get_engine():
    """Get or create SQLAlchemy engine."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        _engine = create_engine(database_url, echo=False)
    return _engine


def get_session():
    """
    Get a SQLAlchemy session.
    
    Returns:
        Session: SQLAlchemy session object.
        
    Raises:
        ValueError: If DATABASE_URL is not configured properly.
    """
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = scoped_session(sessionmaker(bind=engine))
    return _session_factory()


def init_db():
    """
    Initialize database tables.
    
    Creates all tables defined in models. Should be called once at application startup
    or via migration script.
    """
    engine = get_engine()
    Base.metadata.create_all(engine)


def reset_db():
    """
    Drop and recreate all tables. USE WITH CAUTION - deletes all data!
    
    Only for testing/development.
    """
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

