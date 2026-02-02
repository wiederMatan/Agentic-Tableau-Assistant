"""FastAPI application with SSE streaming endpoint."""

import json
import logging
from datetime import datetime
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from .config import get_settings
from .constants import LOG_MESSAGE_TRUNCATE_LENGTH
from .graph import run_agent, stream_agent
from .schemas import ChatRequest, SSEEvent

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Tableau Analytics Agent API",
    description="Conversational analytics agent for Tableau dashboards",
    version="0.1.0",
)


def configure_cors() -> None:
    """Configure CORS middleware."""
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Configure CORS on startup
configure_cors()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions globally."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if get_settings().environment == "development" else None,
        },
    )


def format_sse_event(event: str, data: dict) -> str:
    """Format data as SSE event string."""
    return json.dumps({
        "event": event,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def event_generator(
    message: str,
    conversation_id: str | None,
) -> AsyncIterator[dict]:
    """Generate SSE events for the agent workflow.

    Args:
        message: User's chat message.
        conversation_id: Optional conversation ID.

    Yields:
        SSE event dictionaries.
    """
    settings = get_settings()
    heartbeat_interval = settings.sse_heartbeat_interval
    last_heartbeat = datetime.utcnow()

    try:
        # Stream agent events
        async for event in stream_agent(message, conversation_id):
            yield {
                "event": event["event"],
                "data": json.dumps(event["data"]),
            }

            # Check if we need to send a heartbeat
            now = datetime.utcnow()
            if (now - last_heartbeat).seconds >= heartbeat_interval:
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({"timestamp": now.isoformat()}),
                }
                last_heartbeat = now

    except Exception as e:
        # Broad exception handler at API boundary - convert any streaming error to SSE error event
        logger.error(f"Error in event generator: {e}", exc_info=True)
        yield {
            "event": "error",
            "data": json.dumps({
                "error": str(e),
                "type": type(e).__name__,
            }),
        }
        yield {
            "event": "done",
            "data": json.dumps({}),
        }


@app.post("/api/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    """Stream chat response using Server-Sent Events.

    Args:
        request: Chat request containing the user message.

    Returns:
        EventSourceResponse streaming agent events.
    """
    logger.info(f"Received chat request: {request.message[:LOG_MESSAGE_TRUNCATE_LENGTH]}...")

    return EventSourceResponse(
        event_generator(request.message, request.conversation_id),
        media_type="text/event-stream",
    )


@app.post("/api/chat/sync")
async def chat_sync(request: ChatRequest) -> dict:
    """Synchronous chat endpoint (non-streaming).

    Useful for testing and simple integrations.

    Args:
        request: Chat request containing the user message.

    Returns:
        Final agent response.
    """
    logger.info(f"Received sync chat request: {request.message[:LOG_MESSAGE_TRUNCATE_LENGTH]}...")

    try:
        final_state = await run_agent(request.message, request.conversation_id)

        return {
            "success": True,
            "response": final_state.get("analysis_result", ""),
            "query_type": final_state.get("query_type"),
            "iterations": final_state.get("iteration_count", 1),
            "validation_status": final_state.get("validation_status"),
        }
    except Exception as e:
        # Broad exception handler at API boundary - convert any agent error to HTTP 500
        logger.error(f"Error in sync chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status and configuration info.
    """
    settings = get_settings()
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.environment,
        "model": settings.vertex_ai_model,
    }


@app.get("/api/config")
async def get_config() -> dict:
    """Get public configuration settings.

    Returns:
        Non-sensitive configuration values.
    """
    settings = get_settings()
    return {
        "max_revision_iterations": settings.max_revision_iterations,
        "max_csv_rows": settings.max_csv_rows,
        "sse_heartbeat_interval": settings.sse_heartbeat_interval,
        "environment": settings.environment,
    }
