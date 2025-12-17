"""
TestFlow Platform - Redis Cache Connection

This module provides Redis connectivity for caching and
as a result backend for Celery tasks.
"""

from typing import Optional, Any, Union
import json

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings


class RedisCache:
    """
    Redis cache manager for async operations.
    
    Provides methods for common caching operations including
    get, set, delete, and various data structure operations.
    """
    
    client: Optional[Redis] = None
    
    @classmethod
    async def connect(cls) -> None:
        """
        Establish connection to Redis.
        
        This should be called during application startup.
        """
        cls.client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        
        # Verify connection
        try:
            await cls.client.ping()
            print(f"Connected to Redis: {settings.redis_host}:{settings.redis_port}")
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            raise
    
    @classmethod
    async def disconnect(cls) -> None:
        """
        Close Redis connection.
        
        This should be called during application shutdown.
        """
        if cls.client:
            await cls.client.close()
            cls.client = None
            print("Disconnected from Redis")
    
    @classmethod
    def get_client(cls) -> Redis:
        """
        Get the Redis client instance.
        
        Returns:
            Redis: The Redis client
            
        Raises:
            RuntimeError: If not connected to Redis
        """
        if cls.client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return cls.client
    
    @classmethod
    async def get(cls, key: str) -> Optional[str]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            The cached value or None if not found
        """
        return await cls.get_client().get(key)
    
    @classmethod
    async def get_json(cls, key: str) -> Optional[Any]:
        """
        Get a JSON value from cache and deserialize it.
        
        Args:
            key: Cache key
            
        Returns:
            The deserialized value or None if not found
        """
        value = await cls.get(key)
        if value:
            return json.loads(value)
        return None
    
    @classmethod
    async def set(
        cls,
        key: str,
        value: Union[str, bytes],
        expire: Optional[int] = None
    ) -> bool:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            expire: Optional TTL in seconds
            
        Returns:
            bool: True if successful
        """
        return await cls.get_client().set(key, value, ex=expire)
    
    @classmethod
    async def set_json(
        cls,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """
        Serialize a value as JSON and store in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            expire: Optional TTL in seconds
            
        Returns:
            bool: True if successful
        """
        return await cls.set(key, json.dumps(value), expire)
    
    @classmethod
    async def delete(cls, key: str) -> int:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            int: Number of keys deleted
        """
        return await cls.get_client().delete(key)
    
    @classmethod
    async def delete_pattern(cls, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Key pattern (e.g., "user:*")
            
        Returns:
            int: Number of keys deleted
        """
        client = cls.get_client()
        keys = []
        async for key in client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            return await client.delete(*keys)
        return 0
    
    @classmethod
    async def exists(cls, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if key exists
        """
        return await cls.get_client().exists(key) > 0
    
    @classmethod
    async def incr(cls, key: str) -> int:
        """
        Increment a counter.
        
        Args:
            key: Counter key
            
        Returns:
            int: New value after increment
        """
        return await cls.get_client().incr(key)
    
    @classmethod
    async def expire(cls, key: str, seconds: int) -> bool:
        """
        Set expiration time on a key.
        
        Args:
            key: Cache key
            seconds: TTL in seconds
            
        Returns:
            bool: True if successful
        """
        return await cls.get_client().expire(key, seconds)
    
    @classmethod
    async def ttl(cls, key: str) -> int:
        """
        Get remaining TTL for a key.
        
        Args:
            key: Cache key
            
        Returns:
            int: TTL in seconds, -1 if no TTL, -2 if key doesn't exist
        """
        return await cls.get_client().ttl(key)


# Cache key prefixes for organization
class CacheKeys:
    """Cache key prefixes and patterns."""
    
    USER = "user:{user_id}"
    USER_BY_EMAIL = "user:email:{email}"
    PROJECT = "project:{project_id}"
    PROJECT_LIST = "projects:user:{user_id}"
    TEST_CASE = "test_case:{test_case_id}"
    TEST_SUITE = "test_suite:{suite_id}"
    EXECUTION = "execution:{execution_id}"
    EXECUTION_STATUS = "execution:status:{execution_id}"
    REPORT = "report:{report_id}"
    RATE_LIMIT = "rate_limit:{client_id}:{endpoint}"
    
    @staticmethod
    def user(user_id: str) -> str:
        return f"user:{user_id}"
    
    @staticmethod
    def project(project_id: str) -> str:
        return f"project:{project_id}"
    
    @staticmethod
    def test_case(test_case_id: str) -> str:
        return f"test_case:{test_case_id}"
    
    @staticmethod
    def execution_status(execution_id: str) -> str:
        return f"execution:status:{execution_id}"
    
    @staticmethod
    def rate_limit(client_id: str, endpoint: str) -> str:
        return f"rate_limit:{client_id}:{endpoint}"


async def get_redis() -> Redis:
    """
    Dependency that provides Redis client.
    
    This is a FastAPI dependency for injecting Redis access
    into route handlers.
    
    Returns:
        Redis: Redis client instance
    """
    return RedisCache.get_client()
