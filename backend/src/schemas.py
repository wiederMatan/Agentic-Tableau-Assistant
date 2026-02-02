"""Pydantic models and LangGraph state definitions."""

from datetime import datetime
from typing import Annotated, Any, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# === API Request/Response Models ===


class ChatRequest(BaseModel):
    """Chat request from the frontend."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User's natural language query",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Optional conversation ID for context continuity",
    )


class SSEEvent(BaseModel):
    """Server-Sent Event structure."""

    event: Literal[
        "agent_start",
        "tool_call",
        "tool_result",
        "validation",
        "token",
        "complete",
        "error",
        "heartbeat",
        "done",
    ]
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# === Tableau Asset Models ===


class TableauAsset(BaseModel):
    """Base model for Tableau assets."""

    luid: str = Field(..., description="Locally Unique Identifier")
    name: str = Field(..., description="Asset name")
    project_name: str | None = Field(default=None, description="Parent project name")
    owner_name: str | None = Field(default=None, description="Asset owner")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TableauWorkbook(TableauAsset):
    """Tableau workbook metadata."""

    content_url: str | None = None
    show_tabs: bool = False
    views: list[str] = Field(default_factory=list)


class TableauView(TableauAsset):
    """Tableau view (sheet) metadata."""

    workbook_id: str
    workbook_name: str | None = None
    content_url: str | None = None


class TableauDatasource(TableauAsset):
    """Tableau datasource metadata."""

    datasource_type: str | None = None
    has_extracts: bool = False
    content_url: str | None = None


class DataDictionaryField(BaseModel):
    """Single field in a data dictionary."""

    name: str
    data_type: str | None = None
    description: str | None = None
    is_calculated: bool = False
    role: Literal["dimension", "measure"] | None = None


class DataDictionary(BaseModel):
    """Data dictionary for a workbook/datasource."""

    source_name: str
    source_luid: str
    fields: list[DataDictionaryField] = Field(default_factory=list)


# === Tool Input/Output Models ===


class SearchAssetsInput(BaseModel):
    """Input for search_tableau_assets tool."""

    query: str = Field(..., description="Search query string")
    asset_type: Literal["workbook", "view", "datasource", "all"] = Field(
        default="all",
        description="Type of asset to search for",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results",
    )


class GetViewDataInput(BaseModel):
    """Input for get_view_data_as_csv tool."""

    view_luid: str = Field(..., description="View LUID to fetch data from")
    filters: dict[str, str] = Field(
        default_factory=dict,
        description="Optional filters to apply (field_name: value)",
    )
    max_rows: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum rows to return",
    )


class GetDataDictionaryInput(BaseModel):
    """Input for get_data_dictionary tool."""

    workbook_luid: str = Field(..., description="Workbook LUID")


class PythonReplInput(BaseModel):
    """Input for python_repl tool."""

    code: str = Field(..., description="Python code to execute")
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Execution timeout",
    )


class PythonReplOutput(BaseModel):
    """Output from python_repl tool."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    result: Any = None
    execution_time_ms: float = 0


# === Agent State ===


class AgentState(TypedDict):
    """State shared across the multi-agent graph."""

    # Message history with automatic merging
    messages: Annotated[list[BaseMessage], add_messages]

    # Query classification
    query_type: Literal["tableau", "general", "hybrid"] | None

    # Data from Tableau
    raw_data: dict[str, Any] | None
    data_dictionary: dict[str, Any] | None

    # Analysis results
    analysis_result: str | None

    # Validation state
    validation_status: Literal["pending", "approved", "revision_needed"]
    revision_notes: str | None
    iteration_count: int


def create_initial_state() -> AgentState:
    """Create initial agent state with defaults."""
    return AgentState(
        messages=[],
        query_type=None,
        raw_data=None,
        data_dictionary=None,
        analysis_result=None,
        validation_status="pending",
        revision_notes=None,
        iteration_count=0,
    )


# === Validation Models ===


class ValidationResult(BaseModel):
    """Result from the Critic agent."""

    status: Literal["approved", "revision_needed"]
    confidence_score: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    reasoning: str = ""
