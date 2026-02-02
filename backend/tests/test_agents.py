"""Tests for the agent implementations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestRouterAgent:
    """Tests for the router agent."""

    @pytest.mark.asyncio
    async def test_route_tableau_query(self, sample_agent_state, mock_vertex_ai):
        """Test routing a Tableau-related query."""
        from src.agents.router import route_query, parse_router_response

        with patch("src.agents.router.create_router_agent") as mock_create:
            mock_llm = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = '{"query_type": "tableau", "reasoning": "User asking about sales", "key_entities": ["sales"]}'
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_llm

            result = await route_query(sample_agent_state)

            assert result["query_type"] == "tableau"

    @pytest.mark.asyncio
    async def test_route_general_query(self, mock_vertex_ai):
        """Test routing a general query."""
        from langchain_core.messages import HumanMessage

        from src.agents.router import route_query
        from src.schemas import create_initial_state

        state = create_initial_state()
        state["messages"] = [HumanMessage(content="What is the capital of France?")]

        with patch("src.agents.router.create_router_agent") as mock_create:
            mock_llm = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = '{"query_type": "general", "reasoning": "General knowledge question", "key_entities": ["France", "capital"]}'
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_llm

            result = await route_query(state)

            assert result["query_type"] == "general"

    def test_parse_router_response_valid_json(self):
        """Test parsing valid JSON response."""
        from src.agents.router import parse_router_response

        response = '{"query_type": "hybrid", "reasoning": "Test", "key_entities": []}'
        query_type, parsed = parse_router_response(response)

        assert query_type == "hybrid"
        assert parsed["reasoning"] == "Test"

    def test_parse_router_response_with_code_block(self):
        """Test parsing response with markdown code block."""
        from src.agents.router import parse_router_response

        response = '''```json
{"query_type": "tableau", "reasoning": "Has Tableau", "key_entities": ["sales"]}
```'''
        query_type, parsed = parse_router_response(response)

        assert query_type == "tableau"

    def test_parse_router_response_invalid(self):
        """Test parsing invalid response defaults to hybrid."""
        from src.agents.router import parse_router_response

        query_type, parsed = parse_router_response("not valid json")

        assert query_type == "hybrid"

    def test_get_route_decision_tableau(self):
        """Test route decision for Tableau queries."""
        from src.agents.router import get_route_decision
        from src.schemas import create_initial_state

        state = create_initial_state()
        state["query_type"] = "tableau"

        decision = get_route_decision(state)
        assert decision == "researcher"

    def test_get_route_decision_general(self):
        """Test route decision for general queries."""
        from src.agents.router import get_route_decision
        from src.schemas import create_initial_state

        state = create_initial_state()
        state["query_type"] = "general"

        decision = get_route_decision(state)
        assert decision == "analyst"


class TestCriticAgent:
    """Tests for the critic agent."""

    @pytest.mark.asyncio
    async def test_validate_approved(self, sample_agent_state, mock_vertex_ai):
        """Test validation approving a response."""
        from src.agents.critic import validate

        sample_agent_state["analysis_result"] = "Total sales by region: East $100K, West $150K"

        with patch("src.agents.critic.create_critic_agent") as mock_create:
            mock_llm = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = '{"status": "approved", "confidence_score": 0.9, "issues": [], "suggestions": [], "reasoning": "Analysis is accurate"}'
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_llm

            result = await validate(sample_agent_state)

            assert result["validation_status"] == "approved"
            assert result["iteration_count"] == 1

    @pytest.mark.asyncio
    async def test_validate_revision_needed(self, sample_agent_state, mock_vertex_ai):
        """Test validation requesting revision."""
        from src.agents.critic import validate

        sample_agent_state["analysis_result"] = "Some incomplete analysis"

        with patch("src.agents.critic.create_critic_agent") as mock_create:
            mock_llm = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = '{"status": "revision_needed", "confidence_score": 0.3, "issues": ["Missing totals"], "suggestions": ["Add sum"], "reasoning": "Incomplete"}'
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_llm

            result = await validate(sample_agent_state)

            assert result["validation_status"] == "revision_needed"
            assert result["revision_notes"] is not None

    @pytest.mark.asyncio
    async def test_max_iterations_forces_approval(self, sample_agent_state, mock_vertex_ai):
        """Test that max iterations forces approval."""
        from src.agents.critic import validate

        sample_agent_state["analysis_result"] = "Analysis"
        sample_agent_state["iteration_count"] = 2  # One less than max (3)

        with patch("src.agents.critic.create_critic_agent") as mock_create:
            mock_llm = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = '{"status": "revision_needed", "confidence_score": 0.3, "issues": ["Issue"], "suggestions": [], "reasoning": "Needs work"}'
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_llm

            # This should be the 3rd iteration
            result = await validate(sample_agent_state)

            assert result["iteration_count"] == 3
            assert result["validation_status"] == "approved"

    def test_should_continue_revision(self):
        """Test should_continue returns analyst for revision."""
        from src.agents.critic import should_continue
        from src.schemas import create_initial_state

        state = create_initial_state()
        state["validation_status"] = "revision_needed"

        decision = should_continue(state)
        assert decision == "analyst"

    def test_should_continue_end(self):
        """Test should_continue returns end for approved."""
        from src.agents.critic import should_continue
        from src.schemas import create_initial_state

        state = create_initial_state()
        state["validation_status"] = "approved"

        decision = should_continue(state)
        assert decision == "end"
