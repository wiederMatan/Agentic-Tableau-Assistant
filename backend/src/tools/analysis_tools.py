"""Analysis tools for the analytics agent."""

import io
import logging
import signal
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

from langchain_core.tools import tool

from ..config import get_settings
from ..schemas import PythonReplInput, PythonReplOutput

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Raised when code execution exceeds the timeout."""

    pass


def _timeout_handler(signum: int, frame: Any) -> None:
    """Signal handler for execution timeout."""
    raise TimeoutError("Code execution timed out")


# Restricted builtins for sandboxed execution
SAFE_BUILTINS = {
    # Types
    "bool": bool,
    "bytes": bytes,
    "complex": complex,
    "dict": dict,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "list": list,
    "object": object,
    "set": set,
    "str": str,
    "tuple": tuple,
    "type": type,
    # Functions
    "abs": abs,
    "all": all,
    "any": any,
    "ascii": ascii,
    "bin": bin,
    "callable": callable,
    "chr": chr,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "format": format,
    "getattr": getattr,
    "hasattr": hasattr,
    "hash": hash,
    "hex": hex,
    "id": id,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "iter": iter,
    "len": len,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "setattr": setattr,
    "slice": slice,
    "sorted": sorted,
    "sum": sum,
    "zip": zip,
    # Constants
    "True": True,
    "False": False,
    "None": None,
    # Exceptions (commonly needed)
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "AttributeError": AttributeError,
    "ZeroDivisionError": ZeroDivisionError,
}

# Allowed imports for data analysis
ALLOWED_IMPORTS = {
    "pandas",
    "numpy",
    "statistics",
    "math",
    "datetime",
    "collections",
    "itertools",
    "functools",
    "json",
    "csv",
    "io",
    "re",
}


def _safe_import(name: str, *args: Any, **kwargs: Any) -> Any:
    """Restricted import function that only allows safe modules."""
    # Handle 'from X import Y' - name will be the module
    module_name = name.split(".")[0]

    if module_name not in ALLOWED_IMPORTS:
        raise ImportError(
            f"Import of '{name}' is not allowed. "
            f"Allowed modules: {', '.join(sorted(ALLOWED_IMPORTS))}"
        )

    return __builtins__["__import__"](name, *args, **kwargs)


def _create_safe_globals() -> dict[str, Any]:
    """Create a restricted globals dict for code execution."""
    safe_globals = {"__builtins__": SAFE_BUILTINS.copy()}
    safe_globals["__builtins__"]["__import__"] = _safe_import

    # Pre-import common data analysis libraries
    try:
        import pandas as pd
        import numpy as np

        safe_globals["pd"] = pd
        safe_globals["pandas"] = pd
        safe_globals["np"] = np
        safe_globals["numpy"] = np
    except ImportError:
        logger.warning("pandas/numpy not available for REPL")

    try:
        import statistics

        safe_globals["statistics"] = statistics
    except ImportError:
        pass

    try:
        import math

        safe_globals["math"] = math
    except ImportError:
        pass

    try:
        from datetime import datetime, timedelta, date

        safe_globals["datetime"] = datetime
        safe_globals["timedelta"] = timedelta
        safe_globals["date"] = date
    except ImportError:
        pass

    try:
        from io import StringIO

        safe_globals["StringIO"] = StringIO
    except ImportError:
        pass

    return safe_globals


@tool(args_schema=PythonReplInput)
def python_repl(code: str, timeout_seconds: int = 30) -> dict[str, Any]:
    """Execute Python code for data analysis in a sandboxed environment.

    Use this tool to perform calculations, data transformations, and
    statistical analysis on data retrieved from Tableau.

    Pre-imported libraries:
    - pandas (as pd)
    - numpy (as np)
    - statistics
    - math
    - datetime, timedelta, date
    - StringIO (for parsing CSV data)

    Args:
        code: Python code to execute. Should be complete and self-contained.
        timeout_seconds: Maximum execution time (default: 30 seconds).

    Returns:
        Dictionary with execution results, stdout, stderr, and success status.

    Example:
        To analyze CSV data from Tableau:
        ```
        import pandas as pd
        from io import StringIO

        csv_data = '''Name,Sales,Region
        Alice,100,East
        Bob,200,West'''

        df = pd.read_csv(StringIO(csv_data))
        total_sales = df['Sales'].sum()
        print(f"Total Sales: {total_sales}")
        ```
    """
    settings = get_settings()
    timeout = min(timeout_seconds, settings.python_repl_timeout)

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    import time

    start_time = time.time()

    try:
        # Create sandboxed globals
        safe_globals = _create_safe_globals()
        local_vars: dict[str, Any] = {}

        # Set up timeout (Unix only)
        if hasattr(signal, "SIGALRM"):
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)

        try:
            # Redirect stdout/stderr and execute
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Compile to catch syntax errors
                compiled = compile(code, "<repl>", "exec")

                # Execute in sandboxed environment
                exec(compiled, safe_globals, local_vars)

                # Try to get the last expression result
                result = local_vars.get("result", local_vars.get("_", None))

        finally:
            # Clear alarm and restore handler
            if hasattr(signal, "SIGALRM"):
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

        execution_time = (time.time() - start_time) * 1000

        output = PythonReplOutput(
            success=True,
            stdout=stdout_capture.getvalue(),
            stderr=stderr_capture.getvalue(),
            result=_serialize_result(result),
            execution_time_ms=execution_time,
        )

        logger.info(f"Python REPL executed successfully in {execution_time:.2f}ms")
        return output.model_dump()

    except TimeoutError:
        logger.warning(f"Python REPL execution timed out after {timeout}s")
        return PythonReplOutput(
            success=False,
            stdout=stdout_capture.getvalue(),
            stderr=f"Execution timed out after {timeout} seconds",
            execution_time_ms=timeout * 1000,
        ).model_dump()

    except SyntaxError as e:
        logger.warning(f"Python REPL syntax error: {e}")
        return PythonReplOutput(
            success=False,
            stderr=f"Syntax error: {e}",
            execution_time_ms=(time.time() - start_time) * 1000,
        ).model_dump()

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        error_tb = traceback.format_exc()
        logger.warning(f"Python REPL execution error: {e}")

        return PythonReplOutput(
            success=False,
            stdout=stdout_capture.getvalue(),
            stderr=f"{type(e).__name__}: {e}\n{error_tb}",
            execution_time_ms=execution_time,
        ).model_dump()


def _serialize_result(result: Any) -> Any:
    """Serialize execution result to JSON-compatible format."""
    if result is None:
        return None

    # Handle pandas objects
    try:
        import pandas as pd

        if isinstance(result, pd.DataFrame):
            return {
                "type": "DataFrame",
                "shape": list(result.shape),
                "columns": list(result.columns),
                "preview": result.head(10).to_dict(orient="records"),
            }
        if isinstance(result, pd.Series):
            return {
                "type": "Series",
                "name": result.name,
                "length": len(result),
                "preview": result.head(10).to_dict(),
            }
    except ImportError:
        pass

    # Handle numpy arrays
    try:
        import numpy as np

        if isinstance(result, np.ndarray):
            return {
                "type": "ndarray",
                "shape": list(result.shape),
                "dtype": str(result.dtype),
                "preview": result[:10].tolist() if result.size > 0 else [],
            }
    except ImportError:
        pass

    # Handle basic types
    if isinstance(result, (str, int, float, bool, type(None))):
        return result

    if isinstance(result, (list, tuple)):
        return [_serialize_result(item) for item in result[:100]]

    if isinstance(result, dict):
        return {
            str(k): _serialize_result(v) for k, v in list(result.items())[:100]
        }

    # Fallback to string representation
    return str(result)
