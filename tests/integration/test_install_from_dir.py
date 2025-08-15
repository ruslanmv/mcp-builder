from __future__ import annotations

from pathlib import Path

import pytest

# Import the module so we can monkeypatch RUNNERS_HOME
from mcp_builder.installer import install as inst_mod


def _write_minimal_sse_source(root: Path) -> None:
    """Create the smallest viable SSE server tree for detection to succeed."""
    root.mkdir(parents=True, exist_ok=True)
    # No runner/manifest on purpose: installer should synthesize them
    (root / "server_sse.py").write_text(
        "if __name__ == '__main__':\n" "    print('hello-sse')\n",
        encoding="utf-8",
    )


@pytest.mark.timeout(20)
def test_install_from_dir_idempotent(tmp_path, monkeypatch):
    """
    Install from a local directory:
      - synthesizes runner/manifest when missing
      - installs to ~/.matrix/runners/<alias>/<version>/
      - is idempotent (second install = success, no overwrite)
      - --force overwrites the existing install
    """
    # Redirect installs to a temp runners home (never touch the real ~/.matrix)
    runners_home = tmp_path / ".matrix" / "runners"
    monkeypatch.setattr(inst_mod, "RUNNERS_HOME", runners_home, raising=True)

    # Minimal SSE source (no manifest/runner to exercise synthesis)
    src = tmp_path / "src"
    _write_minimal_sse_source(src)

    # 1) First install (no probe, no verify)
    res1 = inst_mod.install_command(str(src), alias="hello", verify=False, probe=False, timeout=3)
    assert res1.alias == "hello"
    # Version defaults to 0.0.0 in P1 synthesis
    expected = runners_home / "hello" / (res1.version or "0.0.0")
    assert res1.path == expected
    assert expected.exists()
    assert (expected / "runner.lock.json").exists()
    # Synthesized files should be present after install
    assert (expected / "runner.json").exists()
    assert (expected / "mcp.server.json").exists()

    # 2) Second install (idempotent path) should NOT fail and keep files
    res2 = inst_mod.install_command(str(src), alias="hello", verify=False, probe=False, timeout=3)
    assert res2.path == expected
    assert expected.exists()
    # Leave a marker to detect overwrite behavior
    marker = expected / "marker.txt"
    marker.write_text("old", encoding="utf-8")

    # 3) Forced reinstall should replace the directory (marker disappears)
    res3 = inst_mod.install_command(
        str(src), alias="hello", verify=False, probe=False, timeout=3, force=True
    )
    assert res3.path == expected
    assert expected.exists()
    assert not marker.exists()  # overwritten


@pytest.mark.timeout(20)
def test_cli_install_from_dir(tmp_path, monkeypatch):
    """
    Smoke test the Typer CLI for 'install' using a temp runners home.
    """
    # Redirect runner home used by the installer
    runners_home = tmp_path / ".matrix" / "runners"
    monkeypatch.setattr(inst_mod, "RUNNERS_HOME", runners_home, raising=True)

    # Prepare minimal source
    src = tmp_path / "src"
    _write_minimal_sse_source(src)

    # Import CLI only after monkeypatch so everything lines up
    from typer.testing import CliRunner

    from mcp_builder.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["install", str(src), "--as", "hello-cli", "--no-probe"])
    assert result.exit_code == 0, result.output

    installed = runners_home / "hello-cli" / "0.0.0"
    assert installed.exists()
    assert (installed / "runner.lock.json").exists()
