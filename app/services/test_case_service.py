"""
TestFlow Platform - Test Case Service

Business logic for test case management.
"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, AuthorizationError, ValidationError
from app.models.project import Project
from app.models.test_case import TestCase, TestCaseStatus, TestCasePriority, TestCaseType
from app.models.test_suite import TestSuite
from app.models.user import User, UserRole
from app.schemas.test_case import (
    TestCaseCreate,
    TestCaseUpdate,
    TestCaseFilter,
    TestCaseBulkUpdate,
)
from app.db.redis import RedisCache, CacheKeys


class TestCaseService:
    """
    Service class for test case management operations.
    
    Handles CRUD operations for test cases, bulk operations,
    and test case organization.
    """
    
    CACHE_TTL = 300  # 5 minutes
    
    def __init__(self, db: AsyncSession):
        """
        Initialize TestCaseService with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def create_test_case(
        self,
        test_case_data: TestCaseCreate,
        user: User
    ) -> TestCase:
        """
        Create a new test case.
        
        Args:
            test_case_data: Test case creation data
            user: User creating the test case
            
        Returns:
            TestCase: The created test case
            
        Raises:
            NotFoundError: If project not found
        """
        # Verify project exists
        project = await self._get_project(test_case_data.project_id)
        if not project:
            raise NotFoundError(
                resource="Project",
                resource_id=str(test_case_data.project_id)
            )
        
        # Convert steps to dict if needed
        steps_data = None
        if test_case_data.steps:
            steps_data = [step.model_dump() for step in test_case_data.steps]
        
        # Create test case
        test_case = TestCase(
            title=test_case_data.title,
            description=test_case_data.description,
            project_id=test_case_data.project_id,
            status=TestCaseStatus.DRAFT,
            priority=test_case_data.priority,
            test_type=test_case_data.test_type,
            preconditions=test_case_data.preconditions,
            steps=steps_data,
            expected_result=test_case_data.expected_result,
            test_data=test_case_data.test_data or {},
            tags=test_case_data.tags or [],
            category=test_case_data.category,
            module=test_case_data.module,
            automation_script=test_case_data.automation_script,
            automation_id=test_case_data.automation_id,
            estimated_duration_seconds=test_case_data.estimated_duration_seconds,
            created_by=user.id,
        )
        
        self.db.add(test_case)
        await self.db.flush()
        await self.db.refresh(test_case)
        
        return test_case
    
    async def get_test_case(self, test_case_id: int) -> TestCase:
        """
        Get test case by ID.
        
        Args:
            test_case_id: Test case ID
            
        Returns:
            TestCase: The requested test case
            
        Raises:
            NotFoundError: If test case not found
        """
        test_case = await self._get_test_case_by_id(test_case_id)
        if not test_case:
            raise NotFoundError(
                resource="TestCase",
                resource_id=str(test_case_id)
            )
        return test_case
    
    async def list_test_cases(
        self,
        filters: TestCaseFilter,
        page: int = 1,
        size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[TestCase], int]:
        """
        List test cases with filtering and pagination.
        
        Args:
            filters: Filter criteria
            page: Page number
            size: Items per page
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            Tuple of test cases list and total count
        """
        query = select(TestCase).options(
            selectinload(TestCase.project),
            selectinload(TestCase.created_by_user)
        )
        count_query = select(func.count(TestCase.id))
        
        # Build filter conditions
        conditions = self._build_filter_conditions(filters)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply sorting
        sort_column = getattr(TestCase, sort_by, TestCase.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Apply pagination
        query = query.offset((page - 1) * size).limit(size)
        
        result = await self.db.execute(query)
        test_cases = result.scalars().all()
        
        return list(test_cases), total
    
    async def update_test_case(
        self,
        test_case_id: int,
        update_data: TestCaseUpdate,
        user: User
    ) -> TestCase:
        """
        Update a test case.
        
        Args:
            test_case_id: Test case ID
            update_data: Update data
            user: Current user
            
        Returns:
            TestCase: Updated test case
            
        Raises:
            NotFoundError: If test case not found
        """
        test_case = await self.get_test_case(test_case_id)
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Handle steps conversion
        if "steps" in update_dict and update_dict["steps"]:
            update_dict["steps"] = [
                step.model_dump() if hasattr(step, 'model_dump') else step
                for step in update_dict["steps"]
            ]
        
        for field, value in update_dict.items():
            setattr(test_case, field, value)
        
        # Increment version
        test_case.version += 1
        test_case.updated_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(test_case)
        
        return test_case
    
    async def delete_test_case(self, test_case_id: int, user: User) -> bool:
        """
        Delete a test case.
        
        Args:
            test_case_id: Test case ID
            user: Current user
            
        Returns:
            bool: True if successful
        """
        test_case = await self.get_test_case(test_case_id)
        
        await self.db.delete(test_case)
        await self.db.flush()
        
        return True
    
    async def bulk_update(
        self,
        bulk_data: TestCaseBulkUpdate,
        user: User
    ) -> int:
        """
        Bulk update multiple test cases.
        
        Args:
            bulk_data: Bulk update data
            user: Current user
            
        Returns:
            int: Number of updated test cases
        """
        updated_count = 0
        
        for test_case_id in bulk_data.test_case_ids:
            try:
                test_case = await self._get_test_case_by_id(test_case_id)
                if not test_case:
                    continue
                
                # Update status if provided
                if bulk_data.status:
                    test_case.status = bulk_data.status
                
                # Update priority if provided
                if bulk_data.priority:
                    test_case.priority = bulk_data.priority
                
                # Add tags
                if bulk_data.tags_to_add:
                    current_tags = set(test_case.tags or [])
                    current_tags.update(bulk_data.tags_to_add)
                    test_case.tags = list(current_tags)
                
                # Remove tags
                if bulk_data.tags_to_remove:
                    current_tags = set(test_case.tags or [])
                    current_tags -= set(bulk_data.tags_to_remove)
                    test_case.tags = list(current_tags)
                
                test_case.updated_at = datetime.utcnow()
                updated_count += 1
                
            except Exception:
                continue
        
        await self.db.flush()
        return updated_count
    
    async def add_to_suite(
        self,
        test_case_id: int,
        suite_id: int
    ) -> bool:
        """
        Add test case to a test suite.
        
        Args:
            test_case_id: Test case ID
            suite_id: Test suite ID
            
        Returns:
            bool: True if successful
        """
        test_case = await self.get_test_case(test_case_id)
        
        suite = await self._get_test_suite(suite_id)
        if not suite:
            raise NotFoundError(resource="TestSuite", resource_id=str(suite_id))
        
        if suite not in test_case.test_suites:
            test_case.test_suites.append(suite)
            await self.db.flush()
        
        return True
    
    async def remove_from_suite(
        self,
        test_case_id: int,
        suite_id: int
    ) -> bool:
        """
        Remove test case from a test suite.
        
        Args:
            test_case_id: Test case ID
            suite_id: Test suite ID
            
        Returns:
            bool: True if successful
        """
        test_case = await self.get_test_case(test_case_id)
        
        suite = await self._get_test_suite(suite_id)
        if not suite:
            raise NotFoundError(resource="TestSuite", resource_id=str(suite_id))
        
        if suite in test_case.test_suites:
            test_case.test_suites.remove(suite)
            await self.db.flush()
        
        return True
    
    async def duplicate_test_case(
        self,
        test_case_id: int,
        user: User,
        new_title: Optional[str] = None
    ) -> TestCase:
        """
        Duplicate a test case.
        
        Args:
            test_case_id: Test case ID to duplicate
            user: Current user
            new_title: Optional new title
            
        Returns:
            TestCase: The duplicated test case
        """
        original = await self.get_test_case(test_case_id)
        
        new_test_case = TestCase(
            title=new_title or f"{original.title} (Copy)",
            description=original.description,
            project_id=original.project_id,
            status=TestCaseStatus.DRAFT,
            priority=original.priority,
            test_type=original.test_type,
            preconditions=original.preconditions,
            steps=original.steps.copy() if original.steps else [],
            expected_result=original.expected_result,
            test_data=original.test_data.copy() if original.test_data else {},
            tags=original.tags.copy() if original.tags else [],
            category=original.category,
            module=original.module,
            automation_script=original.automation_script,
            estimated_duration_seconds=original.estimated_duration_seconds,
            created_by=user.id,
        )
        
        self.db.add(new_test_case)
        await self.db.flush()
        await self.db.refresh(new_test_case)
        
        return new_test_case
    
    def _build_filter_conditions(self, filters: TestCaseFilter) -> list:
        """Build SQLAlchemy filter conditions from filter schema."""
        conditions = []
        
        if filters.project_id:
            conditions.append(TestCase.project_id == filters.project_id)
        
        if filters.status:
            conditions.append(TestCase.status.in_(filters.status))
        
        if filters.priority:
            conditions.append(TestCase.priority.in_(filters.priority))
        
        if filters.test_type:
            conditions.append(TestCase.test_type.in_(filters.test_type))
        
        if filters.category:
            conditions.append(TestCase.category == filters.category)
        
        if filters.module:
            conditions.append(TestCase.module == filters.module)
        
        if filters.created_by:
            conditions.append(TestCase.created_by == filters.created_by)
        
        if filters.search:
            search_term = f"%{filters.search}%"
            conditions.append(
                or_(
                    TestCase.title.ilike(search_term),
                    TestCase.description.ilike(search_term)
                )
            )
        
        if filters.tags:
            # JSON array contains any of the tags
            for tag in filters.tags:
                conditions.append(TestCase.tags.contains([tag]))
        
        return conditions
    
    async def _get_test_case_by_id(self, test_case_id: int) -> Optional[TestCase]:
        """Get test case by ID with relationships."""
        result = await self.db.execute(
            select(TestCase)
            .options(
                selectinload(TestCase.project),
                selectinload(TestCase.created_by_user),
                selectinload(TestCase.test_suites)
            )
            .where(TestCase.id == test_case_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_project(self, project_id: int) -> Optional[Project]:
        """Get project by ID."""
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_test_suite(self, suite_id: int) -> Optional[TestSuite]:
        """Get test suite by ID."""
        result = await self.db.execute(
            select(TestSuite).where(TestSuite.id == suite_id)
        )
        return result.scalar_one_or_none()
