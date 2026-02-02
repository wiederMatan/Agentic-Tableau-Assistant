"""Agent definitions for the multi-agent system."""

from .analyst import create_analyst_agent
from .critic import create_critic_agent
from .researcher import create_researcher_agent
from .router import create_router_agent

__all__ = [
    "create_router_agent",
    "create_researcher_agent",
    "create_analyst_agent",
    "create_critic_agent",
]
