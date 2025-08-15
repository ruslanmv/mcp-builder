"""Python environment prep (stub for P2).

In P2 this will:
- create an isolated venv under the install root
- install requirements via `uv sync` if `uv.lock` exists, else `pip install -r requirements.txt`
- optionally freeze exact wheels and hashes for reproducibility
"""

from __future__ import annotations

from pathlib import Path


def prepare_python_env(root: Path) -> None:
    """Stub: no-op in P1.

    Parameters
    ----------
    root: Path
        Installation root where the environment would be created in P2.
    """
    _ = root  # placeholder to keep signature stable
    return None
