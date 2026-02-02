# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `backend/src/constants.py` - Centralized constants for magic numbers
- `backend/src/utils.py` - Shared utility functions (JSON extraction from markdown)
- Type guards for SSE event validation in frontend
- JSDoc documentation for frontend hooks and stores
- Comprehensive environment variable reference in README
- SSE event documentation in README
- Troubleshooting guide in README

### Changed
- Fixed critical performance bug: removed double graph invocation in `stream_agent()`
- Replaced global singleton pattern with `@lru_cache` for compiled graph
- Added explicit type hints to `compile_graph()` and `get_compiled_graph()`
- Moved `import time` to module level in `analysis_tools.py`
- Refactored `python_repl()` into smaller helper functions (`_setup_timeout`, `_execute_code`, `_clear_timeout`)
- Replaced magic numbers with named constants across backend
- Updated router and critic agents to use shared `extract_json_from_markdown()` utility
- Narrowed exception handling in Tableau tools from `Exception` to specific types
- Improved error logging with `exc_info=True` at API boundaries

### Fixed
- Double execution of agent graph when streaming (was calling both `astream()` and `ainvoke()`)
- Overly broad exception handling masking specific errors

## [0.1.0] - 2024-01-15

### Added
- Initial release
- Multi-agent system with Router, Researcher, Analyst, and Critic agents
- LangGraph-based workflow orchestration
- FastAPI backend with SSE streaming
- Next.js frontend with real-time workflow visualization
- Tableau Server Client integration for data retrieval
- Vertex AI (Gemini 1.5 Pro) integration
- Sandboxed Python REPL for data analysis
- Zustand state management for frontend
- Docker Compose configuration
- Comprehensive test suite
- Agent system prompts
