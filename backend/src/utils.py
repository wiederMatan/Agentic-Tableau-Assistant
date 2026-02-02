"""Shared utilities for the analytics agent backend."""


def extract_json_from_markdown(response: str) -> str:
    """Extract JSON from markdown code blocks.

    Handles responses that may be wrapped in ```json or ``` code blocks,
    returning the inner content suitable for JSON parsing.

    Args:
        response: Raw response string that may contain markdown code blocks.

    Returns:
        Extracted JSON string with code block markers removed.
    """
    response = response.strip()

    # Handle ```json code blocks
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        if end != -1:
            return response[start:end].strip()

    # Handle plain ``` code blocks
    if "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        if end != -1:
            return response[start:end].strip()

    return response
