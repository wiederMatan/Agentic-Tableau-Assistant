"""Entry point for the Tableau Analytics Agent API."""

import logging
import sys
from pathlib import Path

import uvicorn

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_settings


def configure_logging() -> None:
    """Configure logging based on settings."""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def main() -> None:
    """Run the FastAPI application."""
    configure_logging()
    settings = get_settings()

    logger = logging.getLogger(__name__)
    logger.info(f"Starting Tableau Analytics Agent API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Model: {settings.vertex_ai_model}")

    uvicorn.run(
        "src.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
