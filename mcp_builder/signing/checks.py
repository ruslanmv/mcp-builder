"""Integrity helpers (P2): SHA-256 compute & verify.

Cosign/provenance hooks can be added here later without changing callers.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    """Return the hex SHA-256 of *path*."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _normalize_expected(expected: str) -> str:
    exp = expected.strip()
    if exp.startswith("sha256:"):
        exp = exp.split(":", 1)[1]
    return exp.lower()


def verify_sha256(path: Path, expected: str) -> None:
    """Raise ValueError if *path*'s sha256 does not match *expected*.

    *expected* may be either plain hex or `sha256:<hex>`.
    """
    got = sha256(path)
    exp = _normalize_expected(expected)
    if got.lower() != exp:
        raise ValueError(f"SHA-256 mismatch: got {got}, expected {exp}")
