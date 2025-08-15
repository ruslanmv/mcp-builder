from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_builder.signing.checks import sha256, verify_sha256
from mcp_builder.validator import (
    validate_mcp_manifest,
    validate_runner,
    write_scaffolds,
)


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_write_scaffolds_creates_minimal_runner_and_manifest(tmp_path: Path) -> None:
    """
    Ensure write_scaffolds() produces valid runner.json and mcp.server.json
    with the expected minimal fields for an SSE Python server.
    """
    # Act: create scaffolds
    write_scaffolds(
        path=tmp_path,
        transport="sse",
        lang="python",
        name="unit-srv",
        version="0.0.0",
    )

    runner_path = tmp_path / "runner.json"
    manifest_path = tmp_path / "mcp.server.json"

    assert runner_path.exists(), "runner.json should be created"
    assert manifest_path.exists(), "mcp.server.json should be created"

    runner = _read_json(runner_path)
    manifest = _read_json(manifest_path)

    # Validate with schema helpers (will raise on failure)
    validate_runner(runner)
    validate_mcp_manifest(manifest)

    # Minimal shape checks (keep permissive; tighten later as schemas evolve)
    assert runner.get("type") in {"sse", "stdio"}
    assert isinstance(runner.get("env"), dict)
    assert (
        "limits" in runner and {"timeoutMs", "maxInputKB", "maxOutputKB"} <= runner["limits"].keys()
    )
    assert (
        "security" in runner
        and {"readOnlyDefault", "fsAllowlist", "egressAllowlist"} <= runner["security"].keys()
    )

    assert manifest.get("schemaVersion") in {"1.0", "1"}  # tolerate string style
    assert manifest.get("name") == "unit-srv"
    assert manifest.get("version") == "0.0.0"
    assert isinstance(manifest.get("transports"), list) and len(manifest["transports"]) >= 1
    assert manifest["transports"][0].get("type") in {"sse", "stdio"}


def test_sha256_verify_roundtrip(tmp_path: Path) -> None:
    """
    Compute sha256 for a temp file, verify success, and ensure a mismatch raises.
    """
    data = b"mcp-builder unit test payload\n"
    f = tmp_path / "payload.bin"
    f.write_bytes(data)

    digest = sha256(f)
    assert (
        isinstance(digest, str)
        and len(digest) == 64
        and all(c in "0123456789abcdef" for c in digest)
    )

    # Should not raise on correct digest
    verify_sha256(f, expected=digest)

    # Corrupt expectation should raise
    bad = "0" * 64
    with pytest.raises(Exception):
        verify_sha256(f, expected=bad)
