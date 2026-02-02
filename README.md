# Tableau Analytics Agent

Chat with your Tableau dashboards using natural language. Ask questions, get insights.

**Stack:** Python + FastAPI + LangGraph + Gemini 1.5 Pro | Next.js + TypeScript

---

## Quick Start

### 1. Clone & Setup Backend

```bash
git clone https://github.com/wiederMatan/Agentic-Tableau-Assistant.git
cd Agentic-Tableau-Assistant/backend

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Then edit with your credentials
```

### 2. Setup Frontend

```bash
cd ../frontend
npm install
cp .env.example .env.local
```

### 3. Configure `.env`

```env
TABLEAU_SERVER_URL=https://your-server.com
TABLEAU_TOKEN_NAME=your-token-name
TABLEAU_TOKEN_VALUE=your-token-value
GCP_PROJECT_ID=your-gcp-project
```

### 4. Run

```bash
# Terminal 1 - Backend
cd backend && source venv/bin/activate && python main.py

# Terminal 2 - Frontend
cd frontend && npm run dev
```

Open http://localhost:3000

---

## How It Works

```
You ask a question
        ↓
   [ Router ] → Classifies your query
        ↓
 [ Researcher ] → Fetches Tableau data
        ↓
  [ Analyst ] → Analyzes with Python
        ↓
   [ Critic ] → Validates quality
        ↓
    Answer!
```

---

## API

| Endpoint | What it does |
|----------|--------------|
| `POST /api/chat` | Stream responses (SSE) |
| `POST /api/chat/sync` | Get full response |
| `GET /api/health` | Health check |
| `GET /api/config` | Public configuration |

**Try it:**
```bash
curl -X POST http://localhost:8000/api/chat/sync \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my top selling products?"}'
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TABLEAU_SERVER_URL` | Yes | Tableau Server/Cloud URL |
| `TABLEAU_SITE_ID` | Yes | Site ID (empty for default) |
| `TABLEAU_TOKEN_NAME` | Yes | PAT name |
| `TABLEAU_TOKEN_VALUE` | Yes | PAT value |
| `GCP_PROJECT_ID` | Yes | Google Cloud project |
| `GCP_LOCATION` | No | Region (default: `us-central1`) |
| `VERTEX_AI_MODEL` | No | Model (default: `gemini-1.5-pro-002`) |
| `MAX_REVISION_ITERATIONS` | No | Critic loops (default: `3`) |
| `PYTHON_REPL_TIMEOUT` | No | REPL timeout secs (default: `30`) |

---

## SSE Events

| Event | Description |
|-------|-------------|
| `agent_start` | Agent started |
| `tool_result` | Tool completed |
| `validation` | Critic validation |
| `token` | Streamed content |
| `complete` | Final response |
| `error` | Error occurred |
| `done` | Stream ended |

---

## Project Structure

```
├── backend/
│   ├── src/
│   │   ├── agents/       # Router, Researcher, Analyst, Critic
│   │   ├── tools/        # Tableau & Python REPL tools
│   │   ├── api.py        # FastAPI endpoints
│   │   ├── graph.py      # LangGraph workflow
│   │   └── constants.py  # Shared constants
│   ├── prompts/          # Agent system prompts
│   └── tests/            # Pytest tests
├── frontend/
│   ├── src/
│   │   ├── hooks/        # SSE streaming hook
│   │   ├── stores/       # Zustand state
│   │   └── components/   # React UI
│   └── package.json
└── docker-compose.yml
```

---

## Docker

```bash
docker-compose up --build
```

---

## Tests

```bash
# Backend
cd backend && pytest tests/ -v

# Frontend
cd frontend && npm run lint && npm run type-check
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Tableau connection failed | Check PAT credentials and server URL |
| Vertex AI auth error | Run `gcloud auth application-default login` |
| CORS errors | Add frontend URL to `CORS_ORIGINS` |
| Python REPL timeout | Increase `PYTHON_REPL_TIMEOUT` |

---

## License

MIT
