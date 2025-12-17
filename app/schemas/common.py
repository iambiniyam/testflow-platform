"""
TestFlow Platform - Common Schemas

Common Pydantic schemas used across the application.
"""

from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


# Generic type for paginated responses
T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    total: int
    page: int
    size: int
    pages: int
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        size: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        pages = (total + size - 1) // size if size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages
        )


class SortParams(BaseModel):
    """Sorting parameters."""
    sort_by: str = "created_at"
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class SearchParams(BaseModel):
    """Search parameters."""
    query: Optional[str] = Field(None, min_length=1, max_length=255)
    fields: Optional[List[str]] = None


class DateRangeParams(BaseModel):
    """Date range filter parameters."""
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    timestamp: datetime
    services: dict = {}


class ErrorResponse(BaseModel):
    """Standard error response."""
    error_code: str
    message: str
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: Optional[str] = None
    request_id: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    message: str
    data: Optional[Any] = None


class BulkOperationResult(BaseModel):
    """Result of a bulk operation."""
    total: int
    successful: int
    failed: int
    errors: List[dict] = []


class FileUploadResponse(BaseModel):
    """Response for file upload."""
    filename: str
    filepath: str
    size: int
    content_type: str
    url: str


class WebhookPayload(BaseModel):
    """Webhook notification payload."""
    event_type: str
    timestamp: datetime
    data: dict
    source: str = "testflow"


class AuditLogEntry(BaseModel):
    """Audit log entry."""
    id: str
    user_id: Optional[int] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime
