"""
TestFlow Platform - Custom Exception Classes

This module defines custom exceptions used throughout the application
for consistent error handling and API responses.
"""

from typing import Any, Dict, Optional


class TestFlowException(Exception):
    """Base exception for all TestFlow application errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(TestFlowException):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            details=details
        )


class AuthorizationError(TestFlowException):
    """Raised when user lacks permission for an action."""
    
    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details
        )


class NotFoundError(TestFlowException):
    """Raised when a requested resource is not found."""
    
    def __init__(
        self,
        resource: str = "Resource",
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with ID '{resource_id}' not found"
        
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404,
            details=details
        )


class ConflictError(TestFlowException):
    """Raised when there's a conflict with existing data."""
    
    def __init__(
        self,
        message: str = "Resource already exists",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=409,
            details=details
        )


class ValidationError(TestFlowException):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str = "Validation error",
        errors: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if details is None:
            details = {}
        if errors:
            details["errors"] = errors
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details
        )


class DatabaseError(TestFlowException):
    """Raised when a database operation fails."""
    
    def __init__(
        self,
        message: str = "Database error occurred",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details
        )


class ExternalServiceError(TestFlowException):
    """Raised when an external service call fails."""
    
    def __init__(
        self,
        service: str = "External service",
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message or f"{service} is unavailable",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=503,
            details=details
        )


class RateLimitError(TestFlowException):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if details is None:
            details = {}
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details
        )


class TestExecutionError(TestFlowException):
    """Raised when test execution fails."""
    
    def __init__(
        self,
        message: str = "Test execution failed",
        execution_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if details is None:
            details = {}
        if execution_id:
            details["execution_id"] = execution_id
        
        super().__init__(
            message=message,
            error_code="EXECUTION_ERROR",
            status_code=500,
            details=details
        )


class FileUploadError(TestFlowException):
    """Raised when file upload fails."""
    
    def __init__(
        self,
        message: str = "File upload failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="FILE_UPLOAD_ERROR",
            status_code=400,
            details=details
        )
