"""
TestFlow Platform - Execution Schemas

Pydantic schemas for test execution-related request/response validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.execution import (
    ExecutionStatus,
    ExecutionTrigger,
    TestResultStatus,
)
from app.schemas.project import ProjectBrief
from app.schemas.test_case import TestCaseBrief
from app.schemas.user import UserBrief


# Base schemas
class ExecutionBase(BaseModel):
    """Base execution schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255)
    environment: Optional[str] = None
    config: Optional[Dict[str, Any]] = {}
    variables: Optional[Dict[str, Any]] = {}
    tags: Optional[List[str]] = []


# Request schemas
class ExecutionCreate(ExecutionBase):
    """Schema for creating a new test execution."""
    project_id: int
    test_suite_id: Optional[int] = None
    test_case_ids: Optional[List[int]] = None
    trigger: ExecutionTrigger = ExecutionTrigger.MANUAL
    scheduled_at: Optional[datetime] = None
    max_retries: int = Field(default=3, ge=0, le=10)
    parallel_workers: int = Field(default=1, ge=1, le=10)


class ExecutionUpdate(BaseModel):
    """Schema for updating an execution."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[ExecutionStatus] = None
    environment: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None


class ExecutionCancel(BaseModel):
    """Schema for cancelling an execution."""
    reason: Optional[str] = None


class ExecutionRetry(BaseModel):
    """Schema for retrying failed tests in an execution."""
    failed_only: bool = True


class ExecutionFilter(BaseModel):
    """Schema for filtering executions."""
    project_id: Optional[int] = None
    test_suite_id: Optional[int] = None
    status: Optional[List[ExecutionStatus]] = None
    trigger: Optional[List[ExecutionTrigger]] = None
    triggered_by: Optional[int] = None
    environment: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


# Result schemas
class TestResultCreate(BaseModel):
    """Schema for creating/updating a test result."""
    test_case_id: int
    status: TestResultStatus
    actual_result: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    duration_seconds: Optional[float] = None
    screenshots: Optional[List[str]] = []
    logs: Optional[List[Dict[str, Any]]] = []
    step_results: Optional[List[Dict[str, Any]]] = []


class TestResultResponse(BaseModel):
    """Schema for test result response."""
    id: int
    execution_id: int
    test_case_id: int
    test_case: Optional[TestCaseBrief] = None
    status: TestResultStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    actual_result: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    screenshots: Optional[List[str]] = []
    logs: Optional[List[Dict[str, Any]]] = []
    step_results: Optional[List[Dict[str, Any]]] = []
    attempt_number: int
    environment: Optional[str] = None
    browser: Optional[str] = None
    platform: Optional[str] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


# Response schemas
class ExecutionResponse(ExecutionBase):
    """Schema for execution response."""
    id: int
    execution_key: str
    project_id: int
    test_suite_id: Optional[int] = None
    status: ExecutionStatus
    trigger: ExecutionTrigger
    triggered_by_user: Optional[UserBrief] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    blocked_tests: int
    error_tests: int
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    celery_task_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ExecutionBrief(BaseModel):
    """Brief execution info for embedding in other responses."""
    id: int
    execution_key: str
    name: str
    status: ExecutionStatus
    pass_rate: float
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ExecutionDetail(ExecutionResponse):
    """Detailed execution response with results."""
    project: ProjectBrief
    results: List[TestResultResponse] = []
    pass_rate: float = 0.0


class ExecutionList(BaseModel):
    """Paginated list of executions."""
    items: List[ExecutionResponse]
    total: int
    page: int
    size: int
    pages: int


class ExecutionProgress(BaseModel):
    """Real-time execution progress."""
    execution_id: int
    status: ExecutionStatus
    total_tests: int
    completed_tests: int
    passed_tests: int
    failed_tests: int
    current_test: Optional[str] = None
    progress_percent: float
    elapsed_seconds: float
    estimated_remaining_seconds: Optional[float] = None


class ExecutionSummary(BaseModel):
    """Execution summary for reporting."""
    execution_id: int
    execution_key: str
    name: str
    project_name: str
    status: ExecutionStatus
    trigger: ExecutionTrigger
    triggered_by: Optional[str] = None
    environment: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    pass_rate: float
    failed_test_names: List[str] = []
