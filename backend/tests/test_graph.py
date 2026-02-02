"""Tests for the LangGraph workflow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestGraphConstruction:
    """Tests for graph construction."""

    def test_create_graph(self):
        """Test that the graph can be created."""
        from src.graph import create_graph

        graph = create_graph()

        assert graph is not None
        # Check that all nodes are present
        assert "router" in graph.nodes
        assert "researcher" in graph.nodes
        assert "analyst" in graph.nodes
        assert "critic" in graph.nodes

    def test_compile_graph(self):
        """Test that the graph can be compiled."""
        from src.graph import compile_graph

        compiled = compile_graph()

        assert compiled is not None

    def test_get_compiled_graph_singleton(self):
        """Test that get_compiled_graph returns a singleton."""
        from src.graph import get_compiled_graph

        graph1 = get_compiled_graph()
        graph2 = get_compiled_graph()

        assert graph1 is graph2


class TestGraphExecution:
    """Tests for graph execution."""

    @pytest.mark.asyncio
    async def test_run_agent_simple(self):
        """Test running the agent with a simple query."""
        from src.graph import run_agent

        with patch("src.graph.get_compiled_graph") as mock_graph:
            mock_compiled = MagicMock()
            mock_compiled.ainvoke = AsyncMock(return_value={
                "messages": [],
                "query_type": "general",
                "raw_data": None,
                "data_dictionary": None,
                "analysis_result": "The answer is 42.",
                "validation_status": "approved",
                "revision_notes": None,
                "iteration_count": 1,
            })
            mock_graph.return_value = mock_compiled

            result = await run_agent("What is 6 times 7?")

            assert result["analysis_result"] == "The answer is 42."
            assert result["validation_status"] == "approved"

    @pytest.mark.asyncio
    async def test_stream_agent_events(self):
        """Test streaming agent events."""
        from src.graph import stream_agent

        async def mock_stream(state, **kwargs):
            yield {"router": {"query_type": "tableau"}}
            yield {"researcher": {"raw_data": {"search_results": {}}}}
            yield {"analyst": {"analysis_result": "Analysis complete"}}
            yield {"critic": {"validation_status": "approved"}}

        with patch("src.graph.get_compiled_graph") as mock_graph:
            mock_compiled = MagicMock()
            mock_compiled.astream = mock_stream
            mock_compiled.ainvoke = AsyncMock(return_value={
                "messages": [],
                "query_type": "tableau",
                "raw_data": {},
                "data_dictionary": None,
                "analysis_result": "Analysis complete",
                "validation_status": "approved",
                "revision_notes": None,
                "iteration_count": 1,
            })
            mock_graph.return_value = mock_compiled

            events = []
            async for event in stream_agent("Show me sales data"):
                events.append(event)

            assert len(events) > 0
            event_types = [e["event"] for e in events]
            assert "agent_start" in event_types
            assert "complete" in event_types
            assert "done" in event_types


class TestAPIIntegration:
    """Tests for API integration with the graph."""

    def test_health_endpoint(self, test_client):
        """Test the health check endpoint."""
        response = test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_config_endpoint(self, test_client):
        """Test the config endpoint."""
        response = test_client.get("/api/config")

        assert response.status_code == 200
        data = response.json()
        assert "max_revision_iterations" in data
        assert "max_csv_rows" in data

    @pytest.mark.asyncio
    async def test_chat_sync_endpoint(self, test_client):
        """Test the synchronous chat endpoint."""
        with patch("src.api.run_agent") as mock_run:
            mock_run.return_value = {
                "messages": [],
                "query_type": "general",
                "analysis_result": "Test response",
                "validation_status": "approved",
                "iteration_count": 1,
            }

            response = test_client.post(
                "/api/chat/sync",
                json={"message": "Hello, how are you?"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["response"] == "Test response"
