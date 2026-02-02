# Secure Code Guidelines

## Tableau Analytics Agent - Security Best Practices

---

## 1. Authentication & Authorization

### DO
```python
# Use dependency injection for auth
from fastapi import Security, Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

api_key_header = APIKeyHeader(name="X-API-Key")

@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    api_key: str = Security(verify_api_key)
):
    ...
```

### DON'T
```python
# Never expose endpoints without auth
@app.post("/api/chat")
async def chat(request: ChatRequest):  # No auth!
    ...
```

---

## 2. Input Validation

### DO
```python
from pydantic import BaseModel, Field, validator

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: str | None = Field(None, regex=r'^[a-z0-9-]+$')

    @validator('message')
    def sanitize_message(cls, v):
        # Remove potential injection patterns
        dangerous = ['ignore previous', 'system prompt', '<|']
        for pattern in dangerous:
            if pattern.lower() in v.lower():
                raise ValueError('Invalid input')
        return v
```

### DON'T
```python
# Never trust user input
message = request.message  # Direct use without validation
exec(f"result = {message}")  # Code injection!
```

---

## 3. Code Execution

### DO
```python
# Use containerized execution
import docker

def safe_execute(code: str) -> str:
    client = docker.from_env()
    result = client.containers.run(
        "python:3.11-slim",
        f"python -c '{code}'",
        network_disabled=True,
        read_only=True,
        mem_limit="256m",
        user="nobody",
    )
    return result.decode()
```

### DON'T
```python
# Never exec() user-influenced code directly
exec(user_code, globals())  # Full system access!

# Don't trust import restrictions alone
ALLOWED = {'pandas', 'numpy'}  # Can be bypassed
```

---

## 4. Secrets Management

### DO
```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Use SecretStr for sensitive values
    api_key: SecretStr
    tableau_token: SecretStr

    # Never log secrets
    def __repr__(self):
        return "Settings(***)"

# Access secret value only when needed
token = settings.tableau_token.get_secret_value()
```

### DON'T
```python
# Never hardcode secrets
API_KEY = "sk-1234567890"  # Exposed in source!

# Never log secrets
logger.info(f"Using token: {settings.token}")  # Leaked!
```

---

## 5. Logging

### DO
```python
import re
import logging

class SanitizingFilter(logging.Filter):
    PATTERNS = [
        (r'\b[\w.-]+@[\w.-]+\.\w+\b', '[EMAIL]'),
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),
    ]

    def filter(self, record):
        for pattern, replacement in self.PATTERNS:
            record.msg = re.sub(pattern, replacement, str(record.msg))
        return True

# Log request IDs, not content
logger.info(f"Request {request_id}: status=success")
```

### DON'T
```python
# Never log full user input
logger.info(f"User message: {request.message}")  # PII exposed!

# Never log credentials
logger.debug(f"Connecting with token: {token}")  # Secret leaked!
```

---

## 6. Error Handling

### DO
```python
@app.exception_handler(Exception)
async def handle_error(request, exc):
    error_id = str(uuid.uuid4())[:8]

    # Log full error internally
    logger.error(f"Error {error_id}", exc_info=True)

    # Return generic message externally
    return JSONResponse(
        status_code=500,
        content={"error": "Internal error", "id": error_id}
    )
```

### DON'T
```python
# Never expose stack traces
return JSONResponse(
    status_code=500,
    content={"error": str(exc), "traceback": traceback.format_exc()}
)
```

---

## 7. HTTP Security

### DO
```python
# Add security headers
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

# Strict CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],  # Specific origin
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

### DON'T
```python
# Overly permissive CORS
allow_origins=["*"],  # Any origin!
allow_methods=["*"],  # Any method!
allow_credentials=True,  # With cookies!
```

---

## 8. Rate Limiting

### DO
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/chat")
@limiter.limit("10/minute")
async def chat(request: Request, ...):
    ...

# Also limit by user if authenticated
@limiter.limit("100/hour", key_func=lambda r: r.state.user_id)
```

### DON'T
```python
# No limits = DoS vulnerability
@app.post("/api/expensive-operation")
async def process():  # Can be called unlimited times!
    ...
```

---

## 9. Docker Security

### DO
```dockerfile
# Use non-root user
RUN useradd -r -u 1000 appuser
USER appuser

# Read-only filesystem
docker run --read-only ...

# Drop capabilities
docker run --cap-drop ALL ...

# Resource limits
docker run --memory=512m --cpus=1 ...
```

### DON'T
```dockerfile
# Running as root
USER root  # Full system access!

# Mounting sensitive paths
volumes:
  - /etc:/etc  # Host filesystem exposed!
```

---

## 10. Dependency Security

### DO
```bash
# Pin exact versions
fastapi==0.115.0
pydantic==2.7.0

# Regular vulnerability scanning
pip-audit
safety check
npm audit

# Update regularly
pip install --upgrade package
```

### DON'T
```bash
# Unpinned versions
fastapi>=0.100.0  # Could get vulnerable version

# Ignoring audit warnings
npm audit  # 5 high vulnerabilities found
# Proceeds anyway...
```

---

## Quick Reference: Security Checklist

- [ ] All endpoints require authentication
- [ ] Input validated with Pydantic
- [ ] No direct code execution of user input
- [ ] Secrets stored in environment/secrets manager
- [ ] Logs sanitized of PII
- [ ] Error messages don't expose internals
- [ ] Security headers configured
- [ ] CORS policy is restrictive
- [ ] Rate limiting implemented
- [ ] Docker runs as non-root with limits
- [ ] Dependencies pinned and scanned

---

*Last updated: 2026-02-02*
