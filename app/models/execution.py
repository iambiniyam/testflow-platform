"""
TestFlow Platform - Test Execution Model

SQLAlchemy models for test executions and results.
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
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgresql import Base


class ExecutionStatus(str, PyEnum):
    """Test execution status options."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ExecutionTrigger(str, PyEnum):
    """How the execution was triggered."""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    CI_CD = "ci_cd"
    API = "api"
    WEBHOOK = "webhook"


class TestResultStatus(str, PyEnum):
    """Individual test result status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    ERROR = "error"
    PENDING = "pending"


class TestExecution(Base):
    """
    Test Execution model representing a test run.
    
    Attributes:
        id: Primary key
        name: Execution name
        project_id: Foreign key to project
        test_suite_id: Foreign key to test suite (optional)
        status: Current execution status
        trigger: How the execution was triggered
        triggered_by: User who triggered the execution
        environment: Execution environment
        config: JSON configuration for the execution
        started_at: Execution start time
        completed_at: Execution completion time
        total_tests: Total number of tests
        passed_tests: Number of passed tests
        failed_tests: Number of failed tests
        skipped_tests: Number of skipped tests
        error_message: Error message if execution failed
    """
    
    __tablename__ = "test_executions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    execution_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    test_suite_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("test_suites.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus),
        default=ExecutionStatus.PENDING,
        nullable=False,
        index=True
    )
    trigger: Mapped[ExecutionTrigger] = mapped_column(
        Enum(ExecutionTrigger),
        default=ExecutionTrigger.MANUAL,
        nullable=False
    )
    triggered_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Execution configuration
    environment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    variables: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    
    # Timing
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Results summary
    total_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocked_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    
    # Celery task tracking
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
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
        back_populates="executions",
        lazy="selectin"
    )
    test_suite: Mapped[Optional["TestSuite"]] = relationship(
        "TestSuite",
        back_populates="executions",
        lazy="selectin"
    )
    triggered_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="executions",
        lazy="selectin"
    )
    results: Mapped[List["TestCaseResult"]] = relationship(
        "TestCaseResult",
        back_populates="execution",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<TestExecution(id={self.id}, name='{self.name}', status='{self.status}')>"
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        executed = self.passed_tests + self.failed_tests
        if executed == 0:
            return 0.0
        return round((self.passed_tests / executed) * 100, 2)
    
    @property
    def is_running(self) -> bool:
        """Check if execution is currently running."""
        return self.status in [ExecutionStatus.RUNNING, ExecutionStatus.QUEUED]
    
    @property
    def is_complete(self) -> bool:
        """Check if execution is complete."""
        return self.status in [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMEOUT
        ]


class TestCaseResult(Base):
    """
    Test Case Result model for individual test results within an execution.
    
    Attributes:
        id: Primary key
        execution_id: Foreign key to parent execution
        test_case_id: Foreign key to test case
        status: Result status
        duration_seconds: Execution duration
        error_message: Error message if failed
        stack_trace: Stack trace for errors
        actual_result: Actual test result
        screenshots: JSON array of screenshot URLs
        logs: JSON array of log entries
    """
    
    __tablename__ = "test_case_results"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    execution_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("test_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    test_case_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    status: Mapped[TestResultStatus] = mapped_column(
        Enum(TestResultStatus),
        default=TestResultStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Result details
    actual_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Artifacts
    screenshots: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    logs: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    attachments: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    
    # Step-level results
    step_results: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    
    # Metadata
    environment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Retry tracking
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    execution: Mapped["TestExecution"] = relationship(
        "TestExecution",
        back_populates="results",
        lazy="selectin"
    )
    test_case: Mapped["TestCase"] = relationship(
        "TestCase",
        back_populates="execution_results",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<TestCaseResult(id={self.id}, status='{self.status}')>"
    
    @property
    def is_passed(self) -> bool:
        """Check if test passed."""
        return self.status == TestResultStatus.PASSED
    
    @property
    def is_failed(self) -> bool:
        """Check if test failed."""
        return self.status in [TestResultStatus.FAILED, TestResultStatus.ERROR]


# Import at the end to avoid circular imports
from app.models.project import Project
from app.models.test_suite import TestSuite
from app.models.user import User
from app.models.test_case import TestCase
