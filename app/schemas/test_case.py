"""
TestFlow Platform - Test Case Schemas

Pydantic schemas for test case-related request/response validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.test_case import TestCaseStatus, TestCasePriority, TestCaseType
from app.schemas.project import ProjectBrief
from app.schemas.user import UserBrief


# Step schema
class TestStep(BaseModel):
    """Schema for a test step."""
    step_number: int
    action: str
    expected_result: Optional[str] = None
    test_data: Optional[str] = None


# Base schemas
class TestCaseBase(BaseModel):
    """Base test case schema with common fields."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[TestStep]] = []
    expected_result: Optional[str] = None
    test_data: Optional[Dict[str, Any]] = {}
    tags: Optional[List[str]] = []
    category: Optional[str] = None
    module: Optional[str] = None
    estimated_duration_seconds: Optional[int] = None


# Request schemas
class TestCaseCreate(TestCaseBase):
    """Schema for creating a new test case."""
    project_id: int
    priority: TestCasePriority = TestCasePriority.MEDIUM
    test_type: TestCaseType = TestCaseType.MANUAL
    automation_script: Optional[str] = None
    automation_id: Optional[str] = None


class TestCaseUpdate(BaseModel):
    """Schema for updating a test case."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[TestCaseStatus] = None
    priority: Optional[TestCasePriority] = None
    test_type: Optional[TestCaseType] = None
    preconditions: Optional[str] = None
    steps: Optional[List[TestStep]] = None
    expected_result: Optional[str] = None
    test_data: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    module: Optional[str] = None
    automation_script: Optional[str] = None
    automation_id: Optional[str] = None
    estimated_duration_seconds: Optional[int] = None


class TestCaseBulkUpdate(BaseModel):
    """Schema for bulk updating test cases."""
    test_case_ids: List[int]
    status: Optional[TestCaseStatus] = None
    priority: Optional[TestCasePriority] = None
    tags_to_add: Optional[List[str]] = None
    tags_to_remove: Optional[List[str]] = None


class TestCaseFilter(BaseModel):
    """Schema for filtering test cases."""
    project_id: Optional[int] = None
    status: Optional[List[TestCaseStatus]] = None
    priority: Optional[List[TestCasePriority]] = None
    test_type: Optional[List[TestCaseType]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    module: Optional[str] = None
    search: Optional[str] = None
    created_by: Optional[int] = None


# Response schemas
class TestCaseResponse(TestCaseBase):
    """Schema for test case response."""
    id: int
    project_id: int
    status: TestCaseStatus
    priority: TestCasePriority
    test_type: TestCaseType
    automation_script: Optional[str] = None
    automation_id: Optional[str] = None
    version: int
    created_by_user: Optional[UserBrief] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class TestCaseBrief(BaseModel):
    """Brief test case info for embedding in other responses."""
    id: int
    title: str
    status: TestCaseStatus
    priority: TestCasePriority
    test_type: TestCaseType
    
    model_config = {"from_attributes": True}


class TestCaseDetail(TestCaseResponse):
    """Detailed test case response with project info."""
    project: ProjectBrief
    test_suite_ids: List[int] = []
    last_result_status: Optional[str] = None
    last_executed_at: Optional[datetime] = None


class TestCaseList(BaseModel):
    """Paginated list of test cases."""
    items: List[TestCaseResponse]
    total: int
    page: int
    size: int
    pages: int


class TestCaseImport(BaseModel):
    """Schema for importing test cases."""
    project_id: int
    test_cases: List[TestCaseCreate]
    skip_duplicates: bool = True


class TestCaseExport(BaseModel):
    """Schema for exporting test cases."""
    test_case_ids: Optional[List[int]] = None
    project_id: Optional[int] = None
    format: str = "json"  # json, csv, excel
