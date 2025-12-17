"""
TestFlow Platform - Project Model

SQLAlchemy model for projects that contain test cases and test suites.
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
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgresql import Base


class ProjectStatus(str, PyEnum):
    """Project status options."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"


class Project(Base):
    """
    Project model representing a collection of test cases.
    
    Attributes:
        id: Primary key
        name: Project name
        slug: URL-friendly identifier
        description: Project description
        status: Current project status
        owner_id: Foreign key to project owner
        settings: JSON field for project settings
        tags: JSON array of tags
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = "projects"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), 
        default=ProjectStatus.ACTIVE, 
        nullable=False
    )
    owner_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True
    )
    settings: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    repository_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    default_environment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    # Relationships
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="created_projects",
        foreign_keys=[owner_id],
        lazy="selectin"
    )
    members: Mapped[List["User"]] = relationship(
        "User",
        secondary="user_projects",
        back_populates="projects",
        lazy="selectin"
    )
    test_suites: Mapped[List["TestSuite"]] = relationship(
        "TestSuite",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    executions: Mapped[List["TestExecution"]] = relationship(
        "TestExecution",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if project is active."""
        return self.status == ProjectStatus.ACTIVE


# Import at the end to avoid circular imports
from app.models.user import User
from app.models.test_suite import TestSuite
from app.models.test_case import TestCase
from app.models.execution import TestExecution
