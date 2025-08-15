"""Conformance runner (P1 MVP): smoke-run a bundle or directory.

Responsibilities (minimal):
- If *target* is a .zip: extract to a temp dir and load runner.json.
- If *target* is a directory: try to load runner.json; otherwise infer entry.
- Start the server process (SSE or STDIO) using `runner["command"]`.
- Support `--port` injection by exporting PORT in the environment.
- Wait briefly to allow startup; print a ready/timeout message; terminate if not run_only.

This is a smoke check only — protocol handshakes arrive in P2.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from mcp_builder.security.archive import safe_extract_zip


def _load_runner_from_dir(dir_path: Path) -> tuple[dict, Path]:
    runner_path = dir_path / "runner.json"
    if runner_path.exists():
        return json.loads(runner_path.read_text(encoding="utf-8")), dir_path
    # Fallback inference (Python SSE/STDIO)
    if (dir_path / "server_sse.py").exists():
        return {
            "type": "sse",
            "command": ["python", "server_sse.py"],
            "url": "http://127.0.0.1:8000/messages/",
        }, dir_path
    return {"type": "stdio", "command": ["python", "server.py"]}, dir_path


def _prepare_target(target: Path) -> tuple[dict, Path, Path | None]:
    """Return (runner, workdir, temp_root_if_any)."""
    if target.is_dir():
        runner, workdir = _load_runner_from_dir(target)
        return runner, workdir, None

    if target.suffix == ".zip":
        tmp_root = Path(tempfile.mkdtemp(prefix="mcpb-run-"))
        safe_extract_zip(target, tmp_root)
        runner, workdir = _load_runner_from_dir(tmp_root)
        return runner, workdir, tmp_root

    raise ValueError(f"Unsupported target: {target}")


def smoke_run(
    target: str,
    run_only: bool = False,
    port: int = 0,
    timeout: int = 10,
    concurrency: int = 1,  # reserved for future
    extra_env: list[str] | None = None,
) -> None:
    t = Path(target).resolve()
    runner, workdir, tmp = _prepare_target(t)

    env = os.environ.copy()
    if port:
        env["PORT"] = str(port)
    if extra_env:
        for kv in extra_env:
            if "=" in kv:
                k, v = kv.split("=", 1)
                env[k] = v

    cmd = runner.get("command")
    if not isinstance(cmd, list) or not cmd:
        raise RuntimeError("runner.command must be a non-empty list")

    proc = subprocess.Popen(cmd, cwd=workdir, env=env)

    try:
        # Naive readiness wait; P2 will probe health or handshake
        waited = 0
        step = 0.25
        while waited < timeout:
            time.sleep(step)
            waited += step
            if proc.poll() is not None:
                raise RuntimeError(f"Process exited early with code {proc.returncode}")
        if run_only:
            print("running (Ctrl-C to stop)…")
            proc.wait()
        else:
            print("smoke-run complete (process alive)")
    finally:
        try:
            if not run_only:
                proc.terminate()
        finally:
            if tmp and tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
