# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Conversational Analytics Agent that enables natural language querying of Tableau dashboards using Vertex AI (Gemini 1.5 Pro) and the Tableau Server Client library.

## Commands

### Backend (Python)

```bash
# Start development server (from backend/)
cd backend && source venv/bin/activate && python main.py

# Run all tests
cd backend && pytest tests/ -v

# Run single test file
cd backend && pytest tests/test_graph.py -v

# Run single test
cd backend && pytest tests/test_graph.py::TestGraphConstruction::test_create_graph -v

# Run tests with coverage
cd backend && pytest tests/ -v --cov=src --cov-report=html

# Install dependencies
cd backend && pip install -r requirements.txt
```

### Frontend (Next.js)

```bash
# Start development server (from frontend/)
cd frontend && npm run dev

# Build for production
cd frontend && npm run build

# Run linter
cd frontend && npm run lint

# Type check
cd frontend && npm run type-check
```

### Docker

```bash
# Build and run all services
docker-compose up --build

# Run in background
docker-compose up -d
```

## Architecture

### Multi-Agent System (LangGraph)

The backend uses LangGraph to orchestrate four specialized agents in a state machine:

```
START → Router → [Researcher | Analyst] → Analyst → Critic → [Revision Loop | END]
```

**Agents** (`backend/src/agents/`):
- **Router** (`router.py`): Classifies queries as `tableau`, `general`, or `hybrid`
- **Researcher** (`researcher.py`): Retrieves data from Tableau Server (only for tableau/hybrid queries)
- **Analyst** (`analyst.py`): Analyzes data using sandboxed Python REPL, generates insights
- **Critic** (`critic.py`): Validates analysis quality; triggers revision loop if needed (max 3 iterations)

**Graph Definition** (`backend/src/graph.py`):
- `create_graph()`: Builds the StateGraph with nodes and conditional edges
- `get_compiled_graph()`: Returns singleton compiled graph
- `stream_agent()`: Async generator yielding SSE events during execution
- `run_agent()`: Synchronous execution returning final state

**State** (`backend/src/schemas.py`):
- `AgentState`: TypedDict with message history, query_type, raw_data, analysis_result, validation_status
- Uses `Annotated[list[BaseMessage], add_messages]` for automatic message merging

### Backend API

FastAPI server (`backend/src/api.py`) with SSE streaming:
- `POST /api/chat`: SSE streaming endpoint (real-time events)
- `POST /api/chat/sync`: Synchronous endpoint
- `GET /api/health`: Health check
- `GET /api/config`: Public configuration

Configuration via Pydantic Settings (`backend/src/config.py`) loaded from `.env`.

### Frontend

Next.js 14 with App Router:
- **State**: Zustand store (`frontend/src/stores/chatStore.ts`)
- **SSE Hook**: `frontend/src/hooks/useSSE.ts` handles streaming events
- **Types**: Comprehensive TypeScript definitions in `frontend/src/types/index.ts`
- **Components**: Chat UI in `frontend/src/components/chat/`

### Tools

Located in `backend/src/tools/`:
- **tableau_tools.py**: `search_tableau_assets`, `get_view_data_as_csv`, `get_data_dictionary`
- **analysis_tools.py**: `python_repl` - sandboxed execution with restricted imports (pandas, numpy, statistics, math)

### Testing

Tests use pytest with async support. Key fixtures in `backend/tests/conftest.py`:
- `mock_tableau_client`: Mocked TSC client
- `mock_vertex_ai`: Mocked LLM responses
- `test_client`: FastAPI TestClient
- `sample_agent_state`: Pre-populated AgentState

Environment variables are set in conftest.py for test isolation.
