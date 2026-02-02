# SEC-007: Insecure Docker Configuration

## Severity: MEDIUM
## CVSS Score: 6.5
## CWE: CWE-250 (Execution with Unnecessary Privileges)

---

## Location

| File | Line | Issue |
|------|------|-------|
| `docker-compose.yml` | 23-24 | Volume mount of entire backend directory |
| `docker-compose.yml` | 25 | GCP credentials mounted from external volume |
| `backend/Dockerfile` | 16-17 | Non-root user created but potential issues |

---

## Description

Several Docker security issues identified:

1. **Development volume mount**: Entire backend directory mounted in container
2. **Credential volume**: GCP credentials mounted at predictable path
3. **No security options**: Missing seccomp, AppArmor, capabilities restrictions
4. **No resource limits**: Vulnerable to resource exhaustion
5. **No read-only filesystem**: Container can modify its filesystem

---

## Vulnerable Configuration

```yaml
# docker-compose.yml
services:
  backend:
    volumes:
      - ./backend:/app                           # Full code mount
      - gcp-credentials:/root/.config/gcloud:ro  # Credentials at root path

    # Missing security options:
    # - security_opt
    # - cap_drop
    # - read_only
    # - mem_limit
    # - cpus
```

```dockerfile
# Dockerfile - User created but late in build
USER appuser  # Created after COPY, inherits file permissions
```

---

## Impact

1. **Code Modification**: Attacker can modify backend code if container compromised
2. **Credential Theft**: GCP credentials accessible in container
3. **Resource Exhaustion**: No limits on CPU/memory
4. **Container Escape**: Without restrictions, escape more likely

---

## Remediation

### Secure docker-compose.yml

```yaml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      # Use secrets instead of env vars
      - TABLEAU_TOKEN_VALUE_FILE=/run/secrets/tableau_token
    secrets:
      - tableau_token
      - gcp_credentials

    # Security options
    security_opt:
      - no-new-privileges:true
      - seccomp:unconfined  # Or use custom profile

    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if needed

    read_only: true
    tmpfs:
      - /tmp:size=100M,mode=1777

    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

    # No volume mounts in production
    # volumes: []

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

secrets:
  tableau_token:
    file: ./secrets/tableau_token.txt
  gcp_credentials:
    file: ./secrets/gcp_credentials.json
```

### Secure Dockerfile

```dockerfile
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/install -r requirements.txt

FROM python:3.11-slim

# Create non-root user FIRST
RUN useradd -r -u 1000 -g nogroup appuser

WORKDIR /app

# Copy dependencies
COPY --from=builder /install /usr/local/lib/python3.11/site-packages

# Copy code with correct ownership
COPY --chown=appuser:nogroup . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Use exec form for proper signal handling
CMD ["python", "main.py"]
```

---

## Effort: MEDIUM
## Priority: PLANNED (2 weeks)

---

## References

- https://docs.docker.com/engine/security/
- https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html
- https://cwe.mitre.org/data/definitions/250.html
