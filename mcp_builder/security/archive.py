"""Safe archive extraction helpers (P1).

Guards against common archive attacks:
- Zip Slip (../ traversal)
- Absolute paths
- Symlink escapes (best-effort on unzip)
- Oversized files (basic cap)
"""

from __future__ import annotations

import os
import stat
import zipfile
from pathlib import Path

MAX_MEMBER_BYTES = 128 * 1024 * 1024  # 128 MiB per member (adjust as needed)


def _is_within(base: Path, target: Path) -> bool:
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False


def safe_extract_zip(zip_path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for m in z.infolist():
            fn = Path(m.filename)
            # Skip directories explicitly; create them implicitly as needed
            if fn.name in {"", "."} or m.is_dir():
                continue
            # Disallow absolute paths and traversal
            if fn.is_absolute() or ".." in fn.parts:
                raise RuntimeError(f"Unsafe member path: {m.filename}")
            # Materialize target path and ensure containment
            target = (dest / fn).resolve()
            if not _is_within(dest.resolve(), target):
                raise RuntimeError(f"Member escapes destination: {m.filename}")
            # Size guard
            if m.file_size > MAX_MEMBER_BYTES:
                raise RuntimeError(f"Member too large: {m.filename} ({m.file_size} bytes)")
            # Extract
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(m) as src, open(target, "wb") as out:
                out.write(src.read())
            # Best-effort: normalize perms (strip setuid/setgid)
            try:
                mode = stat.S_IMODE(m.external_attr >> 16)
                os.chmod(target, mode & ~stat.S_ISUID & ~stat.S_ISGID)
            except Exception:
                pass
