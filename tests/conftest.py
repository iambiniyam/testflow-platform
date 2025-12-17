"""
Pytest Configuration and Fixtures

Provides common test fixtures and configuration for the test suite.
"""

import asyncio
import pytest
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.db.postgresql import Base
from app.core.config import settings
from app.models.user import User, UserRole, UserStatus
from app.core.security import get_password_hash


# Test database URL
TEST_DATABASE_URL = settings.database_url.replace("testflow", "testflow_test")


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a clean database session for each test."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("TestPassword123"),
        role=UserRole.TESTER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password=get_password_hash("AdminPassword123"),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def test_project_data():
    """Sample project data for testing."""
    return {
        "name": "Test Project",
        "slug": "test-project",
        "description": "A test project for unit testing",
        "tags": ["test", "automation"],
        "settings": {"notifications": True}
    }


@pytest.fixture
def test_case_data():
    """Sample test case data for testing."""
    return {
        "title": "Test Login Functionality",
        "description": "Verify user can log in with valid credentials",
        "preconditions": "User account must exist",
        "steps": [
            {
                "step_number": 1,
                "action": "Navigate to login page",
                "expected_result": "Login page is displayed"
            },
            {
                "step_number": 2,
                "action": "Enter valid credentials",
                "expected_result": "Credentials are accepted"
            },
            {
                "step_number": 3,
                "action": "Click login button",
                "expected_result": "User is logged in successfully"
            }
        ],
        "expected_result": "User is redirected to dashboard",
        "tags": ["login", "authentication"],
        "priority": "high",
        "test_type": "manual"
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
