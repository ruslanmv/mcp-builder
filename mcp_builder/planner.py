"""Plan emission for Matrix Hub installer (P0)."""

from __future__ import annotations

import json
from pathlib import Path

from mcp_builder.validator import validate_plan


def emit_install_plan(bundle_path: Path, name: str = "unnamed", transport: str = "SSE") -> str:
    """Create a simple plan JSON for a local zip bundle.

    The plan references the archive via a file:// URL and includes a digest read from
    the sibling `.sha256` file. Minimal `mcp_registration` is included so Matrix Hub
    can pre-register a server if desired.
    """
    bundle_path = bundle_path.resolve()
    sha_path = Path(str(bundle_path) + ".sha256")
    if not sha_path.exists():
        raise FileNotFoundError(f"Missing digest file: {sha_path}")
    sha_hex = sha_path.read_text(encoding="utf-8").strip()

    plan = {
        "id": f"mcp_server:{name}@0.0.0",
        "artifacts": [
            {
                "kind": "zip",
                "spec": {
                    "url": bundle_path.as_uri(),
                    "digest": f"sha256:{sha_hex}",
                    "dest": "server",
                },
            }
        ],
        "mcp_registration": {
            "server": {
                "name": name,
                "transport": transport,
                "url": "http://127.0.0.1:8000/messages/",
            }
        },
    }
    validate_plan(plan)
    return json.dumps(plan, indent=2)
