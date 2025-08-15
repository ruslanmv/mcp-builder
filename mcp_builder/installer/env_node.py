"""Node environment preparation (P3 MVP).

Creates an isolated Node env within the install root by running a frozen
lockfile install via `pnpm` (preferred) or `npm ci`.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _has(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def prepare_node_env(root: Path) -> None:
    pkg = root / "package.json"
    if not pkg.exists():
        return  # nothing to do

    # Prefer pnpm when lockfile exists and pnpm is installed
    if (root / "pnpm-lock.yaml").exists() and _has("pnpm"):
        subprocess.run(["pnpm", "i", "--frozen-lockfile"], cwd=root, check=True)
        return

    # Fallback to npm ci when package-lock.json exists
    if (root / "package-lock.json").exists() and _has("npm"):
        subprocess.run(["npm", "ci"], cwd=root, check=True)
        return

    # Last resort: npm install (not frozen, discouraged but acceptable in P3)
    if _has("npm"):
        subprocess.run(["npm", "install"], cwd=root, check=True)
