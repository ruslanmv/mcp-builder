"""Node buildpack (P3): stdio-first, SSE optional later.

Turns a Node project into a bundle candidate by selecting an entry file,
copying `server.js` and `package.json`, and synthesizing a minimal runner and
self-describing manifest. Zip packaging is handled by `package/zip.py`.
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


_CANDIDATE_ENTRIES = ["server.js", "src/server.js", "index.js"]


def _select_entry(root: Path, info: DetectReport) -> Path:
    if info.entrypoints:
        p = root / info.entrypoints[0]
        if p.exists():
            return p
    for name in _CANDIDATE_ENTRIES:
        p = root / name
        if p.exists():
            return p
    # Fallback to server.js in root (created by init if needed)
    return root / "server.js"


def build(ctx, info: DetectReport) -> BuildResult:
    root = Path(".").resolve() if ctx is None else Path(getattr(ctx, "root", ".")).resolve()

    entry = _select_entry(root, info)
    files: list[Path] = []
    if entry.exists():
        files.append(entry)

    pkg = root / "package.json"
    if pkg.exists():
        files.append(pkg)

    # Prefer stdio for P3 unless evidence of SSE exists in detection
    transport = info.transport or "stdio"

    runner = {
        "type": transport,
        "command": ["node", entry.name],
        "url": None if transport == "stdio" else "http://127.0.0.1:8000/messages/",
        "env": {},
        "limits": {"timeoutMs": 15000, "maxInputKB": 128, "maxOutputKB": 256},
        "security": {"readOnlyDefault": True, "fsAllowlist": [], "egressAllowlist": []},
    }

    mcp_manifest = {
        "schemaVersion": "1.0",
        "name": "unnamed-node",
        "version": "0.0.0",
        "transports": [{"type": transport, "url": runner.get("url")}],
        "tools": [t.get("name", "hello") for t in (info.tools or [])],
        "limits": runner["limits"],
        "security": runner["security"],
        "build": {"lang": "node", "runner": "npm"},
    }

    return BuildResult(files=files, runner=runner, mcp_manifest=mcp_manifest)
