"""Minimal test spec (P2): basic liveness & optional handshake.

For P2 we implement a pragmatic approach:
- Launch the server (without blocking) and probe liveness.
- If SSE and a health path is available (default: /healthz), HTTP 200 suffices.
- If STDIO, ensure process stays alive for a short window.

Optional: If `modelcontextprotocol` client is available, attempt a shallow
initialize → tools/list call. This remains best-effort to keep P2 lightweight.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import httpx

from mcp_builder.conformance.runner import _prepare_target  # reuse helper


class TestFailure(Exception):
    pass


def _start_process(target: Path) -> tuple[subprocess.Popen, dict, Path, Path | None]:
    runner, workdir, tmp = _prepare_target(target)
    cmd = runner.get("command")
    if not isinstance(cmd, list) or not cmd:
        raise TestFailure("runner.command must be a non-empty list")
    proc = subprocess.Popen(cmd, cwd=workdir)
    return proc, runner, workdir, tmp


def run_basic_tests(target: str, timeout: int = 10) -> None:
    """Run a basic liveness test and a best-effort handshake where possible.

    Raises TestFailure on failure.
    """
    t = Path(target).resolve()
    proc, runner, workdir, tmp = _start_process(t)
    try:
        # Wait a bit for startup
        start = time.time()
        while time.time() - start < timeout:
            if proc.poll() is not None:
                raise TestFailure(f"process exited early with code {proc.returncode}")
            time.sleep(0.25)
            # SSE liveness via health
            if runner.get("type") == "sse":
                url = runner.get("url") or "http://127.0.0.1:8000/messages/"
                # Try a sibling health path
                health = url.replace("/messages/", "/healthz")
                try:
                    r = httpx.get(health, timeout=2)
                    if r.status_code == 200:
                        break
                except Exception:
                    pass
            else:
                # STDIO: if alive for 1 second, we consider it started for P2
                if time.time() - start > 1.0:
                    break
        else:
            raise TestFailure("timeout waiting for server readiness")

        # Optional: try a tiny handshake if client lib is present
        try:
            import importlib

            m = importlib.import_module("modelcontextprotocol")
            _ = m  # placeholder — real handshake to be wired in later
        except Exception:
            pass
    finally:
        try:
            proc.terminate()
        finally:
            if tmp and tmp.exists():
                import shutil

                shutil.rmtree(tmp, ignore_errors=True)
