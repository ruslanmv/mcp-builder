"""Schema validation and scaffold helpers (P0)."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from jsonschema import Draft202012Validator

# --- Schema loaders ---------------------------------------------------------


def _load_schema(package: str, resource_name: str) -> dict:
    with resources.files(package).joinpath(resource_name).open("r", encoding="utf-8") as f:
        return json.load(f)


def _runner_schema() -> dict:
    return _load_schema("mcp_builder.schema", "runner.schema.json")


def _mcp_server_schema() -> dict:
    return _load_schema("mcp_builder.schema", "mcp.server.schema.json")


def _plan_schema() -> dict:
    return _load_schema("mcp_builder.schema", "plan.schema.json")


# --- Public validators ------------------------------------------------------


def validate_runner(data: dict) -> None:
    Draft202012Validator(_runner_schema()).validate(data)


def validate_mcp_manifest(data: dict) -> None:
    Draft202012Validator(_mcp_server_schema()).validate(data)


def validate_plan(data: dict) -> None:
    Draft202012Validator(_plan_schema()).validate(data)


# --- Scaffolds --------------------------------------------------------------


def write_scaffolds(path: Path, transport: str, lang: str, name: str, version: str) -> None:
    """Write minimal `runner.json` and `mcp.server.json` into *path*.

    This function validates the generated files against the permissive schemas
    to catch obvious mistakes early while keeping P0 flexible.
    """
    path.mkdir(parents=True, exist_ok=True)

    runner = {
        "type": transport,
        "command": ["python", "server_sse.py" if transport == "sse" else "server.py"],
        "url": "http://127.0.0.1:8000/messages/" if transport == "sse" else None,
        "env": {},
        "limits": {"timeoutMs": 15000, "maxInputKB": 128, "maxOutputKB": 256},
        "security": {"readOnlyDefault": True, "fsAllowlist": [], "egressAllowlist": []},
    }
    validate_runner(runner)
    (path / "runner.json").write_text(json.dumps(runner, indent=2), encoding="utf-8")

    mcp_manifest = {
        "schemaVersion": "1.0",
        "name": name,
        "version": version,
        "transports": [{"type": transport, "url": runner.get("url")}],
        "tools": [],
        "limits": runner["limits"],
        "security": runner["security"],
        "build": {"lang": lang, "runner": "unknown"},
    }
    validate_mcp_manifest(mcp_manifest)
    (path / "mcp.server.json").write_text(json.dumps(mcp_manifest, indent=2), encoding="utf-8")
