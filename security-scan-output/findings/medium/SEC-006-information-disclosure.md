# SEC-006: Information Disclosure via API Endpoints

## Severity: MEDIUM
## CVSS Score: 5.3
## CWE: CWE-200 (Exposure of Sensitive Information)

---

## Location

| File | Line | Function |
|------|------|----------|
| `backend/src/api.py` | 162-175 | `health_check()` |
| `backend/src/api.py` | 178-191 | `get_config()` |
| `backend/src/api.py` | 43-54 | `global_exception_handler()` |

---

## Description

Multiple endpoints expose potentially sensitive information:
1. `/api/health` reveals environment and model configuration
2. `/api/config` reveals internal settings
3. Error handler exposes exception details in development mode

---

## Vulnerable Code

```python
@app.get("/api/health")
async def health_check() -> dict:
    settings = get_settings()
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.environment,  # Reveals deployment mode
        "model": settings.vertex_ai_model,    # Reveals AI model in use
    }

@app.get("/api/config")
async def get_config() -> dict:
    settings = get_settings()
    return {
        "max_revision_iterations": settings.max_revision_iterations,
        "max_csv_rows": settings.max_csv_rows,
        "sse_heartbeat_interval": settings.sse_heartbeat_interval,
        "environment": settings.environment,  # Reveals environment
    }

# Error handler exposes details in development
"detail": str(exc) if get_settings().environment == "development" else None,
```

---

## Impact

1. **Reconnaissance**: Attackers learn about infrastructure
2. **Version Fingerprinting**: Identify exploitable versions
3. **Environment Detection**: Tailor attacks to production/dev
4. **AI Model Targeting**: Known model-specific attacks

---

## Remediation

### Minimal Health Check

```python
@app.get("/api/health")
async def health_check() -> dict:
    """Minimal health check - no sensitive details."""
    return {"status": "healthy"}
```

### Remove Config Endpoint or Secure It

```python
# Option 1: Remove entirely (recommended)
# Delete the /api/config endpoint

# Option 2: Require authentication
@app.get("/api/config")
async def get_config(api_key: str = Security(verify_api_key)) -> dict:
    ...
```

### Secure Error Handling

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Generate unique error ID for tracking
    error_id = str(uuid.uuid4())[:8]

    # Log full error internally
    logger.error(f"Error {error_id}: {exc}", exc_info=True)

    # Return generic message externally
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "error_id": error_id,  # For support reference
        },
    )
```

---

## Effort: LOW
## Priority: PLANNED (2 weeks)

---

## References

- https://cwe.mitre.org/data/definitions/200.html
- https://owasp.org/www-project-api-security/
