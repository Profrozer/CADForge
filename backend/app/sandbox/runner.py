"""Parent-side wrapper around the sandbox harness subprocess."""

import json
import os
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).with_name("harness.py")
RESULT_MARKER = "===CADFORGE_RESULT==="

# Env vars that look like credentials never reach the sandbox.
_SECRET_HINTS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")


def _sandbox_env() -> dict:
    return {
        k: v for k, v in os.environ.items()
        if not any(hint in k.upper() for hint in _SECRET_HINTS)
    }


def execute_cadquery(code: str, out_dir: str, timeout: int = 90) -> dict:
    """Run generated CadQuery code; returns the harness result dict.

    Never raises for code/geometry failures — those come back as
    {"ok": False, "kind": ..., "error": ...} so the pipeline can feed them
    into the self-correction loop.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    code_file = out / "code.py"
    code_file.write_text(code, encoding="utf-8")

    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(HARNESS), str(code_file), str(out)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(out),
            env=_sandbox_env(),
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "kind": "timeout",
            "error": f"Execution exceeded the {timeout}s limit — likely runaway "
                     "geometry (too many features, infinite loop, or an "
                     "excessively fine operation).",
        }

    stdout = proc.stdout or ""
    if RESULT_MARKER in stdout:
        payload = stdout.split(RESULT_MARKER, 1)[1].strip()
        try:
            return json.loads(payload.splitlines()[0])
        except (json.JSONDecodeError, IndexError):
            pass

    return {
        "ok": False,
        "kind": "python_error",
        "error": ((proc.stderr or "") + "\n" + stdout)[-4000:].strip()
                 or f"Sandbox exited with code {proc.returncode} and no output.",
    }
