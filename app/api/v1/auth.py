"""
TestFlow Platform - Authentication API Routes

FastAPI routes for user authentication and registration.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError
from app.db.postgresql import get_db
from app.services.auth_service import AuthService
from app.schemas.user import (
    UserCreate,
    UserResponse,
    LoginRequest,
    TokenResponse,
    TokenRefreshRequest,
)

router = APIRouter()
security = HTTPBearer()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email, username, and password."
)
async def register(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserResponse:
    """
    Register a new user account.
    
    Args:
        user_data: User registration information
        db: Database session
        
    Returns:
        UserResponse: Created user information
        
    Raises:
        ConflictError: If email or username already exists
    """
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.register(user_data)
        await db.commit()
        return UserResponse.model_validate(user)
    
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate user and receive access/refresh tokens."
)
async def login(
    credentials: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    """
    Authenticate user and generate JWT tokens.
    
    Args:
        credentials: Login credentials (email and password)
        db: Database session
        
    Returns:
        TokenResponse: Access and refresh tokens
        
    Raises:
        AuthenticationError: If credentials are invalid
    """
    auth_service = AuthService(db)
    
    try:
        tokens = await auth_service.login(credentials)
        await db.commit()
        return tokens
    
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token."
)
async def refresh_token(
    request: TokenRefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    
    Args:
        request: Refresh token request
        db: Database session
        
    Returns:
        TokenResponse: New access and refresh tokens
        
    Raises:
        AuthenticationError: If refresh token is invalid
    """
    auth_service = AuthService(db)
    
    try:
        tokens = await auth_service.refresh_tokens(request.refresh_token)
        return tokens
    
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Retrieve information about the authenticated user."
)
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserResponse:
    """
    Get current authenticated user information.
    
    Args:
        credentials: HTTP Bearer token
        db: Database session
        
    Returns:
        UserResponse: Current user information
        
    Raises:
        AuthenticationError: If token is invalid
    """
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.get_current_user(credentials.credentials)
        return UserResponse.model_validate(user)
    
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )
