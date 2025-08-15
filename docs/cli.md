# CLI Reference

```text
Usage: mcp-builder [OPTIONS] COMMAND [ARGS]...

Commands:
  detect   Detect language/transport/entry and print JSON
  init     Scaffold runner.json and mcp.server.json
  build    Build metadata (runner/manifest) and prepare for packaging
  plan     Emit a Matrix Hub–compatible install plan from a bundle
  install  Install a bundle or directory into ~/.matrix/runners
  run      Run from bundle/dir with optional env & port
  verify   Verify sha256 of a bundle
```
## Options
- `--prefer docker|zip|git` – preferred surface (forward-compat).
- `--no-probe` – skip post-install probe.
- `--env KEY=VAL` – repeatable environment variables.
- `--port N` – set PORT during probe/run (SSE).
