"""
TestFlow Platform - Core Configuration Module

This module handles all application configuration using Pydantic Settings.
Configuration values are loaded from environment variables and .env files.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    This class uses Pydantic's BaseSettings to automatically load
    configuration from environment variables and .env files.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application Settings
    app_name: str = "TestFlow"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Security Settings
    secret_key: str = "change-this-in-production"
    jwt_secret_key: str = "change-this-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # PostgreSQL Settings
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "testflow"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def sync_database_url(self) -> str:
        """Construct synchronous PostgreSQL connection URL for Alembic."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    # MongoDB Settings
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "testflow"
    mongodb_max_pool_size: int = 100
    mongodb_min_pool_size: int = 10
    
    # Redis Settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # RabbitMQ Settings
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = "/"
    
    @property
    def rabbitmq_url(self) -> str:
        """Construct RabbitMQ connection URL."""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{self.rabbitmq_vhost}"
        )
    
    # Celery Settings
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    celery_task_always_eager: bool = False
    
    @property
    def celery_broker(self) -> str:
        """Get Celery broker URL."""
        return self.celery_broker_url or self.rabbitmq_url
    
    @property
    def celery_backend(self) -> str:
        """Get Celery result backend URL."""
        return self.celery_result_backend or f"{self.redis_url}"
    
    # CORS Settings
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    cors_allow_credentials: bool = True
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Handle JSON-like string
            if v.startswith("["):
                import json
                return json.loads(v)
            # Handle comma-separated string
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # Logging Settings
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Sentry Settings (Optional)
    sentry_dsn: Optional[str] = None
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60
    
    # File Upload Settings
    max_upload_size: int = 10485760  # 10MB
    upload_dir: str = "./uploads"
    
    # Pagination Settings
    default_page_size: int = 20
    max_page_size: int = 100


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Using lru_cache ensures settings are only loaded once,
    improving performance by avoiding repeated file I/O.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Export settings instance for convenience
settings = get_settings()
