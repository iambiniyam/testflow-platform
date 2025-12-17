"""
TestFlow Platform - Execution Tasks

Celery tasks for asynchronous test execution.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any

from celery import Task, group, chord
from sqlalchemy import select, and_

from app.tasks.celery_app import celery_app
from app.db.postgresql import get_db_context
from app.db.mongodb import MongoDB, Collections
from app.db.redis import RedisCache, CacheKeys
from app.models.execution import (
    TestExecution,
    TestCaseResult,
    ExecutionStatus,
    TestResultStatus,
)
from app.models.test_case import TestCase


class CallbackTask(Task):
    """Base task with callback functionality."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        print(f"Task {task_id} failed: {exc}")
        
        # Update execution status if execution_id is provided
        if args and len(args) > 0:
            execution_id = args[0]
            asyncio.run(self._mark_execution_failed(execution_id, str(exc)))
    
    async def _mark_execution_failed(self, execution_id: int, error: str):
        """Mark execution as failed."""
        async with get_db_context() as db:
            result = await db.execute(
                select(TestExecution).where(TestExecution.id == execution_id)
            )
            execution = result.scalar_one_or_none()
            if execution:
                execution.status = ExecutionStatus.FAILED
                execution.error_message = error
                execution.completed_at = datetime.utcnow()
                await db.commit()


@celery_app.task(bind=True, base=CallbackTask, name="execute_test_suite")
def execute_test_suite(self, execution_id: int) -> Dict[str, Any]:
    """
    Execute a test suite asynchronously.
    
    Args:
        execution_id: Test execution ID
        
    Returns:
        Dict with execution results
    """
    return asyncio.run(_execute_test_suite_async(execution_id, self.request.id))


async def _execute_test_suite_async(
    execution_id: int,
    task_id: str
) -> Dict[str, Any]:
    """
    Async implementation of test suite execution.
    
    Args:
        execution_id: Test execution ID
        task_id: Celery task ID
        
    Returns:
        Dict with execution results
    """
    async with get_db_context() as db:
        # Get execution
        result = await db.execute(
            select(TestExecution).where(TestExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        
        if not execution:
            return {"success": False, "error": "Execution not found"}
        
        # Update execution status
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.utcnow()
        execution.celery_task_id = task_id
        await db.commit()
        
        # Update cache with real-time status
        await RedisCache.set_json(
            CacheKeys.execution_status(str(execution_id)),
            {
                "status": ExecutionStatus.RUNNING.value,
                "started_at": execution.started_at.isoformat(),
                "progress": 0
            },
            expire=3600
        )
        
        try:
            # Get test cases to execute
            test_cases = await _get_test_cases_for_execution(db, execution)
            
            if not test_cases:
                execution.status = ExecutionStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
                execution.total_tests = 0
                await db.commit()
                return {"success": True, "total_tests": 0}
            
            execution.total_tests = len(test_cases)
            await db.commit()
            
            # Execute each test case
            results = []
            for idx, test_case in enumerate(test_cases):
                result = await _execute_single_test(
                    db,
                    execution,
                    test_case
                )
                results.append(result)
                
                # Update progress
                progress = ((idx + 1) / len(test_cases)) * 100
                await RedisCache.set_json(
                    CacheKeys.execution_status(str(execution_id)),
                    {
                        "status": ExecutionStatus.RUNNING.value,
                        "progress": progress,
                        "completed": idx + 1,
                        "total": len(test_cases)
                    },
                    expire=3600
                )
            
            # Update execution summary
            await _update_execution_summary(db, execution)
            
            # Mark as completed
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = (
                execution.completed_at - execution.started_at
            ).total_seconds()
            await db.commit()
            
            # Update final cache status
            await RedisCache.set_json(
                CacheKeys.execution_status(str(execution_id)),
                {
                    "status": ExecutionStatus.COMPLETED.value,
                    "completed_at": execution.completed_at.isoformat(),
                    "duration": execution.duration_seconds,
                    "pass_rate": execution.pass_rate
                },
                expire=3600
            )
            
            # Store detailed results in MongoDB
            await _store_execution_logs(execution_id, results)
            
            return {
                "success": True,
                "execution_id": execution_id,
                "total_tests": execution.total_tests,
                "passed": execution.passed_tests,
                "failed": execution.failed_tests,
                "duration": execution.duration_seconds
            }
            
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            await db.commit()
            
            await RedisCache.set_json(
                CacheKeys.execution_status(str(execution_id)),
                {
                    "status": ExecutionStatus.FAILED.value,
                    "error": str(e)
                },
                expire=3600
            )
            
            raise


async def _get_test_cases_for_execution(
    db,
    execution: TestExecution
) -> List[TestCase]:
    """Get test cases to execute."""
    if execution.test_suite_id:
        # Get test cases from suite
        result = await db.execute(
            select(TestCase)
            .join(TestCase.test_suites)
            .where(TestCase.test_suites.any(id=execution.test_suite_id))
        )
        return list(result.scalars().all())
    else:
        # Get all active test cases from project
        result = await db.execute(
            select(TestCase).where(
                and_(
                    TestCase.project_id == execution.project_id,
                    TestCase.status == "active"
                )
            )
        )
        return list(result.scalars().all())


async def _execute_single_test(
    db,
    execution: TestExecution,
    test_case: TestCase
) -> TestCaseResult:
    """
    Execute a single test case.
    
    This is a simplified implementation. In production, this would:
    - Execute actual test scripts
    - Run automation frameworks (Selenium, Pytest, etc.)
    - Capture screenshots and logs
    - Handle retries
    """
    start_time = datetime.utcnow()
    
    # Create result record
    result = TestCaseResult(
        execution_id=execution.id,
        test_case_id=test_case.id,
        status=TestResultStatus.PENDING,
        started_at=start_time,
        environment=execution.environment,
    )
    
    db.add(result)
    await db.flush()
    
    try:
        # Simulate test execution
        # In production, this would execute actual test logic
        import random
        await asyncio.sleep(random.uniform(0.1, 0.5))  # Simulate execution time
        
        # Randomly pass/fail for demo (80% pass rate)
        passed = random.random() < 0.8
        
        result.status = TestResultStatus.PASSED if passed else TestResultStatus.FAILED
        result.completed_at = datetime.utcnow()
        result.duration_seconds = (
            result.completed_at - result.started_at
        ).total_seconds()
        
        if not passed:
            result.error_message = "Test assertion failed"
            result.actual_result = "Expected value did not match actual value"
        else:
            result.actual_result = "All assertions passed"
        
        await db.flush()
        await db.refresh(result)
        
        return result
        
    except Exception as e:
        result.status = TestResultStatus.ERROR
        result.error_message = str(e)
        result.completed_at = datetime.utcnow()
        result.duration_seconds = (
            result.completed_at - result.started_at
        ).total_seconds()
        await db.flush()
        await db.refresh(result)
        return result


async def _update_execution_summary(db, execution: TestExecution):
    """Update execution summary counts."""
    result = await db.execute(
        select(TestCaseResult).where(
            TestCaseResult.execution_id == execution.id
        )
    )
    results = result.scalars().all()
    
    execution.passed_tests = sum(
        1 for r in results if r.status == TestResultStatus.PASSED
    )
    execution.failed_tests = sum(
        1 for r in results if r.status == TestResultStatus.FAILED
    )
    execution.skipped_tests = sum(
        1 for r in results if r.status == TestResultStatus.SKIPPED
    )
    execution.blocked_tests = sum(
        1 for r in results if r.status == TestResultStatus.BLOCKED
    )
    execution.error_tests = sum(
        1 for r in results if r.status == TestResultStatus.ERROR
    )
    
    await db.flush()


async def _store_execution_logs(execution_id: int, results: List[TestCaseResult]):
    """Store detailed execution logs in MongoDB."""
    try:
        db = MongoDB.get_database()
        
        # Store execution summary
        log_entry = {
            "execution_id": execution_id,
            "timestamp": datetime.utcnow(),
            "results_count": len(results),
            "results": [
                {
                    "test_case_id": r.test_case_id,
                    "status": r.status.value,
                    "duration": r.duration_seconds,
                    "error": r.error_message
                }
                for r in results
            ]
        }
        
        await db[Collections.EXECUTION_LOGS].insert_one(log_entry)
        
    except Exception as e:
        print(f"Failed to store execution logs: {e}")


@celery_app.task(name="cleanup_old_results")
def cleanup_old_results():
    """Cleanup old execution results (older than 90 days)."""
    return asyncio.run(_cleanup_old_results_async())


async def _cleanup_old_results_async():
    """Async cleanup of old results."""
    cutoff_date = datetime.utcnow() - timedelta(days=90)
    
    async with get_db_context() as db:
        result = await db.execute(
            select(TestExecution).where(
                and_(
                    TestExecution.created_at < cutoff_date,
                    TestExecution.status.in_([
                        ExecutionStatus.COMPLETED,
                        ExecutionStatus.FAILED,
                        ExecutionStatus.CANCELLED
                    ])
                )
            )
        )
        
        old_executions = result.scalars().all()
        
        for execution in old_executions:
            await db.delete(execution)
        
        await db.commit()
        
        return {"cleaned": len(old_executions)}


@celery_app.task(name="cancel_execution")
def cancel_execution(execution_id: int) -> Dict[str, Any]:
    """Cancel a running execution."""
    return asyncio.run(_cancel_execution_async(execution_id))


async def _cancel_execution_async(execution_id: int) -> Dict[str, Any]:
    """Async implementation of execution cancellation."""
    async with get_db_context() as db:
        result = await db.execute(
            select(TestExecution).where(TestExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        
        if not execution:
            return {"success": False, "error": "Execution not found"}
        
        if execution.status not in [ExecutionStatus.RUNNING, ExecutionStatus.QUEUED]:
            return {"success": False, "error": "Execution is not running"}
        
        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = datetime.utcnow()
        await db.commit()
        
        # Update cache
        await RedisCache.delete(CacheKeys.execution_status(str(execution_id)))
        
        return {"success": True, "execution_id": execution_id}
