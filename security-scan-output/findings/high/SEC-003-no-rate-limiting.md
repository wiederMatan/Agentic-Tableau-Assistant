# SEC-003: Missing Rate Limiting

## Severity: HIGH
## CVSS Score: 7.5
## CWE: CWE-770 (Allocation of Resources Without Limits)

---

## Location

| File | Line | Function |
|------|------|----------|
| `backend/src/api.py` | 115-130 | `chat()` |
| `backend/src/api.py` | 133-159 | `chat_sync()` |

---

## Description

No rate limiting is implemented on any API endpoint. This allows:
- Denial of Service attacks via request flooding
- Brute force attacks (if auth is added later)
- Unbounded Vertex AI cost accumulation
- Tableau API rate limit exhaustion

---

## Vulnerable Code

```python
@app.post("/api/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    # No rate limiting check
    # Each request consumes Vertex AI credits
    # Each request queries Tableau
    return EventSourceResponse(...)
```

---

## Proof of Concept

```bash
# Flood the API to cause DoS and cost accumulation
for i in {1..10000}; do
  curl -X POST http://localhost:8000/api/chat/sync \
    -H "Content-Type: application/json" \
    -d '{"message": "Analyze all sales data in detail"}' &
done
```

---

## Impact

1. **Denial of Service**: Server overwhelmed by requests
2. **Financial Impact**: Unbounded Vertex AI API costs
3. **Tableau Rate Limits**: Exhaust Tableau API quotas
4. **Resource Exhaustion**: Memory/CPU exhaustion from concurrent requests

---

## Remediation

### Option 1: SlowAPI Rate Limiter (FastAPI)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded", "retry_after": exc.detail}
    )

@app.post("/api/chat")
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def chat(request: Request, chat_request: ChatRequest):
    ...
```

### Option 2: Redis-based Rate Limiting

```python
import redis
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379)

async def check_rate_limit(client_ip: str, limit: int = 10, window: int = 60):
    key = f"rate_limit:{client_ip}"
    current = redis_client.incr(key)
    if current == 1:
        redis_client.expire(key, window)
    if current > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

### Recommended Limits

| Endpoint | Limit | Window | Rationale |
|----------|-------|--------|-----------|
| `/api/chat` | 10 | 1 minute | Expensive LLM calls |
| `/api/chat/sync` | 10 | 1 minute | Expensive LLM calls |
| `/api/health` | 60 | 1 minute | Monitoring traffic |
| `/api/config` | 30 | 1 minute | Low cost |

---

## Effort: LOW
## Priority: URGENT (72 hours)

---

## References

- https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/
- https://slowapi.readthedocs.io/
- https://cwe.mitre.org/data/definitions/770.html
