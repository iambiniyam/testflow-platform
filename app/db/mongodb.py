"""
TestFlow Platform - MongoDB Database Connection

This module provides async MongoDB connectivity using Motor,
the official async Python driver for MongoDB.
"""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure

from app.core.config import settings


class MongoDB:
    """
    MongoDB connection manager using Motor async driver.
    
    This class manages the MongoDB client connection and provides
    access to the database instance.
    """
    
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls) -> None:
        """
        Establish connection to MongoDB.
        
        This should be called during application startup.
        """
        cls.client = AsyncIOMotorClient(
            settings.mongodb_url,
            maxPoolSize=settings.mongodb_max_pool_size,
            minPoolSize=settings.mongodb_min_pool_size,
            serverSelectionTimeoutMS=5000,
        )
        cls.database = cls.client[settings.mongodb_db]
        
        # Verify connection
        try:
            await cls.client.admin.command("ping")
            print(f"Connected to MongoDB: {settings.mongodb_db}")
        except ConnectionFailure as e:
            print(f"Failed to connect to MongoDB: {e}")
            raise
    
    @classmethod
    async def disconnect(cls) -> None:
        """
        Close MongoDB connection.
        
        This should be called during application shutdown.
        """
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.database = None
            print("Disconnected from MongoDB")
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """
        Get the MongoDB database instance.
        
        Returns:
            AsyncIOMotorDatabase: The database instance
            
        Raises:
            RuntimeError: If not connected to MongoDB
        """
        if cls.database is None:
            raise RuntimeError("MongoDB is not connected. Call connect() first.")
        return cls.database
    
    @classmethod
    def get_collection(cls, name: str):
        """
        Get a MongoDB collection by name.
        
        Args:
            name: Collection name
            
        Returns:
            Collection: The MongoDB collection
        """
        return cls.get_database()[name]


# Collection names as constants
class Collections:
    """MongoDB collection names."""
    
    TEST_RESULTS = "test_results"
    EXECUTION_LOGS = "execution_logs"
    TEST_ARTIFACTS = "test_artifacts"
    METRICS = "metrics"
    AUDIT_LOGS = "audit_logs"


async def get_mongodb() -> AsyncIOMotorDatabase:
    """
    Dependency that provides MongoDB database instance.
    
    This is a FastAPI dependency for injecting MongoDB access
    into route handlers.
    
    Returns:
        AsyncIOMotorDatabase: MongoDB database instance
    """
    return MongoDB.get_database()


async def init_mongodb_indexes() -> None:
    """
    Create MongoDB indexes for optimal query performance.
    
    This should be called during application startup to ensure
    all required indexes exist.
    """
    db = MongoDB.get_database()
    
    # Test Results collection indexes
    await db[Collections.TEST_RESULTS].create_index("execution_id")
    await db[Collections.TEST_RESULTS].create_index("test_case_id")
    await db[Collections.TEST_RESULTS].create_index("status")
    await db[Collections.TEST_RESULTS].create_index([
        ("execution_id", 1),
        ("created_at", -1)
    ])
    
    # Execution Logs collection indexes
    await db[Collections.EXECUTION_LOGS].create_index("execution_id")
    await db[Collections.EXECUTION_LOGS].create_index([
        ("execution_id", 1),
        ("timestamp", 1)
    ])
    
    # Metrics collection indexes
    await db[Collections.METRICS].create_index([
        ("project_id", 1),
        ("metric_type", 1),
        ("timestamp", -1)
    ])
    
    # Audit Logs collection indexes
    await db[Collections.AUDIT_LOGS].create_index("user_id")
    await db[Collections.AUDIT_LOGS].create_index("action")
    await db[Collections.AUDIT_LOGS].create_index([
        ("created_at", -1)
    ])
    
    print("MongoDB indexes created successfully")
