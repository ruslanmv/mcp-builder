"""Python buildpack (P0).

Turns detection results into a build result that includes:
- files: server file (+ requirements.txt if present)
- runner: minimal runner.json dict
- mcp_manifest: minimal mcp.server.json dict

Zip packaging and checksums come in later phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcp_builder.detect.base import DetectReport


@dataclass
class BuildResult:
    files: list[Path]
    runner: dict
    mcp_manifest: dict


def build(ctx, info: DetectReport) -> BuildResult:
    # Determine the server entry file
    entry = (info.entrypoints[0] if info.entrypoints else None) or (
        "server_sse.py" if info.transport == "sse" else "server.py"
    )
    root = Path(".").resolve() if ctx is None else Path(getattr(ctx, "root", ".")).resolve()

    server_path = root / entry
    files: list[Path] = [server_path]

    req = root / "requirements.txt"
    if req.exists():
        files.append(req)

    transport = info.transport or ("sse" if server_path.name == "server_sse.py" else "stdio")

    runner = {
        "type": transport,
        "command": ["python", server_path.name],
        "url": "http://127.0.0.1:8000/messages/" if transport == "sse" else None,
        "env": {},
        "limits": {"timeoutMs": 15000, "maxInputKB": 128, "maxOutputKB": 256},
        "security": {
            "readOnlyDefault": True,
            "fsAllowlist": [],
            "egressAllowlist": [],
        },
    }

    mcp_manifest = {
        "schemaVersion": "1.0",
        "name": "unnamed",
        "version": "0.0.0",
        "transports": [{"type": transport, "url": runner.get("url")}],
        "tools": [t.get("name", "hello") for t in (info.tools or [])],
        "limits": runner["limits"],
        "security": runner["security"],
        "build": {
            "lang": info.lang or "python",
            "runner": "uv" if (root / "uv.lock").exists() else "pip",
        },
    }

    return BuildResult(files=files, runner=runner, mcp_manifest=mcp_manifest)
