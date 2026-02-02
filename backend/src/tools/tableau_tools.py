"""Tableau-specific tools for the analytics agent."""

import logging
from typing import Any, Literal

from langchain_core.tools import tool

from ..schemas import (
    DataDictionary,
    DataDictionaryField,
    GetDataDictionaryInput,
    GetViewDataInput,
    SearchAssetsInput,
    TableauDatasource,
    TableauView,
    TableauWorkbook,
)
from ..tableau_client import TableauConnectionError, get_tableau_client

logger = logging.getLogger(__name__)


@tool(args_schema=SearchAssetsInput)
def search_tableau_assets(
    query: str,
    asset_type: Literal["workbook", "view", "datasource", "all"] = "all",
    limit: int = 10,
) -> dict[str, Any]:
    """Search for Tableau assets (workbooks, views, datasources) by name.

    Use this tool to find relevant Tableau content based on a search query.
    Returns metadata about matching assets that can be used with other tools.

    Args:
        query: Search query string to match against asset names.
        asset_type: Type of asset to search for. Use "all" to search everything.
        limit: Maximum number of results to return (default: 10).

    Returns:
        Dictionary containing lists of matching workbooks, views, and/or datasources.
    """
    client = get_tableau_client()
    results: dict[str, list[dict]] = {
        "workbooks": [],
        "views": [],
        "datasources": [],
    }

    try:
        # Search workbooks
        if asset_type in ("workbook", "all"):
            workbooks = client.get_workbooks(filter_expression=query, limit=limit)
            results["workbooks"] = [
                TableauWorkbook(
                    luid=wb.id,
                    name=wb.name,
                    project_name=wb.project_name,
                    owner_name=wb.owner_id,
                    content_url=wb.content_url,
                    created_at=wb.created_at,
                    updated_at=wb.updated_at,
                ).model_dump()
                for wb in workbooks
            ]

        # Search views
        if asset_type in ("view", "all"):
            views = client.get_views(filter_expression=query, limit=limit)
            results["views"] = [
                TableauView(
                    luid=v.id,
                    name=v.name,
                    workbook_id=v.workbook_id,
                    content_url=v.content_url,
                    owner_name=v.owner_id,
                ).model_dump()
                for v in views
            ]

        # Search datasources
        if asset_type in ("datasource", "all"):
            datasources = client.get_datasources(filter_expression=query, limit=limit)
            results["datasources"] = [
                TableauDatasource(
                    luid=ds.id,
                    name=ds.name,
                    project_name=ds.project_name,
                    datasource_type=ds.datasource_type,
                    has_extracts=ds.has_extracts or False,
                    content_url=ds.content_url,
                ).model_dump()
                for ds in datasources
            ]

        total_results = sum(len(v) for v in results.values())
        logger.info(f"Search for '{query}' returned {total_results} results")

        return {
            "success": True,
            "query": query,
            "asset_type": asset_type,
            "results": results,
            "total_count": total_results,
        }

    except TableauConnectionError as e:
        logger.error(f"Tableau connection error during search: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "results": results,
        }
    except (AttributeError, TypeError, ValueError) as e:
        # Handle attribute/type errors from TSC object processing
        logger.error(f"Error processing Tableau search results: {e}")
        return {
            "success": False,
            "error": f"Search result processing failed: {str(e)}",
            "query": query,
            "results": results,
        }


@tool(args_schema=GetViewDataInput)
def get_view_data_as_csv(
    view_luid: str,
    filters: dict[str, str] | None = None,
    max_rows: int = 50,
) -> dict[str, Any]:
    """Get tabular data from a Tableau view as CSV.

    Use this tool to extract the underlying data from a Tableau view/sheet.
    The data can then be analyzed using the python_repl tool.

    Args:
        view_luid: The LUID (Locally Unique Identifier) of the view.
        filters: Optional dictionary of filters to apply (field_name: value).
        max_rows: Maximum number of data rows to return (default: 50).

    Returns:
        Dictionary containing CSV data and metadata.
    """
    client = get_tableau_client()
    filters = filters or {}

    try:
        csv_data = client.get_view_data_csv(
            view_id=view_luid,
            filters=filters,
            max_rows=max_rows,
        )

        # Count actual rows (excluding header)
        row_count = len(csv_data.strip().split("\n")) - 1 if csv_data else 0

        logger.info(f"Retrieved {row_count} rows from view {view_luid}")

        return {
            "success": True,
            "view_luid": view_luid,
            "filters_applied": filters,
            "csv_data": csv_data,
            "row_count": row_count,
            "truncated": row_count >= max_rows,
        }

    except TableauConnectionError as e:
        logger.error(f"Tableau connection error fetching view data: {e}")
        return {
            "success": False,
            "error": str(e),
            "view_luid": view_luid,
            "csv_data": "",
        }
    except (AttributeError, TypeError, ValueError) as e:
        # Handle attribute/type errors from CSV processing
        logger.error(f"Error processing view data: {e}")
        return {
            "success": False,
            "error": f"View data processing failed: {str(e)}",
            "view_luid": view_luid,
            "csv_data": "",
        }


@tool(args_schema=GetDataDictionaryInput)
def get_data_dictionary(workbook_luid: str) -> dict[str, Any]:
    """Get the data dictionary (schema metadata) for a Tableau workbook.

    Use this tool to understand the fields, data types, and structure
    of the data in a workbook before performing analysis.

    Args:
        workbook_luid: The LUID of the workbook to get metadata for.

    Returns:
        Dictionary containing field definitions and metadata.
    """
    client = get_tableau_client()

    try:
        workbook = client.get_workbook_by_id(workbook_luid)

        # Extract connection/field information
        fields: list[DataDictionaryField] = []

        # Get fields from connections if available
        if hasattr(workbook, "connections") and workbook.connections:
            for conn in workbook.connections:
                # Connection metadata varies by type
                connection_info = {
                    "connection_type": conn.connection_type,
                    "server_address": getattr(conn, "server_address", None),
                    "server_port": getattr(conn, "server_port", None),
                    "username": getattr(conn, "username", None),
                }
                logger.debug(f"Workbook connection: {connection_info}")

        data_dict = DataDictionary(
            source_name=workbook.name,
            source_luid=workbook.id,
            fields=fields,
        )

        logger.info(f"Retrieved data dictionary for workbook {workbook.name}")

        return {
            "success": True,
            "workbook_luid": workbook_luid,
            "workbook_name": workbook.name,
            "project_name": workbook.project_name,
            "data_dictionary": data_dict.model_dump(),
            "views": [
                {"id": v.id, "name": v.name}
                for v in (workbook.views or [])
            ],
        }

    except TableauConnectionError as e:
        logger.error(f"Tableau connection error fetching data dictionary: {e}")
        return {
            "success": False,
            "error": str(e),
            "workbook_luid": workbook_luid,
        }
    except (AttributeError, TypeError, ValueError) as e:
        # Handle attribute/type errors from workbook metadata processing
        logger.error(f"Error processing workbook metadata: {e}")
        return {
            "success": False,
            "error": f"Workbook metadata processing failed: {str(e)}",
            "workbook_luid": workbook_luid,
        }
