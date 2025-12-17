"""
TestFlow Platform - Project Schemas

Pydantic schemas for project-related request/response validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.project import ProjectStatus
from app.schemas.user import UserBrief


# Base schemas
class ProjectBase(BaseModel):
    """Base project schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    repository_url: Optional[str] = None
    default_environment: Optional[str] = None
    tags: Optional[List[str]] = []
    settings: Optional[Dict[str, Any]] = {}


# Request schemas
class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    
    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug(cls, v: Optional[str], info) -> str:
        """Generate slug from name if not provided."""
        if v:
            return v.lower().replace(" ", "-")
        return None


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    repository_url: Optional[str] = None
    default_environment: Optional[str] = None
    tags: Optional[List[str]] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectMemberAdd(BaseModel):
    """Schema for adding a member to a project."""
    user_id: int
    role: str = "viewer"


class ProjectMemberUpdate(BaseModel):
    """Schema for updating a project member's role."""
    role: str


# Response schemas
class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: int
    slug: str
    status: ProjectStatus
    owner: Optional[UserBrief] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ProjectBrief(BaseModel):
    """Brief project info for embedding in other responses."""
    id: int
    name: str
    slug: str
    status: ProjectStatus
    
    model_config = {"from_attributes": True}


class ProjectDetail(ProjectResponse):
    """Detailed project response with statistics."""
    test_case_count: int = 0
    test_suite_count: int = 0
    member_count: int = 0
    last_execution_at: Optional[datetime] = None
    pass_rate: Optional[float] = None


class ProjectList(BaseModel):
    """Paginated list of projects."""
    items: List[ProjectResponse]
    total: int
    page: int
    size: int
    pages: int


class ProjectStats(BaseModel):
    """Project statistics."""
    total_test_cases: int
    active_test_cases: int
    total_test_suites: int
    total_executions: int
    pass_rate: float
    avg_execution_time: float
    last_execution_at: Optional[datetime] = None
