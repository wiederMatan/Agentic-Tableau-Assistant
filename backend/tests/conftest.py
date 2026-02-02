"""Pytest fixtures for the Tableau Analytics Agent tests."""

import os
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing app modules
os.environ.setdefault("TABLEAU_SERVER_URL", "https://test.tableau.com")
os.environ.setdefault("TABLEAU_SITE_ID", "test-site")
os.environ.setdefault("TABLEAU_TOKEN_NAME", "test-token")
os.environ.setdefault("TABLEAU_TOKEN_VALUE", "test-secret")
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("GCP_LOCATION", "us-central1")
os.environ.setdefault("ENVIRONMENT", "development")


@pytest.fixture(scope="session")
def mock_settings():
    """Create mock settings for testing."""
    from src.config import Settings

    return Settings(
        tableau_server_url="https://test.tableau.com",
        tableau_site_id="test-site",
        tableau_token_name="test-token",
        tableau_token_value="test-secret",
        gcp_project_id="test-project",
        gcp_location="us-central1",
        environment="development",
    )


@pytest.fixture
def mock_tableau_client():
    """Create a mock Tableau client."""
    with patch("src.tableau_client.TableauClientManager") as mock:
        client = MagicMock()
        mock.return_value = client

        # Mock workbook data
        mock_workbook = MagicMock()
        mock_workbook.id = "wb-123"
        mock_workbook.name = "Sales Dashboard"
        mock_workbook.project_name = "Marketing"
        mock_workbook.content_url = "sales-dashboard"
        mock_workbook.created_at = None
        mock_workbook.updated_at = None
        mock_workbook.owner_id = "user-1"

        # Mock view data
        mock_view = MagicMock()
        mock_view.id = "view-456"
        mock_view.name = "Revenue by Region"
        mock_view.workbook_id = "wb-123"
        mock_view.content_url = "revenue-by-region"
        mock_view.owner_id = "user-1"

        # Configure client methods
        client.get_workbooks.return_value = [mock_workbook]
        client.get_views.return_value = [mock_view]
        client.get_datasources.return_value = []
        client.get_view_data_csv.return_value = (
            "Region,Sales,Profit\nEast,100000,20000\nWest,150000,30000"
        )

        yield client


@pytest.fixture
def mock_vertex_ai():
    """Create a mock Vertex AI client."""
    with patch("langchain_google_vertexai.ChatVertexAI") as mock:
        llm = MagicMock()
        mock.return_value = llm

        # Mock response
        mock_response = MagicMock()
        mock_response.content = '{"query_type": "tableau", "reasoning": "User asking about sales data", "key_entities": ["sales", "region"]}'
        mock_response.tool_calls = []

        llm.ainvoke.return_value = mock_response
        llm.bind_tools.return_value = llm

        yield llm


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    from src.api import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_csv_data() -> str:
    """Sample CSV data for testing."""
    return """Product,Region,Sales,Profit,Date
Widget A,East,10000,2000,2024-01-01
Widget B,West,15000,3000,2024-01-02
Widget C,East,8000,1600,2024-01-03
Widget D,West,12000,2400,2024-01-04
Widget E,North,9000,1800,2024-01-05"""


@pytest.fixture
def sample_agent_state():
    """Sample agent state for testing."""
    from langchain_core.messages import HumanMessage

    from src.schemas import create_initial_state

    state = create_initial_state()
    state["messages"] = [HumanMessage(content="What are my total sales by region?")]
    return state
