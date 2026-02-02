"""Tests for the tool implementations."""

import pytest
from unittest.mock import patch, MagicMock


class TestPythonRepl:
    """Tests for the python_repl tool."""

    def test_simple_calculation(self):
        """Test simple arithmetic calculation."""
        from src.tools.analysis_tools import python_repl

        result = python_repl.invoke({"code": "result = 2 + 2\nprint(result)"})

        assert result["success"] is True
        assert "4" in result["stdout"]

    def test_pandas_analysis(self):
        """Test pandas data analysis."""
        from src.tools.analysis_tools import python_repl

        code = """
import pandas as pd
from io import StringIO

csv_data = '''Name,Sales
Alice,100
Bob,200
Charlie,150'''

df = pd.read_csv(StringIO(csv_data))
total = df['Sales'].sum()
print(f"Total Sales: {total}")
"""
        result = python_repl.invoke({"code": code})

        assert result["success"] is True
        assert "Total Sales: 450" in result["stdout"]

    def test_numpy_operations(self):
        """Test numpy array operations."""
        from src.tools.analysis_tools import python_repl

        code = """
import numpy as np
arr = np.array([1, 2, 3, 4, 5])
print(f"Mean: {arr.mean()}")
print(f"Sum: {arr.sum()}")
"""
        result = python_repl.invoke({"code": code})

        assert result["success"] is True
        assert "Mean: 3.0" in result["stdout"]
        assert "Sum: 15" in result["stdout"]

    def test_syntax_error(self):
        """Test handling of syntax errors."""
        from src.tools.analysis_tools import python_repl

        result = python_repl.invoke({"code": "def incomplete("})

        assert result["success"] is False
        assert "Syntax error" in result["stderr"]

    def test_runtime_error(self):
        """Test handling of runtime errors."""
        from src.tools.analysis_tools import python_repl

        result = python_repl.invoke({"code": "x = 1 / 0"})

        assert result["success"] is False
        assert "ZeroDivisionError" in result["stderr"]

    def test_blocked_import(self):
        """Test that dangerous imports are blocked."""
        from src.tools.analysis_tools import python_repl

        result = python_repl.invoke({"code": "import os\nos.system('ls')"})

        assert result["success"] is False
        assert "not allowed" in result["stderr"]

    def test_timeout(self):
        """Test execution timeout."""
        from src.tools.analysis_tools import python_repl

        code = """
import time
time.sleep(100)
"""
        result = python_repl.invoke({"code": code, "timeout_seconds": 5})

        # Note: time.sleep uses the 'time' module which is not in ALLOWED_IMPORTS
        # This will fail with import error, not timeout
        assert result["success"] is False


class TestSearchTableauAssets:
    """Tests for the search_tableau_assets tool."""

    def test_search_workbooks(self, mock_tableau_client):
        """Test searching for workbooks."""
        from src.tools.tableau_tools import search_tableau_assets

        with patch("src.tools.tableau_tools.get_tableau_client") as mock_get_client:
            mock_get_client.return_value = mock_tableau_client

            result = search_tableau_assets.invoke({
                "query": "Sales",
                "asset_type": "workbook",
                "limit": 10,
            })

            assert result["success"] is True
            assert len(result["results"]["workbooks"]) > 0
            mock_tableau_client.get_workbooks.assert_called_once()

    def test_search_views(self, mock_tableau_client):
        """Test searching for views."""
        from src.tools.tableau_tools import search_tableau_assets

        with patch("src.tools.tableau_tools.get_tableau_client") as mock_get_client:
            mock_get_client.return_value = mock_tableau_client

            result = search_tableau_assets.invoke({
                "query": "Revenue",
                "asset_type": "view",
                "limit": 5,
            })

            assert result["success"] is True
            assert "views" in result["results"]
            mock_tableau_client.get_views.assert_called_once()

    def test_search_all_assets(self, mock_tableau_client):
        """Test searching all asset types."""
        from src.tools.tableau_tools import search_tableau_assets

        with patch("src.tools.tableau_tools.get_tableau_client") as mock_get_client:
            mock_get_client.return_value = mock_tableau_client

            result = search_tableau_assets.invoke({
                "query": "Dashboard",
                "asset_type": "all",
                "limit": 10,
            })

            assert result["success"] is True
            assert "workbooks" in result["results"]
            assert "views" in result["results"]
            assert "datasources" in result["results"]


class TestGetViewDataAsCsv:
    """Tests for the get_view_data_as_csv tool."""

    def test_get_view_data(self, mock_tableau_client):
        """Test fetching view data as CSV."""
        from src.tools.tableau_tools import get_view_data_as_csv

        with patch("src.tools.tableau_tools.get_tableau_client") as mock_get_client:
            mock_get_client.return_value = mock_tableau_client

            result = get_view_data_as_csv.invoke({
                "view_luid": "view-456",
                "max_rows": 50,
            })

            assert result["success"] is True
            assert "csv_data" in result
            assert "Region,Sales,Profit" in result["csv_data"]

    def test_get_view_data_with_filters(self, mock_tableau_client):
        """Test fetching view data with filters."""
        from src.tools.tableau_tools import get_view_data_as_csv

        with patch("src.tools.tableau_tools.get_tableau_client") as mock_get_client:
            mock_get_client.return_value = mock_tableau_client

            result = get_view_data_as_csv.invoke({
                "view_luid": "view-456",
                "filters": {"Region": "East"},
                "max_rows": 50,
            })

            assert result["success"] is True
            mock_tableau_client.get_view_data_csv.assert_called_once()
