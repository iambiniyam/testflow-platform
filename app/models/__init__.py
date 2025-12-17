"""Models module initialization."""

from app.models.user import User, UserRole, UserStatus
from app.models.project import Project, ProjectStatus
from app.models.test_suite import TestSuite, SuiteType
from app.models.test_case import (
    TestCase,
    TestCaseStatus,
    TestCasePriority,
    TestCaseType,
)
from app.models.execution import (
    TestExecution,
    TestCaseResult,
    ExecutionStatus,
    ExecutionTrigger,
    TestResultStatus,
)

__all__ = [
    # User
    "User",
    "UserRole",
    "UserStatus",
    # Project
    "Project",
    "ProjectStatus",
    # Test Suite
    "TestSuite",
    "SuiteType",
    # Test Case
    "TestCase",
    "TestCaseStatus",
    "TestCasePriority",
    "TestCaseType",
    # Execution
    "TestExecution",
    "TestCaseResult",
    "ExecutionStatus",
    "ExecutionTrigger",
    "TestResultStatus",
]
