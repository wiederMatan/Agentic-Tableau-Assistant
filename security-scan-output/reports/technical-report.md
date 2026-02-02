# Technical Security Report

**Project:** Tableau Analytics Agent
**Version:** 0.1.0
**Scan Date:** 2026-02-02
**Report Version:** 1.0

---

## Table of Contents

1. [Scope and Methodology](#scope-and-methodology)
2. [Architecture Overview](#architecture-overview)
3. [Detailed Findings](#detailed-findings)
4. [Dependency Analysis](#dependency-analysis)
5. [Configuration Review](#configuration-review)
6. [Remediation Roadmap](#remediation-roadmap)

---

## Scope and Methodology

### In Scope
- Backend Python code (`backend/src/`)
- Frontend TypeScript code (`frontend/src/`)
- Configuration files (Docker, environment)
- Dependencies (requirements.txt, package.json)
- Infrastructure (Dockerfile, docker-compose.yml)

### Methodology
- Static Application Security Testing (SAST)
- Dependency vulnerability scanning
- Configuration review
- Manual code review
- Threat modeling

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        ATTACK SURFACE                           │
└─────────────────────────────────────────────────────────────────┘

Internet
    │
    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Backend   │────▶│   Tableau   │
│  (Next.js)  │     │  (FastAPI)  │     │   Server    │
│  Port 3000  │     │  Port 8000  │     │             │
└─────────────┘     └──────┬──────┘     └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  Vertex AI  │
                   │  (Gemini)   │
                   └─────────────┘

Security Boundaries:
- NO authentication between client and backend
- PAT authentication to Tableau (long-lived token)
- ADC authentication to GCP (machine credentials)
```

---

## Detailed Findings

### CRITICAL SEVERITY

#### SEC-001: Missing API Authentication

**CWE:** CWE-306 (Missing Authentication for Critical Function)
**CVSS:** 9.1 (Critical)

| Attribute | Value |
|-----------|-------|
| Location | `backend/src/api.py:115-159` |
| Affected Endpoints | `/api/chat`, `/api/chat/sync` |
| Exploitability | Network-accessible, no auth required |
| Business Impact | Data breach, cost abuse, compliance violation |

**Technical Details:**
```python
# No authentication middleware or decorator
@app.post("/api/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    # Directly processes request without auth check
    return EventSourceResponse(...)
```

**Remediation Code:**
```python
from fastapi import Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.api_key:
        raise HTTPException(401, "Invalid API key")
    return api_key

@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    _: str = Security(verify_api_key)
):
    ...
```

---

#### SEC-002: Arbitrary Code Execution via Python REPL

**CWE:** CWE-94 (Improper Control of Code Generation)
**CVSS:** 9.8 (Critical)

| Attribute | Value |
|-----------|-------|
| Location | `backend/src/tools/analysis_tools.py:243` |
| Attack Vector | LLM-generated code execution |
| Exploitability | Requires prompt injection or malicious LLM output |
| Business Impact | Full server compromise, data exfiltration |

**Technical Details:**

The sandbox attempts to restrict imports but has multiple bypass vectors:

1. **Pre-imported pandas allows file access:**
```python
# Attacker-influenced code
df = pd.read_csv('/etc/passwd', sep=':', header=None)
print(df.to_string())
```

2. **getattr allows object traversal:**
```python
# Escape via __class__.__mro__
().__class__.__mro__[1].__subclasses__()
```

3. **NumPy can access memory:**
```python
import numpy as np
np.frombuffer(bytes(1000), dtype=np.uint8)  # Memory access
```

**Remediation:**
Use Docker-based execution or remove REPL entirely:

```python
# Docker-based sandbox
import docker

def execute_sandboxed(code: str) -> dict:
    client = docker.from_env()
    container = client.containers.run(
        "python:3.11-slim",
        f"python -c '{code}'",
        network_disabled=True,
        read_only=True,
        mem_limit="256m",
        cpu_quota=50000,
        user="nobody",
        detach=True,
    )
    # ... handle result
```

---

### HIGH SEVERITY

#### SEC-003: No Rate Limiting

**CWE:** CWE-770 (Allocation of Resources Without Limits)
**CVSS:** 7.5

```python
# Recommended implementation
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/chat")
@limiter.limit("10/minute")
async def chat(...):
    ...
```

---

#### SEC-004: CORS Misconfiguration

**CWE:** CWE-942 (Permissive Cross-domain Policy)
**CVSS:** 7.1

Current configuration:
```python
allow_methods=["*"],  # All methods
allow_headers=["*"],  # All headers
allow_credentials=True,  # With credentials
```

Recommended:
```python
allow_methods=["GET", "POST"],
allow_headers=["Content-Type", "Authorization"],
allow_credentials=False,
```

---

#### SEC-005: LLM Prompt Injection

**CWE:** CWE-74 (Improper Neutralization)
**CVSS:** 8.1

User input directly embedded in prompts:
```python
# Vulnerable
HumanMessage(content=user_message)

# Hardened
sanitized = sanitize_input(user_message)
HumanMessage(content=f"<user_query>{sanitized}</user_query>")
```

---

### MEDIUM SEVERITY

| ID | Finding | CWE | CVSS | Location |
|----|---------|-----|------|----------|
| SEC-006 | Information Disclosure | CWE-200 | 5.3 | `api.py:162-191` |
| SEC-007 | Insecure Docker Config | CWE-250 | 6.5 | `docker-compose.yml` |
| SEC-008 | Sensitive Data Logging | CWE-532 | 5.5 | `api.py:125,145` |

---

### LOW SEVERITY

| ID | Finding | CWE | CVSS |
|----|---------|-----|------|
| SEC-009 | Missing Security Headers | CWE-16 | 3.7 |
| SEC-010 | Unix-only Timeout | CWE-400 | 3.1 |

---

## Dependency Analysis

### Backend Dependencies (requirements.txt)

| Package | Version | Known CVEs | Status |
|---------|---------|------------|--------|
| fastapi | >=0.115.0 | None | OK |
| langchain-core | >=0.3.30 | None | OK |
| pandas | >=2.2.0 | None | OK |
| pydantic | >=2.7.0 | None | OK |
| tableauserverclient | >=0.33.0 | None | OK |

**Note:** Dependency versions are minimum constraints. Pin exact versions for reproducibility.

### Frontend Dependencies (package.json)

| Package | Version | Known CVEs | Status |
|---------|---------|------------|--------|
| next | ^14.2.20 | None | OK |
| react | ^18.3.1 | None | OK |
| zustand | ^5.0.0 | None | OK |

---

## Configuration Review

### Environment Variables

| Variable | Security | Recommendation |
|----------|----------|----------------|
| TABLEAU_TOKEN_VALUE | SecretStr | Use secrets manager |
| TABLEAU_TOKEN_NAME | Plain text | Move to secrets |
| GCP_PROJECT_ID | Plain text | OK for non-sensitive |

### Docker Configuration

| Setting | Current | Recommended |
|---------|---------|-------------|
| User | appuser (1000) | OK |
| Capabilities | All | Drop all, add minimal |
| Read-only FS | No | Yes |
| Resource limits | None | Add mem/cpu limits |
| Network | Default | Restrict with policies |

---

## Remediation Roadmap

### Phase 1: Critical (24-48 hours)
- [ ] Implement API authentication
- [ ] Harden or disable Python REPL

### Phase 2: High (1 week)
- [ ] Add rate limiting
- [ ] Fix CORS configuration
- [ ] Implement prompt sanitization

### Phase 3: Medium (2 weeks)
- [ ] Remove info disclosure endpoints
- [ ] Secure Docker configuration
- [ ] Implement log sanitization

### Phase 4: Hardening (1 month)
- [ ] Add security headers
- [ ] Cross-platform timeout fix
- [ ] Security monitoring/alerting
- [ ] Penetration testing

---

## Appendix: OWASP API Top 10 Mapping

| OWASP | Finding | Status |
|-------|---------|--------|
| API1: Broken Object Level Auth | N/A (no objects) | - |
| API2: Broken Authentication | SEC-001 | FAIL |
| API3: Broken Object Property Auth | N/A | - |
| API4: Unrestricted Resource Consumption | SEC-003 | FAIL |
| API5: Broken Function Level Auth | N/A | - |
| API6: Unrestricted Access to Sensitive Flows | SEC-001 | FAIL |
| API7: Server Side Request Forgery | Potential in Tableau | REVIEW |
| API8: Security Misconfiguration | SEC-004, SEC-006 | FAIL |
| API9: Improper Inventory Management | N/A | - |
| API10: Unsafe Consumption of APIs | SEC-005 (LLM) | FAIL |

---

*End of Technical Report*
