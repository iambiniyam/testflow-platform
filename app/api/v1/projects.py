"""
TestFlow Platform - Projects API Routes

FastAPI routes for project management operations.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql import get_db
from app.models.user import User
from app.models.project import ProjectStatus
from app.api.deps import get_current_active_user, get_pagination_params
from app.services.project_service import ProjectService
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetail,
    ProjectList,
    ProjectStats,
)
from app.schemas.common import PaginationParams, SuccessResponse

router = APIRouter()


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project"
)
async def create_project(
    project_data: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ProjectResponse:
    """
    Create a new project.
    
    The authenticated user will be set as the project owner.
    """
    service = ProjectService(db)
    project = await service.create_project(project_data, current_user)
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.get(
    "",
    response_model=ProjectList,
    summary="List projects"
)
async def list_projects(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    status_filter: Optional[ProjectStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None, max_length=255)
) -> ProjectList:
    """
    List projects with pagination and filtering.
    
    Non-admin users only see projects they own or are members of.
    """
    service = ProjectService(db)
    projects, total = await service.list_projects(
        user=current_user,
        page=pagination.page,
        size=pagination.size,
        status=status_filter,
        search=search
    )
    
    return ProjectList(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size
    )


@router.get(
    "/{project_id}",
    response_model=ProjectDetail,
    summary="Get project by ID"
)
async def get_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ProjectDetail:
    """Get detailed information about a specific project."""
    service = ProjectService(db)
    project = await service.get_project(project_id)
    stats = await service.get_project_stats(project_id)
    
    return ProjectDetail(
        **ProjectResponse.model_validate(project).model_dump(),
        test_case_count=stats.total_test_cases,
        test_suite_count=stats.total_test_suites,
        pass_rate=stats.pass_rate,
        last_execution_at=stats.last_execution_at
    )


@router.get(
    "/slug/{slug}",
    response_model=ProjectResponse,
    summary="Get project by slug"
)
async def get_project_by_slug(
    slug: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ProjectResponse:
    """Get project information by slug."""
    service = ProjectService(db)
    project = await service.get_project_by_slug(slug)
    return ProjectResponse.model_validate(project)


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project"
)
async def update_project(
    project_id: int,
    update_data: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ProjectResponse:
    """Update project information."""
    service = ProjectService(db)
    project = await service.update_project(project_id, update_data, current_user)
    await db.commit()
    return ProjectResponse.model_validate(project)


@router.delete(
    "/{project_id}",
    response_model=SuccessResponse,
    summary="Delete project"
)
async def delete_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> SuccessResponse:
    """
    Delete (archive) a project.
    
    Only the project owner or admin can delete a project.
    """
    service = ProjectService(db)
    await service.delete_project(project_id, current_user)
    await db.commit()
    return SuccessResponse(
        success=True,
        message="Project archived successfully"
    )


@router.get(
    "/{project_id}/stats",
    response_model=ProjectStats,
    summary="Get project statistics"
)
async def get_project_stats(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ProjectStats:
    """Get detailed statistics for a project."""
    service = ProjectService(db)
    return await service.get_project_stats(project_id)
