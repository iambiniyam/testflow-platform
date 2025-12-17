"""
TestFlow Platform - Project Service

Business logic for project management.
"""

import re
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ConflictError, AuthorizationError
from app.models.project import Project, ProjectStatus
from app.models.user import User, UserRole
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.models.execution import TestExecution
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectStats,
)
from app.db.redis import RedisCache, CacheKeys


class ProjectService:
    """
    Service class for project management operations.
    
    Handles CRUD operations for projects, member management,
    and project-related statistics.
    """
    
    CACHE_TTL = 300  # 5 minutes
    
    def __init__(self, db: AsyncSession):
        """
        Initialize ProjectService with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def create_project(
        self,
        project_data: ProjectCreate,
        owner: User
    ) -> Project:
        """
        Create a new project.
        
        Args:
            project_data: Project creation data
            owner: User creating the project
            
        Returns:
            Project: The created project
            
        Raises:
            ConflictError: If project with same slug exists
        """
        # Generate slug if not provided
        slug = project_data.slug or self._generate_slug(project_data.name)
        
        # Check for existing slug
        existing = await self._get_project_by_slug(slug)
        if existing:
            raise ConflictError(
                message=f"Project with slug '{slug}' already exists",
                details={"field": "slug"}
            )
        
        # Create project
        project = Project(
            name=project_data.name,
            slug=slug,
            description=project_data.description,
            repository_url=project_data.repository_url,
            default_environment=project_data.default_environment,
            tags=project_data.tags or [],
            settings=project_data.settings or {},
            owner_id=owner.id,
            status=ProjectStatus.ACTIVE,
        )
        
        self.db.add(project)
        await self.db.flush()
        await self.db.refresh(project)
        
        # Add owner as member
        project.members.append(owner)
        await self.db.flush()
        
        # Invalidate cache
        await self._invalidate_project_cache(project.id)
        
        return project
    
    async def get_project(self, project_id: int) -> Project:
        """
        Get project by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project: The requested project
            
        Raises:
            NotFoundError: If project not found
        """
        project = await self._get_project_by_id(project_id)
        if not project:
            raise NotFoundError(resource="Project", resource_id=str(project_id))
        return project
    
    async def get_project_by_slug(self, slug: str) -> Project:
        """
        Get project by slug.
        
        Args:
            slug: Project slug
            
        Returns:
            Project: The requested project
            
        Raises:
            NotFoundError: If project not found
        """
        project = await self._get_project_by_slug(slug)
        if not project:
            raise NotFoundError(resource="Project", resource_id=slug)
        return project
    
    async def list_projects(
        self,
        user: User,
        page: int = 1,
        size: int = 20,
        status: Optional[ProjectStatus] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Project], int]:
        """
        List projects with pagination and filtering.
        
        Args:
            user: Current user (for access control)
            page: Page number
            size: Items per page
            status: Filter by status
            search: Search term
            
        Returns:
            Tuple of projects list and total count
        """
        query = select(Project).options(selectinload(Project.owner))
        count_query = select(func.count(Project.id))
        
        # Apply filters
        filters = []
        
        # Non-admin users only see their projects
        if not user.is_admin:
            filters.append(
                or_(
                    Project.owner_id == user.id,
                    Project.members.any(User.id == user.id)
                )
            )
        
        if status:
            filters.append(Project.status == status)
        
        if search:
            search_term = f"%{search}%"
            filters.append(
                or_(
                    Project.name.ilike(search_term),
                    Project.description.ilike(search_term)
                )
            )
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination and ordering
        query = query.order_by(Project.updated_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        
        result = await self.db.execute(query)
        projects = result.scalars().all()
        
        return list(projects), total
    
    async def update_project(
        self,
        project_id: int,
        project_data: ProjectUpdate,
        user: User
    ) -> Project:
        """
        Update a project.
        
        Args:
            project_id: Project ID to update
            project_data: Update data
            user: Current user
            
        Returns:
            Project: Updated project
            
        Raises:
            NotFoundError: If project not found
            AuthorizationError: If user lacks permission
        """
        project = await self.get_project(project_id)
        
        # Check permission
        if not self._can_modify_project(user, project):
            raise AuthorizationError(
                message="You don't have permission to modify this project"
            )
        
        # Update fields
        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        
        project.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(project)
        
        # Invalidate cache
        await self._invalidate_project_cache(project.id)
        
        return project
    
    async def delete_project(self, project_id: int, user: User) -> bool:
        """
        Delete a project (soft delete by archiving).
        
        Args:
            project_id: Project ID to delete
            user: Current user
            
        Returns:
            bool: True if successful
            
        Raises:
            NotFoundError: If project not found
            AuthorizationError: If user lacks permission
        """
        project = await self.get_project(project_id)
        
        # Only owner or admin can delete
        if project.owner_id != user.id and not user.is_admin:
            raise AuthorizationError(
                message="Only the project owner can delete this project"
            )
        
        # Soft delete by archiving
        project.status = ProjectStatus.ARCHIVED
        project.updated_at = datetime.utcnow()
        await self.db.flush()
        
        # Invalidate cache
        await self._invalidate_project_cache(project.id)
        
        return True
    
    async def get_project_stats(self, project_id: int) -> ProjectStats:
        """
        Get project statistics.
        
        Args:
            project_id: Project ID
            
        Returns:
            ProjectStats: Project statistics
        """
        await self.get_project(project_id)  # Verify project exists
        
        # Count test cases
        test_case_query = select(func.count(TestCase.id)).where(
            TestCase.project_id == project_id
        )
        total_test_cases = (await self.db.execute(test_case_query)).scalar() or 0
        
        # Count active test cases
        active_query = select(func.count(TestCase.id)).where(
            and_(
                TestCase.project_id == project_id,
                TestCase.status == "active"
            )
        )
        active_test_cases = (await self.db.execute(active_query)).scalar() or 0
        
        # Count test suites
        suite_query = select(func.count(TestSuite.id)).where(
            TestSuite.project_id == project_id
        )
        total_suites = (await self.db.execute(suite_query)).scalar() or 0
        
        # Count executions
        exec_query = select(func.count(TestExecution.id)).where(
            TestExecution.project_id == project_id
        )
        total_executions = (await self.db.execute(exec_query)).scalar() or 0
        
        # Calculate pass rate from recent executions
        recent_exec_query = select(TestExecution).where(
            TestExecution.project_id == project_id
        ).order_by(TestExecution.created_at.desc()).limit(10)
        
        result = await self.db.execute(recent_exec_query)
        recent_executions = result.scalars().all()
        
        if recent_executions:
            total_passed = sum(e.passed_tests for e in recent_executions)
            total_tests = sum(
                e.passed_tests + e.failed_tests 
                for e in recent_executions
            )
            pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
            avg_duration = sum(
                e.duration_seconds or 0 for e in recent_executions
            ) / len(recent_executions)
            last_execution = recent_executions[0].created_at
        else:
            pass_rate = 0.0
            avg_duration = 0.0
            last_execution = None
        
        return ProjectStats(
            total_test_cases=total_test_cases,
            active_test_cases=active_test_cases,
            total_test_suites=total_suites,
            total_executions=total_executions,
            pass_rate=round(pass_rate, 2),
            avg_execution_time=round(avg_duration, 2),
            last_execution_at=last_execution,
        )
    
    async def _get_project_by_id(self, project_id: int) -> Optional[Project]:
        """Get project by ID with relationships."""
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.owner))
            .where(Project.id == project_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_project_by_slug(self, slug: str) -> Optional[Project]:
        """Get project by slug."""
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.owner))
            .where(Project.slug == slug)
        )
        return result.scalar_one_or_none()
    
    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug from name."""
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug
    
    def _can_modify_project(self, user: User, project: Project) -> bool:
        """Check if user can modify project."""
        if user.is_admin:
            return True
        if project.owner_id == user.id:
            return True
        if user.role in [UserRole.MANAGER, UserRole.ADMIN]:
            return True
        return False
    
    async def _invalidate_project_cache(self, project_id: int) -> None:
        """Invalidate project cache."""
        try:
            await RedisCache.delete(CacheKeys.project(str(project_id)))
        except Exception:
            pass  # Cache invalidation failure is not critical
