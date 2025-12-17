"""
TestFlow Platform - Authentication Service

Business logic for user authentication and authorization.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
)
from app.core.config import settings
from app.models.user import User, UserStatus, UserRole
from app.schemas.user import (
    UserCreate,
    UserResponse,
    TokenResponse,
    LoginRequest,
)
from app.db.redis import RedisCache, CacheKeys


class AuthService:
    """
    Service class for authentication operations.
    
    Handles user registration, login, token management,
    and authentication-related business logic.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize AuthService with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def register(self, user_data: UserCreate) -> User:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
            
        Returns:
            User: The created user
            
        Raises:
            ConflictError: If email or username already exists
        """
        # Check if email already exists
        existing_email = await self._get_user_by_email(user_data.email)
        if existing_email:
            raise ConflictError(
                message="A user with this email already exists",
                details={"field": "email"}
            )
        
        # Check if username already exists
        existing_username = await self._get_user_by_username(user_data.username)
        if existing_username:
            raise ConflictError(
                message="A user with this username already exists",
                details={"field": "username"}
            )
        
        # Create new user
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            status=UserStatus.ACTIVE,  # Auto-activate for simplicity
            role=UserRole.TESTER,  # Default role
        )
        
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        
        return user
    
    async def login(self, credentials: LoginRequest) -> TokenResponse:
        """
        Authenticate user and generate tokens.
        
        Args:
            credentials: Login credentials (email and password)
            
        Returns:
            TokenResponse: Access and refresh tokens
            
        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Get user by email
        user = await self._get_user_by_email(credentials.email)
        if not user:
            raise AuthenticationError(
                message="Invalid email or password",
                details={"field": "email"}
            )
        
        # Verify password
        if not verify_password(credentials.password, user.hashed_password):
            raise AuthenticationError(
                message="Invalid email or password",
                details={"field": "password"}
            )
        
        # Check if user is active
        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError(
                message=f"Account is {user.status.value}",
                details={"status": user.status.value}
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        await self.db.flush()
        
        # Generate tokens with additional claims
        additional_claims = {
            "email": user.email,
            "role": user.role.value,
            "is_superuser": user.is_superuser,
        }
        
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims=additional_claims
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
    
    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            TokenResponse: New access and refresh tokens
            
        Raises:
            AuthenticationError: If refresh token is invalid
        """
        # Verify refresh token
        user_id = verify_token(refresh_token, token_type="refresh")
        if not user_id:
            raise AuthenticationError(
                message="Invalid or expired refresh token"
            )
        
        # Get user
        user = await self.get_user_by_id(int(user_id))
        if not user or user.status != UserStatus.ACTIVE:
            raise AuthenticationError(
                message="User not found or inactive"
            )
        
        # Generate new tokens
        additional_claims = {
            "email": user.email,
            "role": user.role.value,
            "is_superuser": user.is_superuser,
        }
        
        new_access_token = create_access_token(
            subject=str(user.id),
            additional_claims=additional_claims
        )
        new_refresh_token = create_refresh_token(subject=str(user.id))
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User or None if not found
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_current_user(self, token: str) -> User:
        """
        Get current user from access token.
        
        Args:
            token: JWT access token
            
        Returns:
            User: The authenticated user
            
        Raises:
            AuthenticationError: If token is invalid
        """
        user_id = verify_token(token, token_type="access")
        if not user_id:
            raise AuthenticationError(message="Invalid or expired token")
        
        user = await self.get_user_by_id(int(user_id))
        if not user:
            raise AuthenticationError(message="User not found")
        
        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError(
                message=f"Account is {user.status.value}"
            )
        
        return user
    
    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def _get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    def check_permission(
        user: User,
        required_role: UserRole = None,
        required_permission: str = None
    ) -> bool:
        """
        Check if user has required permission.
        
        Args:
            user: User to check
            required_role: Minimum required role
            required_permission: Specific permission required
            
        Returns:
            bool: True if user has permission
        """
        if user.is_superuser:
            return True
        
        if required_role:
            role_hierarchy = {
                UserRole.VIEWER: 0,
                UserRole.TESTER: 1,
                UserRole.MANAGER: 2,
                UserRole.ADMIN: 3,
            }
            
            user_level = role_hierarchy.get(user.role, 0)
            required_level = role_hierarchy.get(required_role, 0)
            
            return user_level >= required_level
        
        return True
