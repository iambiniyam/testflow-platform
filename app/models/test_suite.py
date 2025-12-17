"""
TestFlow Platform - Test Suite Model

SQLAlchemy model for test suites that group test cases.
"""

from datetime import datetime
from typing import List, Optional
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Table,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgresql import Base


class SuiteType(str, PyEnum):
    """Test suite types."""
    REGRESSION = "regression"
    SMOKE = "smoke"
    INTEGRATION = "integration"
    ACCEPTANCE = "acceptance"
    PERFORMANCE = "performance"
    CUSTOM = "custom"


# Association table for test suite to test case many-to-many relationship
suite_test_cases = Table(
    "suite_test_cases",
    Base.metadata,
    Column("suite_id", Integer, ForeignKey("test_suites.id", ondelete="CASCADE"), primary_key=True),
    Column("test_case_id", Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), primary_key=True),
    Column("order", Integer, default=0),
    Column("created_at", DateTime, default=datetime.utcnow),
)


class TestSuite(Base):
    """
    Test Suite model for grouping related test cases.
    
    Attributes:
        id: Primary key
        name: Suite name
        description: Suite description
        project_id: Foreign key to parent project
        suite_type: Type of test suite
        is_active: Whether suite is active
        settings: JSON field for suite-specific settings
        tags: JSON array of tags
        parent_suite_id: Foreign key for hierarchical suites
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = "test_suites"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    suite_type: Mapped[SuiteType] = mapped_column(
        Enum(SuiteType),
        default=SuiteType.CUSTOM,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    parent_suite_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("test_suites.id", ondelete="SET NULL"),
        nullable=True
    )
    execution_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="test_suites",
        lazy="selectin"
    )
    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase",
        secondary=suite_test_cases,
        back_populates="test_suites",
        lazy="selectin"
    )
    parent_suite: Mapped[Optional["TestSuite"]] = relationship(
        "TestSuite",
        remote_side="TestSuite.id",
        backref="child_suites",
        lazy="selectin"
    )
    executions: Mapped[List["TestExecution"]] = relationship(
        "TestExecution",
        back_populates="test_suite",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<TestSuite(id={self.id}, name='{self.name}', type='{self.suite_type}')>"
    
    @property
    def test_case_count(self) -> int:
        """Get the number of test cases in this suite."""
        return len(self.test_cases) if self.test_cases else 0


# Import at the end to avoid circular imports
from app.models.project import Project
from app.models.test_case import TestCase
from app.models.execution import TestExecution
