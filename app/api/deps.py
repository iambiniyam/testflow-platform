"""
TestFlow Platform - API Dependency Functions

Common dependencies for API routes including authentication,
authorization, and pagination.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql import get_db
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from app.schemas.common import PaginationParams, SortParams

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token
        db: Database session
        
    Returns:
        User: Authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.get_current_user(credentials.credentials)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Verify that the current user is active.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Active user
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )
    return current_user


def require_role(required_role: UserRole):
    """
    Dependency factory to require specific user role.
    
    Args:
        required_role: Minimum required role
        
    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        """Check if user has required role."""
        if not AuthService.check_permission(current_user, required_role=required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher"
            )
        return current_user
    
    return role_checker


# Commonly used role dependencies
RequireAdmin = Depends(require_role(UserRole.ADMIN))
RequireManager = Depends(require_role(UserRole.MANAGER))
RequireTester = Depends(require_role(UserRole.TESTER))


def get_pagination_params(
    page: int = 1,
    size: int = 20
) -> PaginationParams:
    """
    Get pagination parameters.
    
    Args:
        page: Page number (default: 1)
        size: Items per page (default: 20, max: 100)
        
    Returns:
        PaginationParams: Validated pagination parameters
    """
    if page < 1:
        page = 1
    if size < 1:
        size = 20
    if size > 100:
        size = 100
    
    return PaginationParams(page=page, size=size)


def get_sort_params(
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> SortParams:
    """
    Get sorting parameters.
    
    Args:
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        
    Returns:
        SortParams: Validated sort parameters
    """
    if sort_order not in ["asc", "desc"]:
        sort_order = "desc"
    
    return SortParams(sort_by=sort_by, sort_order=sort_order)
