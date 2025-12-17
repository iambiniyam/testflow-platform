"""
Unit Tests for Authentication Service

Tests for user registration, login, and token management.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import AuthService
from app.schemas.user import UserCreate, LoginRequest
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import verify_password
from app.models.user import User


@pytest.mark.asyncio
@pytest.mark.unit
class TestAuthService:
    """Test suite for AuthService."""
    
    async def test_register_new_user(self, db_session: AsyncSession):
        """Test successful user registration."""
        auth_service = AuthService(db_session)
        
        user_data = UserCreate(
            email="newuser@example.com",
            username="newuser",
            full_name="New User",
            password="SecurePassword123"
        )
        
        user = await auth_service.register(user_data)
        
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.full_name == "New User"
        assert verify_password("SecurePassword123", user.hashed_password)
    
    async def test_register_duplicate_email(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test registration with existing email fails."""
        auth_service = AuthService(db_session)
        
        user_data = UserCreate(
            email=test_user.email,  # Duplicate email
            username="anotheruser",
            password="Password123"
        )
        
        with pytest.raises(ConflictError) as exc_info:
            await auth_service.register(user_data)
        
        assert "email already exists" in str(exc_info.value.message).lower()
    
    async def test_register_duplicate_username(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test registration with existing username fails."""
        auth_service = AuthService(db_session)
        
        user_data = UserCreate(
            email="unique@example.com",
            username=test_user.username,  # Duplicate username
            password="Password123"
        )
        
        with pytest.raises(ConflictError) as exc_info:
            await auth_service.register(user_data)
        
        assert "username already exists" in str(exc_info.value.message).lower()
    
    async def test_login_success(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test successful login."""
        auth_service = AuthService(db_session)
        
        credentials = LoginRequest(
            email=test_user.email,
            password="TestPassword123"
        )
        
        tokens = await auth_service.login(credentials)
        
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"
        assert tokens.expires_in > 0
    
    async def test_login_invalid_email(self, db_session: AsyncSession):
        """Test login with non-existent email fails."""
        auth_service = AuthService(db_session)
        
        credentials = LoginRequest(
            email="nonexistent@example.com",
            password="Password123"
        )
        
        with pytest.raises(AuthenticationError):
            await auth_service.login(credentials)
    
    async def test_login_invalid_password(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test login with incorrect password fails."""
        auth_service = AuthService(db_session)
        
        credentials = LoginRequest(
            email=test_user.email,
            password="WrongPassword"
        )
        
        with pytest.raises(AuthenticationError):
            await auth_service.login(credentials)
    
    async def test_get_current_user_valid_token(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test getting current user with valid token."""
        from app.core.security import create_access_token
        
        auth_service = AuthService(db_session)
        token = create_access_token(str(test_user.id))
        
        user = await auth_service.get_current_user(token)
        
        assert user.id == test_user.id
        assert user.email == test_user.email
    
    async def test_get_current_user_invalid_token(
        self,
        db_session: AsyncSession
    ):
        """Test getting current user with invalid token fails."""
        auth_service = AuthService(db_session)
        
        with pytest.raises(AuthenticationError):
            await auth_service.get_current_user("invalid-token")
    
    async def test_refresh_tokens(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test refreshing access token."""
        from app.core.security import create_refresh_token
        
        auth_service = AuthService(db_session)
        refresh_token = create_refresh_token(str(test_user.id))
        
        tokens = await auth_service.refresh_tokens(refresh_token)
        
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"


@pytest.mark.asyncio
@pytest.mark.unit
class TestPasswordValidation:
    """Test password validation rules."""
    
    def test_password_requires_uppercase(self):
        """Test password must contain uppercase letter."""
        with pytest.raises(ValueError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="lowercase123"
            )
        assert "uppercase" in str(exc_info.value).lower()
    
    def test_password_requires_lowercase(self):
        """Test password must contain lowercase letter."""
        with pytest.raises(ValueError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="UPPERCASE123"
            )
        assert "lowercase" in str(exc_info.value).lower()
    
    def test_password_requires_digit(self):
        """Test password must contain digit."""
        with pytest.raises(ValueError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="NoDigitsHere"
            )
        assert "digit" in str(exc_info.value).lower()
    
    def test_password_minimum_length(self):
        """Test password minimum length requirement."""
        with pytest.raises(ValueError):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="Short1"  # Too short
            )
