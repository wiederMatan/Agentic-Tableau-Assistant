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

**Try it:**
```bash
curl -X POST http://localhost:8000/api/chat/sync \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my top selling products?"}'
```

---

## Docker

```bash
docker-compose up --build
```

---

## Tests

```bash
cd backend && pytest tests/ -v
```

---

## License

MIT
