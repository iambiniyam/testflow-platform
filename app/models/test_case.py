"""
TestFlow Platform - Test Case Model

SQLAlchemy model for individual test cases.
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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgresql import Base


class TestCaseStatus(str, PyEnum):
    """Test case status options."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REVIEW = "review"


class TestCasePriority(str, PyEnum):
    """Test case priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TestCaseType(str, PyEnum):
    """Test case types."""
    MANUAL = "manual"
    AUTOMATED = "automated"
    HYBRID = "hybrid"


class TestCase(Base):
    """
    Test Case model representing individual test cases.
    
    Attributes:
        id: Primary key
        title: Test case title
        description: Detailed description
        project_id: Foreign key to parent project
        status: Current status
        priority: Priority level
        test_type: Type of test (manual/automated)
        preconditions: Required preconditions
        steps: JSON array of test steps
        expected_result: Expected outcome
        tags: JSON array of tags
        estimated_duration_seconds: Estimated execution time
        automation_script: Path or content of automation script
        created_by: Foreign key to creator user
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = "test_cases"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status: Mapped[TestCaseStatus] = mapped_column(
        Enum(TestCaseStatus),
        default=TestCaseStatus.DRAFT,
        nullable=False
    )
    priority: Mapped[TestCasePriority] = mapped_column(
        Enum(TestCasePriority),
        default=TestCasePriority.MEDIUM,
        nullable=False
    )
    test_type: Mapped[TestCaseType] = mapped_column(
        Enum(TestCaseType),
        default=TestCaseType.MANUAL,
        nullable=False
    )
    
    # Test case content
    preconditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    expected_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_data: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    
    # Metadata
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    labels: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    module: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Automation
    automation_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    automation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Tracking
    estimated_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
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
        back_populates="test_cases",
        lazy="selectin"
    )
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="test_cases",
        lazy="selectin"
    )
    test_suites: Mapped[List["TestSuite"]] = relationship(
        "TestSuite",
        secondary="suite_test_cases",
        back_populates="test_cases",
        lazy="selectin"
    )
    execution_results: Mapped[List["TestCaseResult"]] = relationship(
        "TestCaseResult",
        back_populates="test_case",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<TestCase(id={self.id}, title='{self.title}', status='{self.status}')>"
    
    @property
    def is_automated(self) -> bool:
        """Check if test case is automated."""
        return self.test_type in [TestCaseType.AUTOMATED, TestCaseType.HYBRID]
    
    @property
    def step_count(self) -> int:
        """Get number of test steps."""
        return len(self.steps) if self.steps else 0


# Import at the end to avoid circular imports
from app.models.project import Project
from app.models.user import User
from app.models.test_suite import TestSuite
from app.models.execution import TestCaseResult
