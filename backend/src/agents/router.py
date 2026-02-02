"""Router agent for query classification."""

import json
import logging
from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI

from ..config import get_settings
from ..schemas import AgentState
from ..utils import extract_json_from_markdown

logger = logging.getLogger(__name__)

# Load prompt from file
PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "router.md"


def load_router_prompt() -> str:
    """Load the router system prompt."""
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text()
    # Fallback prompt if file not found
    return """You are a query classifier. Classify queries as:
- "tableau": needs Tableau data
- "general": no Tableau data needed
- "hybrid": needs both Tableau data and analysis

Respond with JSON: {"query_type": "...", "reasoning": "...", "key_entities": [...]}"""


def create_router_agent() -> ChatVertexAI:
    """Create the router agent LLM."""
    settings = get_settings()
    return ChatVertexAI(
        model=settings.vertex_ai_model,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
        temperature=0,  # Deterministic classification
        max_tokens=500,
    )


def parse_router_response(
    response: str,
) -> tuple[Literal["tableau", "general", "hybrid"], dict[str, Any]]:
    """Parse the router's JSON response.

    Args:
        response: Raw response from the router agent.

    Returns:
        Tuple of (query_type, full_response_dict).
    """
    try:
        # Extract JSON from potential markdown code blocks
        json_str = extract_json_from_markdown(response)

        parsed = json.loads(json_str)
        query_type = parsed.get("query_type", "hybrid")

        # Validate query_type
        if query_type not in ("tableau", "general", "hybrid"):
            logger.warning(f"Invalid query_type '{query_type}', defaulting to 'hybrid'")
            query_type = "hybrid"

        return query_type, parsed

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse router response: {e}")
        # Default to hybrid if parsing fails
        return "hybrid", {"query_type": "hybrid", "reasoning": "Failed to parse", "key_entities": []}


async def route_query(state: AgentState) -> AgentState:
    """Route a query to determine the processing pipeline.

    This is the node function for the LangGraph.

    Args:
        state: Current agent state.

    Returns:
        Updated state with query_type set.
    """
    logger.info("Router: Classifying query")

    # Get the latest user message
    messages = state["messages"]
    user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break

    if not user_message:
        logger.warning("Router: No user message found")
        state["query_type"] = "general"
        return state

    # Create and invoke the router
    llm = create_router_agent()
    system_prompt = load_router_prompt()

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ])

    # Parse the response
    query_type, parsed = parse_router_response(response.content)

    logger.info(f"Router: Classified as '{query_type}' - {parsed.get('reasoning', '')}")

    state["query_type"] = query_type
    return state


def get_route_decision(state: AgentState) -> str:
    """Determine the next node based on query type.

    This is the conditional edge function for the LangGraph.

    Args:
        state: Current agent state.

    Returns:
        Name of the next node to execute.
    """
    query_type = state.get("query_type", "hybrid")

    if query_type == "general":
        # Skip directly to analyst for general questions
        return "analyst"
    else:
        # tableau and hybrid both need research first
        return "researcher"
