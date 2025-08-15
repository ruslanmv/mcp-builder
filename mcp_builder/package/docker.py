"""Docker packaging (P4): SSE image builder (stub).

Goal: build a minimal, non-root image with a healthcheck and emit a reference
file `docker-image-ref.txt` in the dist directory. The actual Docker build
steps will be filled in later to avoid introducing a hard dependency in P3.
"""

from __future__ import annotations

from pathlib import Path


def build_sse_image(outdir: Path, name: str, version: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    ref = f"{name}:{version}"
    ref_file = outdir / "docker-image-ref.txt"
    ref_file.write_text(ref, encoding="utf-8")
    return ref_file
