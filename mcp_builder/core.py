"""P0 build orchestration: detect → buildpack → zip → (schemas validated)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcp_builder.buildpacks.python import BuildResult
from mcp_builder.buildpacks.python import build as py_build
from mcp_builder.detect.base import DetectReport, detect_project
from mcp_builder.package.zip import make_zip_bundle
from mcp_builder.validator import validate_mcp_manifest, validate_runner


@dataclass
class Artifact:
    surface: str
    path: Path
    sha256: str | None = None


@dataclass
class BuildContext:
    root: Path
    surfaces: list[str]
    outdir: Path
    hermetic: bool = False


def build_pipeline(ctx: BuildContext) -> list[Artifact]:
    ctx.outdir.mkdir(parents=True, exist_ok=True)

    report: DetectReport = detect_project(ctx.root)
    if report.lang not in {"python", None}:
        # P0 only supports Python buildpack (Node/others in later phases)
        raise SystemExit(f"Unsupported language in P0: {report.lang}")

    result: BuildResult = py_build(ctx, report)

    # Validate generated metadata before packaging
    validate_runner(result.runner)
    validate_mcp_manifest(result.mcp_manifest)

    artifacts: list[Artifact] = []
    if "zip" in ctx.surfaces:
        # Bundle name: <name>-<transport> if available, else 'bundle'
        name = (result.mcp_manifest.get("name") or "bundle").replace(" ", "-")
        transport = result.runner.get("type", "sse")
        bundle_name = f"{name}-{transport}"
        zip_path = make_zip_bundle(
            ctx.outdir, result.files, result.runner, result.mcp_manifest, bundle_name=bundle_name
        )
        artifacts.append(Artifact(surface="zip", path=zip_path))

    return artifacts
