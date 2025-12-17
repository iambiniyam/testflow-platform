"""
TestFlow Platform - Main Application

FastAPI application entry point with middleware, exception handlers,
and lifecycle event handlers.
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.exceptions import TestFlowException
from app.db.postgresql import init_db, close_db
from app.db.mongodb import MongoDB, init_mongodb_indexes
from app.db.redis import RedisCache
from app.api.v1 import auth, projects, test_cases, executions
from app.schemas.common import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events for database connections
    and other resources.
    """
    # Startup
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    
    # Initialize databases
    try:
        await MongoDB.connect()
        await init_mongodb_indexes()
        await RedisCache.connect()
        print("✅ Database connections established")
    except Exception as e:
        print(f"❌ Failed to connect to databases: {e}")
        raise
    
    yield
    
    # Shutdown
    print("👋 Shutting down application...")
    await MongoDB.disconnect()
    await RedisCache.disconnect()
    await close_db()
    print("✅ Cleanup completed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    **TestFlow Platform** - A comprehensive test case management 
    and execution platform built with FastAPI.
    
    ## Features
    
    * 🔐 **Authentication** - JWT-based auth with role-based access control
    * 📁 **Projects** - Organize tests into projects
    * 📝 **Test Cases** - Create and manage test cases
    * 📦 **Test Suites** - Group test cases into suites
    * ⚡ **Async Execution** - Run tests asynchronously with Celery
    * 📊 **Reporting** - Generate comprehensive test reports
    * 🔌 **API Integration** - RESTful API for CI/CD integration
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    debug=settings.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Exception handlers
@app.exception_handler(TestFlowException)
async def testflow_exception_handler(
    request: Request,
    exc: TestFlowException
) -> JSONResponse:
    """Handle custom TestFlow exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            path=str(request.url),
        ).model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": exc.errors()},
            path=str(request.url),
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions."""
    print(f"Unexpected error: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            details={"error": str(exc)} if settings.debug else {},
            path=str(request.url),
        ).model_dump()
    )


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    import time
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Process-Time"] = str(process_time)
    
    if settings.debug:
        print(
            f"{request.method} {request.url.path} "
            f"- {response.status_code} "
            f"({process_time:.3f}s)"
        )
    
    return response


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    """
    Root endpoint with API information.
    
    Returns basic information about the API.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc",
    }


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint.
    
    Checks the status of all connected services.
    """
    from datetime import datetime
    
    services = {
        "api": "healthy",
        "postgresql": "unknown",
        "mongodb": "unknown",
        "redis": "unknown",
    }
    
    # Check PostgreSQL
    try:
        from app.db.postgresql import engine
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        services["postgresql"] = "healthy"
    except Exception:
        services["postgresql"] = "unhealthy"
    
    # Check MongoDB
    try:
        db = MongoDB.get_database()
        await db.command("ping")
        services["mongodb"] = "healthy"
    except Exception:
        services["mongodb"] = "unhealthy"
    
    # Check Redis
    try:
        await RedisCache.get_client().ping()
        services["redis"] = "healthy"
    except Exception:
        services["redis"] = "unhealthy"
    
    overall_status = "healthy" if all(
        s == "healthy" for s in services.values()
    ) else "degraded"
    
    return {
        "status": overall_status,
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
        "services": services,
    }


# Include API routers
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    projects.router,
    prefix="/api/v1/projects",
    tags=["Projects"]
)

app.include_router(
    test_cases.router,
    prefix="/api/v1/test-cases",
    tags=["Test Cases"]
)

app.include_router(
    executions.router,
    prefix="/api/v1/executions",
    tags=["Executions"]
)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers if not settings.debug else 1,
    )
