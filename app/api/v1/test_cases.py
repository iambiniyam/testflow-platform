"""
TestFlow Platform - Test Cases API Routes

FastAPI routes for test case management operations.
"""

from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql import get_db
from app.models.user import User
from app.models.test_case import TestCaseStatus, TestCasePriority, TestCaseType
from app.api.deps import get_current_active_user, get_pagination_params, get_sort_params
from app.services.test_case_service import TestCaseService
from app.schemas.test_case import (
    TestCaseCreate,
    TestCaseUpdate,
    TestCaseResponse,
    TestCaseDetail,
    TestCaseList,
    TestCaseFilter,
    TestCaseBulkUpdate,
)
from app.schemas.common import PaginationParams, SortParams, SuccessResponse

router = APIRouter()


@router.post(
    "",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new test case"
)
async def create_test_case(
    test_case_data: TestCaseCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TestCaseResponse:
    """Create a new test case in a project."""
    service = TestCaseService(db)
    test_case = await service.create_test_case(test_case_data, current_user)
    await db.commit()
    return TestCaseResponse.model_validate(test_case)


@router.get(
    "",
    response_model=TestCaseList,
    summary="List test cases"
)
async def list_test_cases(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    project_id: Optional[int] = Query(None),
    status_filter: Optional[List[TestCaseStatus]] = Query(None, alias="status"),
    priority: Optional[List[TestCasePriority]] = Query(None),
    test_type: Optional[List[TestCaseType]] = Query(None),
    category: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    search: Optional[str] = Query(None, max_length=255),
    tags: Optional[List[str]] = Query(None)
) -> TestCaseList:
    """
    List test cases with advanced filtering and pagination.
    """
    filters = TestCaseFilter(
        project_id=project_id,
        status=status_filter,
        priority=priority,
        test_type=test_type,
        category=category,
        module=module,
        search=search,
        tags=tags
    )
    
    service = TestCaseService(db)
    test_cases, total = await service.list_test_cases(
        filters=filters,
        page=pagination.page,
        size=pagination.size,
        sort_by=sort.sort_by,
        sort_order=sort.sort_order
    )
    
    return TestCaseList(
        items=[TestCaseResponse.model_validate(tc) for tc in test_cases],
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get(
    "/{test_case_id}",
    response_model=TestCaseDetail,
    summary="Get test case by ID"
)
async def get_test_case(
    test_case_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TestCaseDetail:
    """Get detailed information about a specific test case."""
    service = TestCaseService(db)
    test_case = await service.get_test_case(test_case_id)
    
    return TestCaseDetail(
        **TestCaseResponse.model_validate(test_case).model_dump(),
        project=test_case.project,
        test_suite_ids=[suite.id for suite in test_case.test_suites]
    )


@router.put(
    "/{test_case_id}",
    response_model=TestCaseResponse,
    summary="Update test case"
)
async def update_test_case(
    test_case_id: int,
    update_data: TestCaseUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TestCaseResponse:
    """Update a test case."""
    service = TestCaseService(db)
    test_case = await service.update_test_case(test_case_id, update_data, current_user)
    await db.commit()
    return TestCaseResponse.model_validate(test_case)


@router.delete(
    "/{test_case_id}",
    response_model=SuccessResponse,
    summary="Delete test case"
)
async def delete_test_case(
    test_case_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> SuccessResponse:
    """Delete a test case."""
    service = TestCaseService(db)
    await service.delete_test_case(test_case_id, current_user)
    await db.commit()
    return SuccessResponse(
        success=True,
        message="Test case deleted successfully"
    )


@router.post(
    "/bulk-update",
    response_model=SuccessResponse,
    summary="Bulk update test cases"
)
async def bulk_update_test_cases(
    bulk_data: TestCaseBulkUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> SuccessResponse:
    """Update multiple test cases at once."""
    service = TestCaseService(db)
    count = await service.bulk_update(bulk_data, current_user)
    await db.commit()
    return SuccessResponse(
        success=True,
        message=f"Updated {count} test case(s)"
    )


@router.post(
    "/{test_case_id}/duplicate",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate test case"
)
async def duplicate_test_case(
    test_case_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    new_title: Optional[str] = Query(None)
) -> TestCaseResponse:
    """Create a copy of an existing test case."""
    service = TestCaseService(db)
    new_test_case = await service.duplicate_test_case(
        test_case_id,
        current_user,
        new_title
    )
    await db.commit()
    return TestCaseResponse.model_validate(new_test_case)


@router.post(
    "/{test_case_id}/suites/{suite_id}",
    response_model=SuccessResponse,
    summary="Add test case to suite"
)
async def add_to_suite(
    test_case_id: int,
    suite_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> SuccessResponse:
    """Add a test case to a test suite."""
    service = TestCaseService(db)
    await service.add_to_suite(test_case_id, suite_id)
    await db.commit()
    return SuccessResponse(
        success=True,
        message="Test case added to suite"
    )


@router.delete(
    "/{test_case_id}/suites/{suite_id}",
    response_model=SuccessResponse,
    summary="Remove test case from suite"
)
async def remove_from_suite(
    test_case_id: int,
    suite_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> SuccessResponse:
    """Remove a test case from a test suite."""
    service = TestCaseService(db)
    await service.remove_from_suite(test_case_id, suite_id)
    await db.commit()
    return SuccessResponse(
        success=True,
        message="Test case removed from suite"
    )
