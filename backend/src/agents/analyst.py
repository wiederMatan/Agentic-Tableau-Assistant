"""Analyst agent for data analysis."""

import logging
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_vertexai import ChatVertexAI

from ..config import get_settings
from ..schemas import AgentState
from ..tools import python_repl

logger = logging.getLogger(__name__)

# Load prompt from file
PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "analyst.md"


def load_analyst_prompt() -> str:
    """Load the analyst system prompt."""
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text()
    return """You are a data analyst. Analyze the provided data and answer the user's question."""


def create_analyst_agent() -> ChatVertexAI:
    """Create the analyst agent LLM with tools."""
    settings = get_settings()

    llm = ChatVertexAI(
        model=settings.vertex_ai_model,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
        temperature=0.2,
        max_tokens=4096,
    )

    # Bind the python_repl tool
    return llm.bind_tools([python_repl])


def _format_context(state: AgentState) -> str:
    """Format the research context for the analyst."""
    context_parts = []

    # Add data dictionary if available
    if state.get("data_dictionary"):
        dd = state["data_dictionary"]
        if isinstance(dd, dict) and dd.get("success"):
            context_parts.append(f"## Data Dictionary\n")
            context_parts.append(f"Workbook: {dd.get('workbook_name', 'Unknown')}\n")
            if dd.get("views"):
                context_parts.append("Views:\n")
                for view in dd["views"]:
                    context_parts.append(f"  - {view.get('name', 'Unknown')}\n")

    # Add CSV data if available
    if state.get("raw_data"):
        raw = state["raw_data"]
        if "csv_data" in raw and raw["csv_data"].get("success"):
            csv_content = raw["csv_data"].get("csv_data", "")
            row_count = raw["csv_data"].get("row_count", 0)
            context_parts.append(f"\n## Data (CSV format, {row_count} rows)\n")
            context_parts.append(f"```csv\n{csv_content}\n```\n")

        if "search_results" in raw and raw["search_results"].get("success"):
            results = raw["search_results"]["results"]
            context_parts.append("\n## Available Tableau Assets\n")
            for asset_type, assets in results.items():
                if assets:
                    context_parts.append(f"### {asset_type.title()}\n")
                    for asset in assets[:5]:
                        context_parts.append(f"  - {asset.get('name', 'Unknown')} (LUID: {asset.get('luid', 'N/A')})\n")

    # Add revision notes if this is a revision
    if state.get("revision_notes"):
        context_parts.append(f"\n## Revision Requested\n")
        context_parts.append(f"{state['revision_notes']}\n")

    return "".join(context_parts)


async def analyze(state: AgentState) -> AgentState:
    """Analyze data and generate insights.

    This is the node function for the LangGraph.

    Args:
        state: Current agent state.

    Returns:
        Updated state with analysis_result.
    """
    logger.info("Analyst: Starting analysis")

    # Get the user's query
    messages = state["messages"]
    user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break

    if not user_message:
        logger.warning("Analyst: No user message found")
        state["analysis_result"] = "Unable to process: no user query found."
        return state

    # Build context from research
    context = _format_context(state)

    # Create the analyst agent
    llm = create_analyst_agent()
    system_prompt = load_analyst_prompt()

    # Build the prompt
    analysis_prompt = f"""User Query: {user_message}

{context}

Analyze this data to answer the user's question. Use the python_repl tool if calculations are needed."""

    agent_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=analysis_prompt),
    ]

    # Run the agent loop
    max_iterations = 5
    iteration = 0
    final_response = ""

    while iteration < max_iterations:
        iteration += 1
        logger.debug(f"Analyst: Iteration {iteration}")

        response = await llm.ainvoke(agent_messages)

        # Check for tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                logger.info(f"Analyst: Executing Python code")

                if tool_name == "python_repl":
                    result = python_repl.invoke(tool_args)
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}

                # Add tool result to messages
                agent_messages.append(response)
                agent_messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )
        else:
            # No more tool calls, capture final response
            final_response = response.content
            logger.info("Analyst: Completed analysis")
            break

    state["analysis_result"] = final_response
    state["messages"].append(
        AIMessage(content=f"[Analyst] {final_response}", name="analyst")
    )

    return state
