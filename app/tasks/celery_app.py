"""
TestFlow Platform - Celery Application

Configuration and initialization of Celery for asynchronous task processing.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Create Celery application
celery_app = Celery(
    "testflow",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=[
        "app.tasks.execution_tasks",
        "app.tasks.report_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Task routing
    task_routes={
        "app.tasks.execution_tasks.*": {"queue": "executions"},
        "app.tasks.report_tasks.*": {"queue": "reports"},
    },
    
    # Task time limits (in seconds)
    task_soft_time_limit=1800,  # 30 minutes
    task_time_limit=3600,  # 1 hour
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-old-results": {
            "task": "app.tasks.execution_tasks.cleanup_old_results",
            "schedule": crontab(hour=2, minute=0),  # Run at 2 AM daily
        },
        "generate-daily-reports": {
            "task": "app.tasks.report_tasks.generate_daily_reports",
            "schedule": crontab(hour=8, minute=0),  # Run at 8 AM daily
        },
    },
)

# Task error handling
celery_app.conf.task_annotations = {
    "*": {
        "rate_limit": "100/m",  # 100 tasks per minute
        "retry_backoff": True,
        "retry_backoff_max": 600,  # Max 10 minutes
        "retry_jitter": True,
    }
}


if __name__ == "__main__":
    celery_app.start()
