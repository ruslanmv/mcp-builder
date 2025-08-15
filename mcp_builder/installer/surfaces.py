"""Surface resolver (P1+P3): add git parsing.

New: parse `https://…git@ref` into {kind: "git", spec: {repo, ref}}.
Examples:
- https://github.com/org/repo.git@v1.2.3
- https://gitlab.com/org/repo.git@main
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class Surface:
    kind: str  # "zip" | "plan" | "dir" | "git" (P3) | future: "oci"|"pypi"|"npm"
    spec: dict


def _looks_like_url(s: str) -> bool:
    try:
        u = urlparse(s)
        return u.scheme in {"http", "https", "file"} and bool(u.netloc or u.scheme == "file")
    except Exception:
        return False


def _parse_git(source: str) -> Surface | None:
    if source.startswith("http") and ".git" in source:
        if "@" in source:
            repo, ref = source.rsplit("@", 1)
        else:
            repo, ref = source, "HEAD"
        return Surface("git", {"repo": repo, "ref": ref})
    return None


def resolve_surface(source: str) -> Surface:
    # Git (P3)
    g = _parse_git(source)
    if g:
        return g

    # URL cases
    if _looks_like_url(source):
        s = source.lower()
        if s.endswith(".zip"):
            return Surface("zip", {"url": source})
        if s.endswith(".json"):
            return Surface("plan", {"url": source})

    # Local filesystem
    p = Path(source)
    if p.is_file() and p.suffix.lower() == ".zip":
        return Surface("zip", {"path": str(p.resolve())})
    if p.is_file() and p.suffix.lower() == ".json":
        return Surface("plan", {"path": str(p.resolve())})
    if p.exists() and p.is_dir():
        return Surface("dir", {"path": str(p.resolve())})

    # Fallback
    return Surface("dir", {"path": str(p.resolve())})
