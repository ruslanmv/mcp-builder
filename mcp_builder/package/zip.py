"""Zip packaging utilities (P0).

Creates a normalized zip archive that contains:
- provided server files
- runner.json
- mcp.server.json

Also writes a sibling `.sha256` file with the archive's SHA-256 hex digest.

Design goals:
- Stable, deterministic-ish ordering (sort entries) for reproducibility.
- No directory traversal issues; only relative arcnames.
- Small, dependency-free implementation suitable for CI use.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from collections.abc import Iterable
from pathlib import Path


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _as_rel_arcname(root: Path, path: Path) -> str:
    """Return a safe, relative arcname for a file under root.

    We normalize to forward slashes and prevent absolute paths.
    """
    path = path.resolve()
    root = root.resolve()
    rel = path.relative_to(root)
    return str(rel).replace("\\", "/")


def make_zip_bundle(
    outdir: Path,
    files: Iterable[Path],
    runner: dict,
    mcp_manifest: dict,
    bundle_name: str | None = None,
) -> Path:
    """Create a zip bundle and a matching .sha256 file.

    Parameters
    ----------
    outdir: Path
        Destination directory (created if missing).
    files: Iterable[Path]
        Files to include at the archive root.
    runner: dict
        JSON-serializable runner spec to write as `runner.json`.
    mcp_manifest: dict
        JSON-serializable MCP bundle manifest to write as `mcp.server.json`.
    bundle_name: str | None
        Filename (without extension). Defaults to `bundle`.

    Returns
    -------
    Path
        Full path to the created zip file.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    name = (bundle_name or "bundle").rstrip(".zip")
    zip_path = outdir / f"{name}.zip"

    # Write zip with sorted arcnames for stable output
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        root = Path.cwd()
        # Add user files
        unique_files = sorted({Path(p).resolve() for p in files})
        for fp in unique_files:
            if not fp.is_file():
                continue
            z.write(fp, arcname=fp.name)
        # Add metadata files
        z.writestr("runner.json", json.dumps(runner, indent=2))
        z.writestr("mcp.server.json", json.dumps(mcp_manifest, indent=2))

    # Compute and persist sha256 sidecar
    digest = _sha256_bytes(zip_path.read_bytes())
    (zip_path.with_suffix(".zip.sha256")).write_text(digest, encoding="utf-8")
    return zip_path
