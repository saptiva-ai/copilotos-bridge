"""
MongoDB database configuration using Motor and Beanie
"""

from typing import Optional

import structlog
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.server_api import ServerApi

from .config import get_settings

logger = structlog.get_logger()


class Database:
    """MongoDB database manager"""
    
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect_to_mongo(cls) -> None:
        """Create database connection"""
        settings = get_settings()
        
        logger.info("Connecting to MongoDB", url=settings.mongodb_url.split("@")[-1])
        
        cls.client = AsyncIOMotorClient(
            settings.mongodb_url,
            minPoolSize=settings.db_min_pool_size,
            maxPoolSize=settings.db_max_pool_size,
            connectTimeoutMS=settings.db_connect_timeout_ms,
            serverSelectionTimeoutMS=settings.db_server_selection_timeout_ms,
            maxIdleTimeMS=settings.db_max_idle_time_ms,
            server_api=ServerApi('1')  # Use Stable API version 1
        )
        
        # Get database name from URL or use default
        db_name = settings.mongodb_url.split("/")[-1].split("?")[0]
        cls.database = cls.client[db_name]
        
        # Test connection
        try:
            await cls.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB", database=db_name)
        except Exception as e:
            logger.error("Failed to connect to MongoDB", error=str(e))
            raise

        # Initialize Beanie with document models
        from ..models import get_document_models
        await init_beanie(
            database=cls.database,
            document_models=get_document_models()
        )
        logger.info("Beanie ODM initialized with document models")

    @classmethod
    async def close_mongo_connection(cls) -> None:
        """Close database connection"""
        if cls.client:
            logger.info("Closing MongoDB connection")
            cls.client.close()
            cls.client = None
            cls.database = None

    @classmethod
    async def ping(cls) -> bool:
        """Check database connection"""
        if not cls.client:
            return False
        try:
            await cls.client.admin.command('ping')
            return True
        except Exception as e:
            logger.warning("MongoDB ping failed", error=str(e))
            return False

    @classmethod
    def get_client(cls) -> Optional[AsyncIOMotorClient]:
        """Get MongoDB client instance"""
        return cls.client

    @classmethod
    def get_database(cls) -> Optional[AsyncIOMotorDatabase]:
        """Get database instance"""
        return cls.database


# Dependency for FastAPI
async def get_database() -> AsyncIOMotorDatabase:
    """FastAPI dependency to get database instance"""
    if Database.database is None:
        raise RuntimeError("Database not initialized")
    return Database.database