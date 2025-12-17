"""Database module initialization."""

from app.db.postgresql import (
    Base,
    engine,
    async_session_maker,
    get_db,
    get_db_context,
    init_db,
    close_db,
)
from app.db.mongodb import (
    MongoDB,
    Collections,
    get_mongodb,
    init_mongodb_indexes,
)
from app.db.redis import (
    RedisCache,
    CacheKeys,
    get_redis,
)

__all__ = [
    # PostgreSQL
    "Base",
    "engine",
    "async_session_maker",
    "get_db",
    "get_db_context",
    "init_db",
    "close_db",
    # MongoDB
    "MongoDB",
    "Collections",
    "get_mongodb",
    "init_mongodb_indexes",
    # Redis
    "RedisCache",
    "CacheKeys",
    "get_redis",
]
