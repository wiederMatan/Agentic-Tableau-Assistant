"""Researcher agent for Tableau data retrieval."""

import logging
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_vertexai import ChatVertexAI

from ..config import get_settings
from ..schemas import AgentState
from ..tools import get_data_dictionary, get_view_data_as_csv, search_tableau_assets

logger = logging.getLogger(__name__)

# Load prompt from file
PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "researcher.md"


def load_researcher_prompt() -> str:
    """Load the researcher system prompt."""
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text()
    return """You are a Tableau data researcher. Use the available tools to find and retrieve data from Tableau Server."""


def create_researcher_agent() -> ChatVertexAI:
    """Create the researcher agent LLM with tools."""
    settings = get_settings()

    llm = ChatVertexAI(
        model=settings.vertex_ai_model,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
        temperature=0.1,
        max_tokens=4096,
    )

    # Bind Tableau tools
    tools = [search_tableau_assets, get_data_dictionary, get_view_data_as_csv]
    return llm.bind_tools(tools)


async def research(state: AgentState) -> AgentState:
    """Execute research to find and retrieve Tableau data.

    This is the node function for the LangGraph.

    Args:
        state: Current agent state.

    Returns:
        Updated state with raw_data and data_dictionary.
    """
    logger.info("Researcher: Starting data retrieval")

    # Get the user's query from messages
    messages = state["messages"]
    user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break

    if not user_message:
        logger.warning("Researcher: No user message found")
        return state

    # Create the researcher agent
    llm = create_researcher_agent()
    system_prompt = load_researcher_prompt()

    # Build the conversation for the agent
    agent_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User query: {user_message}\n\nFind and retrieve the relevant Tableau data."),
    ]

    # Run the agent loop (simplified - in production use langgraph's prebuilt agent)
    raw_data = {}
    data_dictionary = {}
    max_iterations = 5
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        logger.debug(f"Researcher: Iteration {iteration}")

        response = await llm.ainvoke(agent_messages)

        # Check for tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                logger.info(f"Researcher: Calling tool '{tool_name}' with args {tool_args}")

                # Execute the tool
                if tool_name == "search_tableau_assets":
                    result = search_tableau_assets.invoke(tool_args)
                    raw_data["search_results"] = result
                elif tool_name == "get_data_dictionary":
                    result = get_data_dictionary.invoke(tool_args)
                    data_dictionary = result
                elif tool_name == "get_view_data_as_csv":
                    result = get_view_data_as_csv.invoke(tool_args)
                    raw_data["csv_data"] = result
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}

                # Add tool result to messages
                agent_messages.append(response)
                agent_messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )
        else:
            # No more tool calls, agent is done
            logger.info("Researcher: Completed data retrieval")

            # Add the final summary to state
            if response.content:
                state["messages"].append(
                    AIMessage(
                        content=f"[Researcher] {response.content}",
                        name="researcher",
                    )
                )
            break

    state["raw_data"] = raw_data
    state["data_dictionary"] = data_dictionary

    logger.info(f"Researcher: Retrieved data keys: {list(raw_data.keys())}")
    return state
