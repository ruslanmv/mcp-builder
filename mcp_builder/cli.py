"""mcp-builder CLI — polished flags for install/run (P3/P4 ready).

Additions:
- --prefer [docker|zip|git] (reserved for future surfaces)
- --no-probe (skip post-install smoke probe)
- --env KEY=VAL (repeatable)
- --port N (inject PORT for run/probe)
- --force (overwrite existing installation if present)
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from mcp_builder.buildpacks.python import build as build_python
from mcp_builder.conformance.runner import smoke_run
from mcp_builder.detect.base import detect_project
from mcp_builder.installer.install import install_command
from mcp_builder.planner import emit_install_plan

app = typer.Typer(add_completion=False, help="Build and package MCP servers")
console = Console()


@app.command()
def detect(path: str = typer.Argument(".", help="Path to a source directory")) -> None:
    report = detect_project(Path(path))
    rprint(report.model_dump_json(indent=2))


@app.command()
def init(
    path: str = typer.Argument(".", help="Path to project root"),
    transport: str = typer.Option("auto", help='"sse" | "stdio" | "auto"'),
    name: str = typer.Option("unnamed", help="Server name for scaffolds"),
    version: str = typer.Option("0.0.0", help="Server version for scaffolds"),
) -> None:

    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    report = detect_project(root)

    inferred_transport = report.transport or ("sse" if transport == "auto" else transport)
    if transport in {"sse", "stdio"}:
        inferred_transport = transport

    entry = (report.entrypoints[0] if report.entrypoints else None) or (
        "server_sse.py" if inferred_transport == "sse" else "server.py"
    )
    runner = {
        "type": inferred_transport,
        "command": ["python", entry],
        "url": "http://127.0.0.1:8000/messages/" if inferred_transport == "sse" else None,
        "env": {},
        "limits": {"timeoutMs": 15000, "maxInputKB": 128, "maxOutputKB": 256},
        "security": {"readOnlyDefault": True, "fsAllowlist": [], "egressAllowlist": []},
    }
    manifest = {
        "schemaVersion": "1.0",
        "name": name,
        "version": version,
        "transports": [{"type": inferred_transport, "url": runner.get("url")}],
        "tools": [],
        "limits": runner["limits"],
        "security": runner["security"],
        "build": {"lang": report.lang or "python", "runner": "unknown"},
    }

    (root / "runner.json").write_text(json.dumps(runner, indent=2), encoding="utf-8")
    (root / "mcp.server.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    rprint("[green]Scaffolded:[/green] runner.json, mcp.server.json")


@app.command()
def build(
    path: str = typer.Argument(".", help="Path to project root"),
    out: str = typer.Option("./dist", help="Output directory for artifacts"),
) -> None:
    root = Path(path)
    outdir = Path(out)
    outdir.mkdir(parents=True, exist_ok=True)

    report = detect_project(root)
    if report.lang != "python":
        rprint("[yellow]P0 supports Python only — detected[/yellow]", report.lang)

    result = build_python(ctx=None, info=report)

    (root / "runner.json").write_text(json.dumps(result.runner, indent=2), encoding="utf-8")
    (root / "mcp.server.json").write_text(
        json.dumps(result.mcp_manifest, indent=2), encoding="utf-8"
    )

    table = Table(title="Build Summary (P0)")
    table.add_column("File", style="cyan")
    for f in result.files:
        table.add_row(str(f))
    table.add_row("runner.json")
    table.add_row("mcp.server.json")
    console.print(table)
    rprint("[green]Build metadata written. Use packaging to zip & plan.[/green]")


@app.command()
def plan(
    bundle: str = typer.Argument(..., help="Path to the zip bundle"),
    name: str = typer.Option("unnamed", help="Server name (plan id & registration)"),
    transport: str = typer.Option("SSE", help='Transport string for registration ("SSE"/"STDIO")'),
    out: str | None = typer.Option(None, "--out", help="Write to file instead of stdout"),
) -> None:
    payload = emit_install_plan(Path(bundle), name=name, transport=transport)
    if out:
        Path(out).write_text(payload, encoding="utf-8")
        rprint(f"[green]Plan written:[/green] {out}")
    else:
        print(payload)


@app.command()
def run(
    target: str = typer.Argument(..., help="Path to bundle/dir or alias (dir)"),
    port: int = typer.Option(0, "--port", help="PORT to export for SSE servers"),
    env: list[str] | None = typer.Option(
        None, "--env", help="KEY=VAL env vars", show_default=False
    ),
) -> None:
    smoke_run(target, run_only=True, port=port, extra_env=env or [])


@app.command()
def install(
    source: str = typer.Argument(..., help="zip URL/path or directory"),
    as_: str = typer.Option(..., "--as", help="Alias for installation"),
    prefer: str | None = typer.Option(
        None, "--prefer", help="Preferred surface (docker|zip|git)"
    ),
    no_probe: bool = typer.Option(False, "--no-probe", help="Skip post-install smoke probe"),
    port: int = typer.Option(0, "--port", help="PORT to export during probe"),
    env: list[str] | None = typer.Option(
        None, "--env", help="KEY=VAL env vars for probe", show_default=False
    ),
    timeout: int = typer.Option(10, "--timeout", help="Probe timeout seconds"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing installation if present"),
) -> None:
    # Note: current install_command signature doesn't consume prefer/env/port.
    # We perform probe via install_command (if enabled), and optionally run again
    # with the requested env/port for immediate feedback.
    res = install_command(
        source,
        alias=as_,
        verify=True,
        probe=not no_probe,
        timeout=timeout,
        force=force,  # NEW
    )
    rprint(f"[green]Installed:[/green] alias={res.alias} version={res.version} path={res.path}")

    if not no_probe and (port or env):
        rprint("[cyan]Re-running quick smoke with requested env/port…[/cyan]")
        smoke_run(str(res.path), run_only=False, port=port, timeout=timeout, extra_env=env or [])


@app.command()
def verify(
    bundle: str = typer.Argument(..., help="Path to zip bundle"),
    sha256: str = typer.Argument(..., help="Expected digest (hex or sha256:<hex>)"),
) -> None:
    from pathlib import Path as _P

    from mcp_builder.signing.checks import verify_sha256

    verify_sha256(_P(bundle), expected=sha256)
    rprint("[green]SHA-256 verified.[/green]")


if __name__ == "__main__":
    app()
