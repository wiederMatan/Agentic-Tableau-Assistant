# SEC-001: Missing API Authentication

## Severity: CRITICAL
## CVSS Score: 9.1
## CWE: CWE-306 (Missing Authentication for Critical Function)

---

## Location

| File | Line | Function |
|------|------|----------|
| `backend/src/api.py` | 115-130 | `chat()` |
| `backend/src/api.py` | 133-159 | `chat_sync()` |

---

## Description

All API endpoints are publicly accessible without any form of authentication. This allows any network-accessible client to:
- Query Tableau data through the agent
- Execute analysis operations
- Consume Vertex AI credits
- Access business-sensitive data

---

## Vulnerable Code

```python
@app.post("/api/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    """Stream chat response using Server-Sent Events."""
    # NO AUTHENTICATION CHECK
    logger.info(f"Received chat request: {request.message[:100]}...")
    return EventSourceResponse(
        event_generator(request.message, request.conversation_id),
        media_type="text/event-stream",
    )
```

---

## Proof of Concept

```bash
# Any unauthenticated user can access Tableau data
curl -X POST http://localhost:8000/api/chat/sync \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me all customer PII data"}'

# Response includes business-sensitive data without authentication
```

---

## Impact

1. **Data Exfiltration**: Attackers can query and extract any data accessible via the Tableau PAT
2. **Cost Abuse**: Unlimited Vertex AI API calls at victim's expense
3. **Business Intelligence Leak**: Competitive intelligence exposed
4. **Compliance Violation**: GDPR, SOC2, HIPAA violations if PII exposed

---

## Remediation

### Option 1: API Key Authentication (Minimum)

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    api_key: str = Security(verify_api_key)
) -> EventSourceResponse:
    # Authenticated request
    ...
```

### Option 2: JWT/OAuth2 (Recommended for Production)

```python
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

---

## Effort: MEDIUM
## Priority: IMMEDIATE (24 hours)

---

## References

- https://owasp.org/www-project-api-security/
- https://cwe.mitre.org/data/definitions/306.html
- https://fastapi.tiangolo.com/tutorial/security/
