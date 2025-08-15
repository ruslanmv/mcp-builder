"""Detection API and dispatcher (P0).

This module defines the typed contract for detectors and a simple dispatcher that
tries Python detection first (additional detectors are added in later phases).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel


class DetectReport(BaseModel):
    """Normalized detection result.

    Attributes
    ----------
    score: float
        Confidence (0..1). Higher is better.
    lang: str | None
        Primary language (e.g., "python", "node").
    transport: str | None
        "sse" | "stdio" when known.
    entrypoints: list[str]
        Candidate entry files (relative paths).
    tools: list[dict]
        Optional early tool hints (name/desc/schema) if parsable in P0.
    notes: list[str]
        Free-form observations from detectors.
    """

    score: float = 0.0
    lang: str | None = None
    transport: str | None = None
    entrypoints: list[str] = []
    tools: list[dict] = []
    notes: list[str] = []


class Detector(Protocol):
    def detect(self, root: Path) -> DetectReport: ...


def detect_project(root: Path) -> DetectReport:
    """Run available detectors (Python first) and return the best report.

    For P0, we only run the Python detector. Future phases add Node/Go/Rust and
    merge logic with scoring.
    """
    from .python_ast import detect as detect_python

    report = detect_python(root)
    # Ensure reasonable defaults to keep downstream code simple in P0
    if not report.entrypoints:
        if report.transport == "sse" and (root / "server_sse.py").exists():
            report.entrypoints = ["server_sse.py"]
        elif (root / "server.py").exists():
            report.entrypoints = ["server.py"]
    return report
