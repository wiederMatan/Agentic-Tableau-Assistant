"""Critic agent for validation."""

import json
import logging
from pathlib import Path
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI

from ..config import get_settings
from ..schemas import AgentState, ValidationResult

logger = logging.getLogger(__name__)

# Load prompt from file
PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "critic.md"


def load_critic_prompt() -> str:
    """Load the critic system prompt."""
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text()
    return """You are a quality assurance agent. Validate the analysis response and output JSON with status, confidence_score, issues, suggestions, and reasoning."""


def create_critic_agent() -> ChatVertexAI:
    """Create the critic agent LLM."""
    settings = get_settings()
    return ChatVertexAI(
        model=settings.vertex_ai_model,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
        temperature=0,
        max_tokens=2048,
    )


def parse_validation_response(response: str) -> ValidationResult:
    """Parse the critic's JSON response.

    Args:
        response: Raw response from the critic agent.

    Returns:
        ValidationResult object.
    """
    try:
        response = response.strip()

        # Handle markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()

        parsed = json.loads(response)
        return ValidationResult(**parsed)

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to parse critic response: {e}")
        # Default to approved if parsing fails (don't block on errors)
        return ValidationResult(
            status="approved",
            confidence_score=0.5,
            issues=["Failed to parse validation response"],
            suggestions=[],
            reasoning="Defaulting to approved due to parsing error",
        )


async def validate(state: AgentState) -> AgentState:
    """Validate the analyst's response.

    This is the node function for the LangGraph.

    Args:
        state: Current agent state.

    Returns:
        Updated state with validation status.
    """
    settings = get_settings()
    iteration = state.get("iteration_count", 0) + 1
    state["iteration_count"] = iteration

    logger.info(f"Critic: Validating analysis (iteration {iteration})")

    # Check if we've exceeded max iterations
    if iteration >= settings.max_revision_iterations:
        logger.warning(f"Critic: Max iterations ({settings.max_revision_iterations}) reached, forcing approval")
        state["validation_status"] = "approved"
        state["messages"].append(
            AIMessage(
                content="[Critic] Approved after maximum revision attempts. Note: Some quality concerns may remain.",
                name="critic",
            )
        )
        return state

    # Get the analysis result
    analysis_result = state.get("analysis_result", "")
    if not analysis_result:
        logger.warning("Critic: No analysis result to validate")
        state["validation_status"] = "approved"
        return state

    # Get the original user query
    user_message = None
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break

    # Build validation prompt
    raw_data_summary = ""
    if state.get("raw_data") and state["raw_data"].get("csv_data"):
        csv_data = state["raw_data"]["csv_data"]
        if csv_data.get("success"):
            raw_data_summary = f"\nSource data ({csv_data.get('row_count', 0)} rows):\n{csv_data.get('csv_data', '')[:2000]}"

    validation_prompt = f"""## User's Original Question
{user_message}

## Analyst's Response
{analysis_result}

## Source Data
{raw_data_summary}

Please validate the analyst's response. Output your assessment as JSON."""

    # Create and invoke the critic
    llm = create_critic_agent()
    system_prompt = load_critic_prompt()

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=validation_prompt),
    ])

    # Parse the validation result
    validation = parse_validation_response(response.content)

    logger.info(
        f"Critic: Status={validation.status}, Confidence={validation.confidence_score:.2f}"
    )

    # Update state
    state["validation_status"] = validation.status

    if validation.status == "revision_needed":
        # Format revision notes for the analyst
        revision_notes = []
        if validation.issues:
            revision_notes.append("Issues found:")
            for issue in validation.issues:
                revision_notes.append(f"  - {issue}")
        if validation.suggestions:
            revision_notes.append("\nSuggestions:")
            for suggestion in validation.suggestions:
                revision_notes.append(f"  - {suggestion}")

        state["revision_notes"] = "\n".join(revision_notes)
        state["messages"].append(
            AIMessage(
                content=f"[Critic] Revision needed:\n{state['revision_notes']}",
                name="critic",
            )
        )
    else:
        state["revision_notes"] = None
        state["messages"].append(
            AIMessage(
                content=f"[Critic] Approved (confidence: {validation.confidence_score:.0%})",
                name="critic",
            )
        )

    return state


def should_continue(state: AgentState) -> Literal["analyst", "end"]:
    """Determine if we should revise or end.

    This is the conditional edge function for the LangGraph.

    Args:
        state: Current agent state.

    Returns:
        "analyst" to revise, "end" to finish.
    """
    if state.get("validation_status") == "revision_needed":
        logger.info("Critic: Requesting revision from analyst")
        return "analyst"
    else:
        logger.info("Critic: Analysis approved, ending workflow")
        return "end"
