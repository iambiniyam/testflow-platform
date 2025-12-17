"""
TestFlow Platform - User Model

SQLAlchemy model for user accounts and authentication.
"""

from datetime import datetime
from typing import List, Optional
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Table,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgresql import Base


class UserRole(str, PyEnum):
    """User roles for access control."""
    ADMIN = "admin"
    MANAGER = "manager"
    TESTER = "tester"
    VIEWER = "viewer"


class UserStatus(str, PyEnum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


# Association table for user-project many-to-many relationship
user_projects = Table(
    "user_projects",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("role", Enum(UserRole), default=UserRole.VIEWER),
    Column("created_at", DateTime, default=datetime.utcnow),
)


class User(Base):
    """
    User model for authentication and authorization.
    
    Attributes:
        id: Primary key
        email: Unique email address
        username: Unique username
        hashed_password: Bcrypt hashed password
        full_name: User's full name
        role: Global role for access control
        status: Account status
        is_superuser: Whether user has superuser privileges
        avatar_url: URL to user's avatar image
        last_login: Timestamp of last login
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        secondary=user_projects,
        back_populates="members",
        lazy="selectin"
    )
    created_projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="owner",
        foreign_keys="Project.owner_id",
        lazy="selectin"
    )
    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase",
        back_populates="created_by_user",
        lazy="selectin"
    )
    executions: Mapped[List["TestExecution"]] = relationship(
        "TestExecution",
        back_populates="triggered_by_user",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN or self.is_superuser


# Import at the end to avoid circular imports
from app.models.project import Project
from app.models.test_case import TestCase
from app.models.execution import TestExecution
