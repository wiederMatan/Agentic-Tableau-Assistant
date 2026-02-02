"""Tableau Server Client connection manager."""

import logging
from contextlib import contextmanager
from typing import Generator

import tableauserverclient as TSC

from .config import Settings, get_settings

logger = logging.getLogger(__name__)


class TableauConnectionError(Exception):
    """Raised when Tableau connection fails."""

    pass


class TableauClientManager:
    """Manages Tableau Server Client connections."""

    def __init__(self, settings: Settings | None = None):
        """Initialize the client manager.

        Args:
            settings: Application settings. If None, loads from environment.
        """
        self._settings = settings or get_settings()
        self._server: TSC.Server | None = None
        self._auth: TSC.PersonalAccessTokenAuth | None = None

    @property
    def server_url(self) -> str:
        """Get the Tableau server URL."""
        return self._settings.tableau_server_url

    @property
    def site_id(self) -> str:
        """Get the Tableau site ID."""
        return self._settings.tableau_site_id

    def _create_auth(self) -> TSC.PersonalAccessTokenAuth:
        """Create authentication object."""
        return TSC.PersonalAccessTokenAuth(
            token_name=self._settings.tableau_token_name,
            personal_access_token=self._settings.tableau_token_value.get_secret_value(),
            site_id=self._settings.tableau_site_id,
        )

    def _create_server(self) -> TSC.Server:
        """Create server object with configuration."""
        server = TSC.Server(self._settings.tableau_server_url, use_server_version=True)
        # Set request options for better performance
        server.add_http_options({"verify": True})
        return server

    @contextmanager
    def connect(self) -> Generator[TSC.Server, None, None]:
        """Context manager for Tableau server connection.

        Yields:
            Connected TSC.Server instance.

        Raises:
            TableauConnectionError: If connection fails.
        """
        server = self._create_server()
        auth = self._create_auth()

        try:
            logger.info(f"Connecting to Tableau Server: {self.server_url}")
            server.auth.sign_in(auth)
            logger.info(
                f"Successfully authenticated to site: {self.site_id or 'default'}"
            )
            yield server
        except TSC.ServerResponseError as e:
            logger.error(f"Tableau authentication failed: {e}")
            raise TableauConnectionError(f"Authentication failed: {e}") from e
        except Exception as e:
            logger.error(f"Tableau connection error: {e}")
            raise TableauConnectionError(f"Connection failed: {e}") from e
        finally:
            try:
                server.auth.sign_out()
                logger.debug("Signed out from Tableau Server")
            except Exception as e:
                logger.warning(f"Error during sign out: {e}")

    def test_connection(self) -> bool:
        """Test the Tableau connection.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            with self.connect() as server:
                # Try to get server info as a connection test
                server_info = server.server_info.get()
                logger.info(
                    f"Connected to Tableau Server v{server_info.product_version}"
                )
                return True
        except TableauConnectionError:
            return False

    def get_workbooks(
        self,
        filter_expression: str | None = None,
        limit: int = 100,
    ) -> list[TSC.WorkbookItem]:
        """Get workbooks with optional filtering.

        Args:
            filter_expression: Optional filter expression.
            limit: Maximum number of results.

        Returns:
            List of workbook items.
        """
        with self.connect() as server:
            req_options = TSC.RequestOptions(pagesize=min(limit, 100))
            if filter_expression:
                req_options.filter.add(
                    TSC.Filter(
                        TSC.RequestOptions.Field.Name,
                        TSC.RequestOptions.Operator.Contains,
                        filter_expression,
                    )
                )
            workbooks, _ = server.workbooks.get(req_options)
            return list(workbooks)[:limit]

    def get_views(
        self,
        filter_expression: str | None = None,
        limit: int = 100,
    ) -> list[TSC.ViewItem]:
        """Get views with optional filtering.

        Args:
            filter_expression: Optional filter expression.
            limit: Maximum number of results.

        Returns:
            List of view items.
        """
        with self.connect() as server:
            req_options = TSC.RequestOptions(pagesize=min(limit, 100))
            if filter_expression:
                req_options.filter.add(
                    TSC.Filter(
                        TSC.RequestOptions.Field.Name,
                        TSC.RequestOptions.Operator.Contains,
                        filter_expression,
                    )
                )
            views, _ = server.views.get(req_options)
            return list(views)[:limit]

    def get_datasources(
        self,
        filter_expression: str | None = None,
        limit: int = 100,
    ) -> list[TSC.DatasourceItem]:
        """Get datasources with optional filtering.

        Args:
            filter_expression: Optional filter expression.
            limit: Maximum number of results.

        Returns:
            List of datasource items.
        """
        with self.connect() as server:
            req_options = TSC.RequestOptions(pagesize=min(limit, 100))
            if filter_expression:
                req_options.filter.add(
                    TSC.Filter(
                        TSC.RequestOptions.Field.Name,
                        TSC.RequestOptions.Operator.Contains,
                        filter_expression,
                    )
                )
            datasources, _ = server.datasources.get(req_options)
            return list(datasources)[:limit]

    def get_view_data_csv(
        self,
        view_id: str,
        filters: dict[str, str] | None = None,
        max_rows: int = 50,
    ) -> str:
        """Get view data as CSV.

        Args:
            view_id: View LUID.
            filters: Optional view filters.
            max_rows: Maximum rows to return.

        Returns:
            CSV string of view data.
        """
        with self.connect() as server:
            # Apply view filters if provided
            view_filter_options = None
            if filters:
                view_filter_options = TSC.CSVRequestOptions(maxage=1)
                for field, value in filters.items():
                    view_filter_options.vf(field, value)

            # Populate CSV data
            server.views.populate_csv(
                server.views.get_by_id(view_id),
                view_filter_options,
            )
            view = server.views.get_by_id(view_id)
            server.views.populate_csv(view, view_filter_options)

            # Read and limit rows
            csv_data = view.csv
            if csv_data:
                lines = csv_data.decode("utf-8").split("\n")
                # Keep header + limited data rows
                limited_lines = lines[: max_rows + 1]
                return "\n".join(limited_lines)
            return ""

    def get_workbook_by_id(self, workbook_id: str) -> TSC.WorkbookItem:
        """Get a workbook by ID with connections populated.

        Args:
            workbook_id: Workbook LUID.

        Returns:
            Workbook item with connections.
        """
        with self.connect() as server:
            workbook = server.workbooks.get_by_id(workbook_id)
            server.workbooks.populate_connections(workbook)
            return workbook


# Module-level singleton for convenience
_client_manager: TableauClientManager | None = None


def get_tableau_client() -> TableauClientManager:
    """Get or create the Tableau client manager singleton."""
    global _client_manager
    if _client_manager is None:
        _client_manager = TableauClientManager()
    return _client_manager
