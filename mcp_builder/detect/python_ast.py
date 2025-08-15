"""Lightweight Python detector (P0).

Heuristics:
- If `server_sse.py` exists → transport="sse", entry="server_sse.py".
- Else if `server.py` exists → transport="stdio", entry="server.py".
- Otherwise, report lang="python" with low score, no transport.

We avoid heavy AST parsing in P0 for speed and simplicity; deeper analysis lands in P1.
"""

from __future__ import annotations

from pathlib import Path

from .base import DetectReport


def detect(root: Path) -> DetectReport:
    server_sse = root / "server_sse.py"
    server_stdio = root / "server.py"

    if server_sse.exists():
        return DetectReport(
            score=0.95,
            lang="python",
            transport="sse",
            entrypoints=["server_sse.py"],
            notes=["Found server_sse.py (SSE)"],
        )
    if server_stdio.exists():
        return DetectReport(
            score=0.85,
            lang="python",
            transport="stdio",
            entrypoints=["server.py"],
            notes=["Found server.py (STDIO)"],
        )
    # Unknown layout but Python-ish project? Look for requirements/pyproject as hint
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        return DetectReport(score=0.4, lang="python", notes=["Python project hints present"])
    return DetectReport(score=0.0, notes=["No Python indicators found"])
