# Tableau Analytics Agent

A production-grade Conversational Analytics Agent that enables natural language querying of Tableau dashboards via Vertex AI (Gemini 1.5 Pro) and the Tableau Server Client (TSC) library.

## Architecture

```
                         ┌─────────────────┐
                         │     ROUTER      │
                         │  (Classifies)   │
                         └────────┬────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
   ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
   │ RESEARCHER  │───────▶│  ANALYST    │───────▶│   CRITIC    │
   │ (Tableau)   │        │ (Analysis)  │        │ (Validate)  │
   └─────────────┘        └─────────────┘        └──────┬──────┘
                                                        │
                                          ┌─────────────┘
                                          │ (revision loop, max 3)
                                          ▼
                                   ┌─────────────┐
                                   │   COMPLETE  │
                                   └─────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, LangGraph, Vertex AI (Gemini 1.5 Pro), TSC |
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Zustand |
| Data Validation | Pydantic v2 |
| Streaming | SSE (Server-Sent Events) |

## Prerequisites

- Python 3.11+
- Node.js 20+
- Google Cloud project with Vertex AI enabled
- Tableau Server or Tableau Cloud with Personal Access Token

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/wiederMatan/Agentic-Tableau-Assistant.git
cd Agentic-Tableau-Assistant
```

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials
```

### 3. Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Copy and configure environment
cp .env.example .env.local
```

### 4. Configure credentials

Edit `backend/.env` with your settings:

```env
# Tableau Configuration
TABLEAU_SERVER_URL=https://your-tableau-server.com
TABLEAU_SITE_ID=your-site-id
TABLEAU_TOKEN_NAME=your-token-name
TABLEAU_TOKEN_VALUE=your-token-value

# Google Cloud Configuration
GCP_PROJECT_ID=your-gcp-project
GCP_LOCATION=us-central1
VERTEX_AI_MODEL=gemini-1.5-pro-002
```

### 5. Google Cloud Authentication

```bash
# Login and set up application default credentials
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

## Running the Application

### Development mode

**Backend:**
```bash
cd backend
source venv/bin/activate
python main.py
```

**Frontend:**
```bash
cd frontend
npm run dev
```

Access the app at http://localhost:3000

### Docker Compose

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d
```

## Testing

### Run backend tests

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

### Run with coverage

```bash
pytest tests/ -v --cov=src --cov-report=html
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | SSE streaming chat endpoint |
| `/api/chat/sync` | POST | Synchronous chat (non-streaming) |
| `/api/health` | GET | Health check |
| `/api/config` | GET | Public configuration |

### Example request

```bash
curl -X POST http://localhost:8000/api/chat/sync \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my top selling products?"}'
```

## Project Structure

```
tableau-analytics-agent/
├── backend/
│   ├── src/
│   │   ├── agents/         # Router, Researcher, Analyst, Critic
│   │   ├── tools/          # Tableau and analysis tools
│   │   ├── api.py          # FastAPI endpoints
│   │   ├── config.py       # Pydantic settings
│   │   ├── graph.py        # LangGraph workflow
│   │   ├── schemas.py      # Data models
│   │   └── tableau_client.py
│   ├── prompts/            # Agent system prompts
│   ├── tests/              # Pytest tests
│   ├── main.py             # Entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js pages
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom hooks (SSE)
│   │   ├── stores/         # Zustand stores
│   │   └── types/          # TypeScript types
│   └── package.json
├── docker-compose.yml
└── README.md
```

## Agent Workflow

1. **Router** - Classifies the query as `tableau`, `general`, or `hybrid`
2. **Researcher** - Searches Tableau assets and retrieves data (for tableau/hybrid queries)
3. **Analyst** - Analyzes data using Python REPL and generates insights
4. **Critic** - Validates the analysis for accuracy and completeness
5. **Revision Loop** - If validation fails, analyst revises (max 3 iterations)

## Available Tools

- `search_tableau_assets` - Search workbooks, views, and datasources
- `get_view_data_as_csv` - Extract tabular data from views
- `get_data_dictionary` - Get schema metadata for workbooks
- `python_repl` - Sandboxed Python execution for analysis

## Security Considerations

- Python REPL uses a sandboxed environment with restricted imports
- Only safe modules are allowed (pandas, numpy, statistics, math, etc.)
- Tableau credentials are managed via environment variables
- CORS is configured for allowed origins only

## License

MIT License
