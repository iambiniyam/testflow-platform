"""
TestFlow Platform - Executions API Routes

FastAPI routes for test execution operations.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql import get_db
from app.db.redis import RedisCache, CacheKeys
from app.models.user import User
from app.api.deps import get_current_active_user, get_pagination_params
from app.schemas.execution import (
    ExecutionCreate,
    ExecutionResponse,
    ExecutionDetail,
    ExecutionList,
    ExecutionProgress,
)
from app.schemas.common import PaginationParams, SuccessResponse
from app.models.execution import TestExecution, ExecutionStatus
from app.tasks.execution_tasks import execute_test_suite, cancel_execution
from sqlalchemy import select
import uuid

router = APIRouter()


@router.post(
    "",
    response_model=ExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and start test execution"
)
async def create_execution(
    execution_data: ExecutionCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ExecutionResponse:
    """
    Create a new test execution and queue it for processing.
    
    The execution will run asynchronously via Celery workers.
    """
    # Create execution record
    execution = TestExecution(
        name=execution_data.name,
        execution_key=f"EXE-{uuid.uuid4().hex[:8].upper()}",
        project_id=execution_data.project_id,
        test_suite_id=execution_data.test_suite_id,
        status=ExecutionStatus.QUEUED,
        trigger=execution_data.trigger,
        triggered_by=current_user.id,
        environment=execution_data.environment,
        config=execution_data.config or {},
        variables=execution_data.variables or {},
        tags=execution_data.tags or [],
        scheduled_at=execution_data.scheduled_at,
        max_retries=execution_data.max_retries,
    )
    
    db.add(execution)
    await db.flush()
    await db.refresh(execution)
    
    # Queue the execution task
    task = execute_test_suite.delay(execution.id)
    
    execution.celery_task_id = task.id
    await db.commit()
    
    return ExecutionResponse.model_validate(execution)


@router.get(
    "",
    response_model=ExecutionList,
    summary="List test executions"
)
async def list_executions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    project_id: Optional[int] = Query(None),
    status_filter: Optional[ExecutionStatus] = Query(None, alias="status")
) -> ExecutionList:
    """List test executions with filtering and pagination."""
    from sqlalchemy import func, and_
    
    query = select(TestExecution)
    count_query = select(func.count(TestExecution.id))
    
    filters = []
    if project_id:
        filters.append(TestExecution.project_id == project_id)
    if status_filter:
        filters.append(TestExecution.status == status_filter)
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get executions
    query = query.order_by(TestExecution.created_at.desc())
    query = query.offset(pagination.offset).limit(pagination.size)
    
    result = await db.execute(query)
    executions = result.scalars().all()
    
    return ExecutionList(
        items=[ExecutionResponse.model_validate(e) for e in executions],
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get(
    "/{execution_id}",
    response_model=ExecutionDetail,
    summary="Get execution by ID"
)
async def get_execution(
    execution_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ExecutionDetail:
    """Get detailed information about a test execution."""
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(TestExecution)
        .options(
            selectinload(TestExecution.project),
            selectinload(TestExecution.results)
        )
        .where(TestExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()
    
    if not execution:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    return ExecutionDetail(
        **ExecutionResponse.model_validate(execution).model_dump(),
        project=execution.project,
        results=execution.results,
        pass_rate=execution.pass_rate
    )


@router.get(
    "/{execution_id}/progress",
    response_model=ExecutionProgress,
    summary="Get execution progress"
)
async def get_execution_progress(
    execution_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ExecutionProgress:
    """Get real-time progress of a running execution."""
    import time
    
    # Try to get from cache first
    cache_data = await RedisCache.get_json(
        CacheKeys.execution_status(str(execution_id))
    )
    
    # Fall back to database
    result = await db.execute(
        select(TestExecution).where(TestExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()
    
    if not execution:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    completed = (
        execution.passed_tests +
        execution.failed_tests +
        execution.skipped_tests
    )
    
    progress_percent = 0
    if execution.total_tests > 0:
        progress_percent = (completed / execution.total_tests) * 100
    
    elapsed = 0
    if execution.started_at:
        elapsed = (
            execution.completed_at or datetime.utcnow()
        ) - execution.started_at
        elapsed = elapsed.total_seconds()
    
    return ExecutionProgress(
        execution_id=execution.id,
        status=execution.status,
        total_tests=execution.total_tests,
        completed_tests=completed,
        passed_tests=execution.passed_tests,
        failed_tests=execution.failed_tests,
        progress_percent=progress_percent,
        elapsed_seconds=elapsed
    )


@router.post(
    "/{execution_id}/cancel",
    response_model=SuccessResponse,
    summary="Cancel execution"
)
async def cancel_test_execution(
    execution_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> SuccessResponse:
    """Cancel a running or queued execution."""
    # Queue cancellation task
    cancel_execution.delay(execution_id)
    
    return SuccessResponse(
        success=True,
        message="Execution cancellation requested"
    )


from datetime import datetime
