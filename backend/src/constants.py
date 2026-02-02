"""Shared constants for the analytics agent backend."""

# Logging configuration
LOG_MESSAGE_TRUNCATE_LENGTH = 100
"""Maximum length for log message previews (user queries, etc.)."""

# Tool execution limits
TOOL_MAX_ITERATIONS = 5
"""Maximum iterations for agent tool loops (researcher, analyst)."""

# Data preview limits
DATA_PREVIEW_ROWS = 10
"""Number of rows to include in DataFrame/Series previews."""

RESULT_SERIALIZATION_LIMIT = 100
"""Maximum items to include when serializing lists/dicts in results."""

CSV_PREVIEW_CHARS = 2000
"""Maximum characters for CSV data previews in validation context."""

# Serialization limits for numpy arrays
NUMPY_PREVIEW_ELEMENTS = 10
"""Maximum elements to include in numpy array previews."""
