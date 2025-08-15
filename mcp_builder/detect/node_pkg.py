"""Node package detector (P3).

Heuristics:
- Look for package.json and presence of `@modelcontextprotocol/sdk` or similar deps
- Entry candidates: `server.js`, `src/server.js`, `index.js`
- Transport guess: `sse` if a string contains `/messages/` and a web framework dep is present; otherwise `stdio`
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp_builder.detect.base import DetectReport

_NODE_HINT_DEPS = {
    "@modelcontextprotocol/sdk",
    "modelcontextprotocol",
}
_WEB_DEPS = {"express", "h3", "fastify", "koa"}
_CANDIDATE_ENTRIES = [
    "server.js",
    "src/server.js",
    "index.js",
]


def _read_package_json(root: Path) -> dict | None:
    pj = root / "package.json"
    if not pj.exists():
        return None
    try:
        return json.loads(pj.read_text(encoding="utf-8"))
    except Exception:
        return None


def detect(root: Path) -> DetectReport:
    pkg = _read_package_json(root)
    if not pkg:
        return DetectReport(score=0.0, notes=["No package.json found"])

    deps = set((pkg.get("dependencies") or {}).keys()) | set(
        (pkg.get("devDependencies") or {}).keys()
    )
    if not (_NODE_HINT_DEPS & deps):
        # Not clearly an MCP node project
        return DetectReport(score=0.3, lang="node", notes=["No MCP SDK dep detected"])

    entries: list[str] = [p for p in _CANDIDATE_ENTRIES if (root / p).exists()]
    transport = "stdio"
    if any(d in deps for d in _WEB_DEPS):
        # best-effort text search for /messages/ endpoint
        for e in entries:
            try:
                txt = (root / e).read_text(encoding="utf-8")
                if "/messages/" in txt:
                    transport = "sse"
                    break
            except Exception:
                pass

    score = 0.8 if entries else 0.6
    return DetectReport(
        score=score,
        lang="node",
        transport=transport,
        entrypoints=entries or ["server.js"],
        notes=["Detected Node MCP project"],
    )
