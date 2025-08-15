"""Installer (P1 MVP): materialize bundles into ~/.matrix/runners/<alias>/<version>/.

Supported surfaces (P1):
- zip: local path or URL; optional SHA-256 verification via sibling .sha256 or provided value
- dir: copy a local source tree; synthesize runner/manifest if missing

Behavior:
- Use a staging directory and atomic rename to avoid partial installs
- Write a `runner.lock.json` with minimal metadata
- Optionally run a quick smoke probe to ensure the process starts
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from mcp_builder.conformance.runner import smoke_run
from mcp_builder.detect.base import detect_project
from mcp_builder.installer.surfaces import Surface, resolve_surface
from mcp_builder.security.archive import safe_extract_zip
from mcp_builder.signing.checks import sha256, verify_sha256
from mcp_builder.validator import write_scaffolds

RUNNERS_HOME = Path(os.path.expanduser("~/.matrix/runners"))


@dataclass
class InstallResult:
    alias: str
    version: str
    path: Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_runner_and_manifest(dir_path: Path) -> tuple[dict | None, dict | None]:
    runner = None
    manifest = None
    rp = dir_path / "runner.json"
    mp = dir_path / "mcp.server.json"
    if rp.exists():
        runner = json.loads(rp.read_text(encoding="utf-8"))
    if mp.exists():
        manifest = json.loads(mp.read_text(encoding="utf-8"))
    return runner, manifest


def _synthesize_if_missing(dir_path: Path, alias: str) -> tuple[dict, dict]:
    runner, manifest = _load_runner_and_manifest(dir_path)
    if runner and manifest:
        return runner, manifest

    report = detect_project(dir_path)
    transport = report.transport or ("sse" if (dir_path / "server_sse.py").exists() else "stdio")
    name = alias
    version = "0.0.0"

    # Write scaffolds safely
    write_scaffolds(dir_path, transport, report.lang or "python", name, version)
    return _load_runner_and_manifest(dir_path)


def _atomic_rename(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise FileExistsError(f"Install target already exists: {dst}")
    os.replace(src, dst)


def _final_path(alias: str, version: str) -> Path:
    return RUNNERS_HOME / alias / version


def _write_lock(
    target_dir: Path,
    *,
    alias: str,
    version: str,
    source: str,
    bundle_sha256: str | None,
    runner: dict,
) -> None:
    lock = {
        "alias": alias,
        "version": version,
        "installed_at": datetime.now(UTC).isoformat(),
        "source": source,
        "bundle_sha256": bundle_sha256,
        "runner": runner,
    }
    (target_dir / "runner.lock.json").write_text(json.dumps(lock, indent=2), encoding="utf-8")


def _download(url: str) -> Path:
    tmpf = Path(tempfile.mkstemp(prefix="mcpb-download-", suffix=".zip")[1])
    with httpx.stream("GET", url, timeout=60) as r:
        r.raise_for_status()
        with open(tmpf, "wb") as out:
            for chunk in r.iter_bytes():
                out.write(chunk)
    return tmpf


def _maybe_fetch_remote_digest(url: str) -> str | None:
    # Best-effort: try <url>.sha256
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url + ".sha256")
            if resp.status_code == 200:
                text = resp.text.strip()
                if len(text) == 64 and all(c in "0123456789abcdefABCDEF" for c in text):
                    return text.lower()
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def install_command(
    source: str,
    alias: str,
    *,
    verify: bool = True,
    probe: bool = True,
    timeout: int = 10,
) -> InstallResult:
    """Install from a source spec into ~/.matrix/runners.

    Parameters
    ----------
    source: str
        Path/URL to a zip, or a local directory. (P1 supports zip/dir only.)
    alias: str
        Installer alias under ~/.matrix/runners/<alias>/.
    verify: bool
        If True, verify sha256 when available (local .sha256 or <url>.sha256).
    probe: bool
        If True, run a short smoke probe after installation.
    timeout: int
        Seconds to wait for the smoke probe.
    """
    surf: Surface = resolve_surface(source)

    staging_root = Path(tempfile.mkdtemp(prefix="mcpb-install-"))
    bundle_sha: str | None = None

    try:
        if surf.kind == "zip":
            # Obtain the zip locally
            if "path" in surf.spec:
                zip_path = Path(surf.spec["path"]).resolve()
                if verify:
                    # Use sibling .sha256 if present
                    sidecar = Path(str(zip_path) + ".sha256")
                    if sidecar.exists():
                        verify_sha256(
                            zip_path, expected=sidecar.read_text(encoding="utf-8").strip()
                        )
                bundle_sha = sha256(zip_path)
            else:
                url = surf.spec["url"]
                zip_path = _download(url)
                if verify:
                    expected = _maybe_fetch_remote_digest(url)
                    if expected:
                        verify_sha256(zip_path, expected=expected)
                bundle_sha = sha256(zip_path)

            # Extract and load metadata
            safe_extract_zip(zip_path, staging_root)
            runner, manifest = _synthesize_if_missing(staging_root, alias)

        elif surf.kind == "dir":
            src_dir = Path(surf.spec["path"]).resolve()
            if not src_dir.is_dir():
                raise FileNotFoundError(src_dir)
            # Copy tree then synthesize if needed
            shutil.copytree(src_dir, staging_root, dirs_exist_ok=True)
            runner, manifest = _synthesize_if_missing(staging_root, alias)

        else:
            raise ValueError(f"Unsupported surface in P1: {surf.kind}")

        version = (manifest or {}).get("version") or "0.0.0"
        final_dir = _final_path(alias, version)
        final_dir.parent.mkdir(parents=True, exist_ok=True)

        # Atomic move into place
        _atomic_rename(staging_root, final_dir)

        # Optional probe (launch quickly and ensure process stays alive)
        if probe:
            smoke_run(str(final_dir), run_only=False, timeout=timeout)

        # Write lock metadata
        _write_lock(
            final_dir,
            alias=alias,
            version=version,
            source=source,
            bundle_sha256=bundle_sha,
            runner=runner or {},
        )

        return InstallResult(alias=alias, version=version, path=final_dir)

    except Exception:
        # Cleanup staging on error
        try:
            if staging_root.exists():
                shutil.rmtree(staging_root, ignore_errors=True)
        finally:
            raise
