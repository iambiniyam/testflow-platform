"""
TestFlow Platform - PostgreSQL Database Connection

This module provides async PostgreSQL database connectivity using
SQLAlchemy 2.0's async engine and session management.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Create async engine with connection pooling
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL statements in debug mode
    pool_pre_ping=True,  # Check connection health before using
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    
    This is a FastAPI dependency that creates a new database session
    for each request and ensures it's properly closed after the request.
    
    Yields:
        AsyncSession: Database session for the request
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions outside of request context.
    
    Use this for background tasks, CLI commands, or any context
    where FastAPI dependency injection is not available.
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.
    
    This creates all tables defined in the SQLAlchemy models.
    Should only be used for development/testing. Use Alembic
    migrations for production.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.
    
    Should be called during application shutdown to properly
    close all database connections.
    """
    await engine.dispose()


# Engine for testing (uses NullPool to avoid connection sharing issues)
def create_test_engine():
    """Create a test database engine with NullPool."""
    return create_async_engine(
        settings.database_url.replace("testflow", "testflow_test"),
        echo=True,
        poolclass=NullPool,
    )
