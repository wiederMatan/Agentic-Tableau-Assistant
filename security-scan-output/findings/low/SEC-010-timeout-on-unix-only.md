# SEC-010: Timeout Protection Only Works on Unix

## Severity: LOW
## CVSS Score: 3.1
## CWE: CWE-400 (Uncontrolled Resource Consumption)

---

## Location

| File | Line | Issue |
|------|------|-------|
| `backend/src/tools/analysis_tools.py` | 231-234 | SIGALRM only available on Unix |
| `backend/src/tools/analysis_tools.py` | 248-252 | Timeout cleanup in finally block |

---

## Description

The Python REPL timeout mechanism uses Unix signals (SIGALRM) which are not available on Windows. On Windows deployments, infinite loops in executed code will not be terminated.

---

## Vulnerable Code

```python
# Set up timeout (Unix only)
if hasattr(signal, "SIGALRM"):  # False on Windows
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(timeout)

# On Windows, this code runs without any timeout protection
try:
    exec(compiled, safe_globals, local_vars)  # Can run forever
finally:
    if hasattr(signal, "SIGALRM"):
        signal.alarm(0)  # Never executed on Windows
```

---

## Impact

1. **DoS on Windows**: Infinite loops consume resources indefinitely
2. **Resource Exhaustion**: CPU pegged at 100% until process killed
3. **Deployment Limitation**: Windows deployments are vulnerable

---

## Remediation

### Use Threading-based Timeout (Cross-platform)

```python
import concurrent.futures
from threading import Thread

def python_repl(code: str, timeout_seconds: int = 30) -> dict:
    """Cross-platform timeout using ThreadPoolExecutor."""
    settings = get_settings()
    timeout = min(timeout_seconds, settings.python_repl_timeout)

    def execute_code():
        safe_globals = _create_safe_globals()
        local_vars = {}
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            compiled = compile(code, "<repl>", "exec")
            exec(compiled, safe_globals, local_vars)

        return {
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
            "result": local_vars.get("result"),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(execute_code)
        try:
            result = future.result(timeout=timeout)
            return PythonReplOutput(success=True, **result).model_dump()
        except concurrent.futures.TimeoutError:
            return PythonReplOutput(
                success=False,
                stderr=f"Execution timed out after {timeout} seconds",
            ).model_dump()
```

### Alternative: Multiprocessing with Timeout

```python
import multiprocessing

def python_repl(code: str, timeout_seconds: int = 30) -> dict:
    """Process-based timeout (can kill stuck code)."""

    def worker(code, result_queue):
        try:
            # Execute code in separate process
            result = execute_code_sandboxed(code)
            result_queue.put(result)
        except Exception as e:
            result_queue.put({"error": str(e)})

    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=worker, args=(code, result_queue))
    process.start()
    process.join(timeout=timeout_seconds)

    if process.is_alive():
        process.terminate()
        process.join()
        return {"success": False, "stderr": "Timeout"}

    return result_queue.get()
```

---

## Effort: LOW
## Priority: BEST EFFORT

---

## References

- https://cwe.mitre.org/data/definitions/400.html
- https://docs.python.org/3/library/signal.html
