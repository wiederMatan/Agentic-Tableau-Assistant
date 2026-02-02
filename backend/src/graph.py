"""LangGraph state graph definition for the multi-agent system."""

import logging
from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph

from .agents.analyst import analyze
from .agents.critic import should_continue, validate
from .agents.researcher import research
from .agents.router import get_route_decision, route_query
from .schemas import AgentState, create_initial_state

logger = logging.getLogger(__name__)


def create_graph() -> StateGraph:
    """Create the multi-agent state graph.

    Graph Structure:
        START -> router -> [researcher | analyst]
        researcher -> analyst
        analyst -> critic
        critic -> [analyst (revision) | END]

    Returns:
        Compiled StateGraph ready for execution.
    """
    # Create the graph with AgentState
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", route_query)
    graph.add_node("researcher", research)
    graph.add_node("analyst", analyze)
    graph.add_node("critic", validate)

    # Set entry point
    graph.set_entry_point("router")

    # Add edges from router (conditional)
    graph.add_conditional_edges(
        "router",
        get_route_decision,
        {
            "researcher": "researcher",
            "analyst": "analyst",
        },
    )

    # Researcher always goes to analyst
    graph.add_edge("researcher", "analyst")

    # Analyst always goes to critic
    graph.add_edge("analyst", "critic")

    # Critic conditionally loops back or ends
    graph.add_conditional_edges(
        "critic",
        should_continue,
        {
            "analyst": "analyst",
            "end": END,
        },
    )

    return graph


def compile_graph():
    """Compile the graph for execution.

    Returns:
        Compiled graph that can be invoked.
    """
    graph = create_graph()
    return graph.compile()


# Create a singleton compiled graph
_compiled_graph = None


def get_compiled_graph():
    """Get or create the compiled graph singleton."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = compile_graph()
    return _compiled_graph


async def run_agent(
    user_message: str,
    conversation_id: str | None = None,
) -> AgentState:
    """Run the agent graph with a user message.

    Args:
        user_message: The user's natural language query.
        conversation_id: Optional conversation ID for context.

    Returns:
        Final agent state after graph execution.
    """
    logger.info(f"Starting agent run for query: {user_message[:100]}...")

    # Initialize state
    state = create_initial_state()
    state["messages"] = [HumanMessage(content=user_message)]

    # Get the compiled graph
    graph = get_compiled_graph()

    # Run the graph
    final_state = await graph.ainvoke(state)

    logger.info("Agent run completed")
    return final_state


async def stream_agent(
    user_message: str,
    conversation_id: str | None = None,
) -> AsyncIterator[dict]:
    """Stream agent execution events.

    Yields events for each step of the agent workflow, suitable for
    Server-Sent Events streaming.

    Args:
        user_message: The user's natural language query.
        conversation_id: Optional conversation ID for context.

    Yields:
        Event dictionaries with type and data.
    """
    logger.info(f"Starting streaming agent run for query: {user_message[:100]}...")

    # Initialize state
    state = create_initial_state()
    state["messages"] = [HumanMessage(content=user_message)]

    # Get the compiled graph
    graph = get_compiled_graph()

    # Stream execution
    async for event in graph.astream(state, stream_mode="updates"):
        for node_name, node_output in event.items():
            logger.debug(f"Stream event from node: {node_name}")

            yield {
                "event": "agent_start",
                "data": {
                    "agent": node_name,
                    "status": "running",
                },
            }

            # Extract relevant state updates
            if node_name == "router":
                yield {
                    "event": "tool_result",
                    "data": {
                        "agent": "router",
                        "query_type": node_output.get("query_type"),
                    },
                }

            elif node_name == "researcher":
                raw_data = node_output.get("raw_data", {})
                yield {
                    "event": "tool_result",
                    "data": {
                        "agent": "researcher",
                        "data_retrieved": bool(raw_data),
                        "data_keys": list(raw_data.keys()) if raw_data else [],
                    },
                }

            elif node_name == "analyst":
                analysis = node_output.get("analysis_result", "")
                yield {
                    "event": "tool_result",
                    "data": {
                        "agent": "analyst",
                        "has_result": bool(analysis),
                    },
                }
                # Stream the analysis text
                if analysis:
                    yield {
                        "event": "token",
                        "data": {
                            "content": analysis,
                        },
                    }

            elif node_name == "critic":
                yield {
                    "event": "validation",
                    "data": {
                        "status": node_output.get("validation_status"),
                        "iteration": node_output.get("iteration_count"),
                        "revision_needed": node_output.get("validation_status") == "revision_needed",
                    },
                }

    # Get final state
    final_state = await graph.ainvoke(state)
    analysis_result = final_state.get("analysis_result", "")

    yield {
        "event": "complete",
        "data": {
            "content": analysis_result,
            "query_type": final_state.get("query_type"),
            "iterations": final_state.get("iteration_count", 1),
        },
    }

    yield {
        "event": "done",
        "data": {},
    }
