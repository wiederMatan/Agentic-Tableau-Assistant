"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Tableau Configuration
    tableau_server_url: str = Field(
        ...,
        description="Tableau Server or Tableau Cloud URL",
    )
    tableau_site_id: str = Field(
        default="",
        description="Tableau site ID (empty for default site)",
    )
    tableau_token_name: str = Field(
        ...,
        description="Personal Access Token name",
    )
    tableau_token_value: SecretStr = Field(
        ...,
        description="Personal Access Token value",
    )

    # Vertex AI Configuration
    gcp_project_id: str = Field(
        ...,
        description="Google Cloud project ID",
    )
    gcp_location: str = Field(
        default="us-central1",
        description="Google Cloud region for Vertex AI",
    )
    vertex_ai_model: str = Field(
        default="gemini-1.5-pro-002",
        description="Vertex AI model name",
    )

    # Agent Configuration
    max_revision_iterations: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum revision loop iterations before forcing output",
    )
    max_csv_rows: int = Field(
        default=50,
        ge=10,
        le=500,
        description="Maximum rows to include from CSV data",
    )
    python_repl_timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Python REPL execution timeout in seconds",
    )

    # API Configuration
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host",
    )
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="API server port",
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins",
    )
    sse_heartbeat_interval: int = Field(
        default=15,
        ge=5,
        le=60,
        description="SSE heartbeat interval in seconds",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
