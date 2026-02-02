# SEC-008: Sensitive Data in Logs

## Severity: MEDIUM
## CVSS Score: 5.5
## CWE: CWE-532 (Insertion of Sensitive Information into Log File)

---

## Location

| File | Line | Issue |
|------|------|-------|
| `backend/src/api.py` | 125 | User message logged (first 100 chars) |
| `backend/src/api.py` | 145 | User message logged |
| `backend/src/tableau_client.py` | 72 | Server URL logged |
| `backend/src/tools/analysis_tools.py` | 264 | Code execution success logged |

---

## Description

User queries and potentially sensitive data are logged. In production, logs may be:
- Stored in centralized logging systems
- Accessible to operations staff
- Retained for compliance periods
- Potentially leaked via log aggregation services

---

## Vulnerable Code

```python
# api.py:125 - User queries logged
logger.info(f"Received chat request: {request.message[:100]}...")

# tableau_client.py:72 - Server URL logged
logger.info(f"Connecting to Tableau Server: {self.server_url}")

# Could log PII in user messages like:
# "Show me data for customer John Smith at john@email.com"
```

---

## Impact

1. **PII Exposure**: Customer names, emails in queries
2. **Business Data Leak**: Sensitive business queries logged
3. **Compliance Violation**: GDPR right to erasure complicated
4. **Insider Threat**: Log access exposes queries

---

## Remediation

### Implement Structured Logging with Redaction

```python
import re
import logging
from typing import Any

class SanitizingFormatter(logging.Formatter):
    """Formatter that redacts sensitive information."""

    PATTERNS = [
        (r'\b[\w.-]+@[\w.-]+\.\w+\b', '[EMAIL]'),  # Email
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),       # SSN
        (r'\b\d{16}\b', '[CARD]'),                  # Credit card
        (r'(?i)(password|secret|token)[=:]\s*\S+', r'\1=[REDACTED]'),
    ]

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        for pattern, replacement in self.PATTERNS:
            message = re.sub(pattern, replacement, message)
        return message

# Configure logging with sanitization
handler = logging.StreamHandler()
handler.setFormatter(SanitizingFormatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
```

### Log Request IDs Instead of Content

```python
import uuid

@app.post("/api/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    request_id = str(uuid.uuid4())[:8]

    # Log request ID only, not content
    logger.info(f"Chat request {request_id}: message_length={len(request.message)}")

    # Store mapping securely if needed for debugging
    return EventSourceResponse(...)
```

### Configure Log Retention

```python
# config.py
log_retention_days: int = Field(
    default=30,
    description="Log retention period in days",
)

log_pii_enabled: bool = Field(
    default=False,
    description="Whether to log PII (disable in production)",
)
```

---

## Effort: LOW
## Priority: PLANNED (2 weeks)

---

## References

- https://cwe.mitre.org/data/definitions/532.html
- https://owasp.org/www-project-logging-cheat-sheet/
