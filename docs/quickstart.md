# Quickstart

## Prereqs
- Python 3.11+
- (Optional) Node 18+ for Node servers

## Hello (Python SSE)
```bash
mcp-builder detect ./fixtures/hello-python-sse
mcp-builder init    ./fixtures/hello-python-sse --transport sse --name hello --version 0.1.0
# Build metadata
mcp-builder build   ./fixtures/hello-python-sse --out ./dist
# Package → bundle.zip (via pipeline)
# Plan
mcp-builder plan    ./dist/bundle.zip --name hello --transport SSE --out ./dist/hello.plan.json
# Install & run
mcp-builder install ./dist/bundle.zip --as hello-sse --port 8023 --env LOG_LEVEL=debug
mcp-builder run     ~/.matrix/runners/hello-sse/0.1.0 --port 8023
```
## Flags you’ll use a lot
- `--port` to bind SSE servers deterministically
- `--env KEY=VAL` to pass API keys or config
- `--no-probe` to skip post-install probe (CI speed-ups)
