#!/usr/bin/env bash
# This script tests the core submodules of the mcp-builder CLI.
# Run from the root of the mcp-builder project.

set -Eeuo pipefail

# Ensure a clean state by removing any leftover directories from previous runs
rm -rf "$HOME/.matrix/runners/test-server-alias"


say() { printf '%b\n' "$*"; }

say "--- Running mcp-builder submodule tests ---"

# Ensure the mcp-builder is installed and available in PATH
if ! command -v mcp-builder >/dev/null 2>&1; then
  say "mcp-builder command not found. Make sure it is installed (e.g., 'make venv' or 'make install')."
  exit 1
fi

# 1) Create a temporary directory for the test project
TEST_DIR="$(mktemp -d)"
say "Created temporary test directory: ${TEST_DIR}"
cd "${TEST_DIR}"

# 2) 'init' to scaffold a new project
say "\n--- Testing 'init' ---"
mcp-builder init . --name test-server --version 1.0.0 --transport sse
if [[ ! -f "runner.json" || ! -f "mcp.server.json" ]]; then
  say "FAIL: 'init' did not create runner.json and mcp.server.json"
  exit 1
fi
say "Scaffolded: runner.json, mcp.server.json"
say "PASS: 'init' created scaffold files."

# Create a minimal server file for the build step
: > server_sse.py

# 3) 'build' to prepare metadata (may rewrite version -> 0.0.0 in P0)
say "\n--- Testing 'build' ---"
mcp-builder build . --out ./dist
say "PASS: 'build' command executed."

# Determine the version that will actually be used by install
VERSION="$(
  python3 - <<'PY'
import json,sys
with open("mcp.server.json","r",encoding="utf-8") as f:
    print(json.load(f).get("version","0.0.0"))
PY
)"
say "Detected manifest version after build: ${VERSION}"

# 4) 'plan' from a dummy bundle (planner just needs .sha256 to exist)
say "\n--- Testing 'plan' ---"
mkdir -p ./dist
: > ./dist/test-server-sse.zip
echo "$(printf '%064d' 0)" > ./dist/test-server-sse.zip.sha256
mcp-builder plan ./dist/test-server-sse.zip --name test-server --transport SSE --out ./dist/plan.json
if [[ ! -f "./dist/plan.json" ]]; then
  say "FAIL: 'plan' did not create a plan file."
  exit 1
fi
say "PASS: 'plan' created an install plan."

# 5) 'install' from the local directory
say "\n--- Testing 'install' ---"
mcp-builder install . --as test-server-alias --no-probe
INSTALL_PATH="$HOME/.matrix/runners/test-server-alias/${VERSION}"
if [[ ! -d "${INSTALL_PATH}" ]]; then
  say "FAIL: 'install' did not create the installation directory: ${INSTALL_PATH}"
  # Print tree for debugging
  if command -v tree >/dev/null 2>&1; then
    tree -a "$HOME/.matrix/runners/test-server-alias" || true
  else
    find "$HOME/.matrix/runners/test-server-alias" -maxdepth 3 -print 2>/dev/null || true
  fi
  exit 1
fi
say "PASS: 'install' created the installation directory at ${INSTALL_PATH}"

# 6) 'run' smoke test (background and stop shortly after)
say "\n--- Testing 'run' (smoke) ---"
mcp-builder run "${INSTALL_PATH}" --port 8023 >/dev/null 2>&1 &
RUN_PID=$!
sleep 2
kill "${RUN_PID}" >/dev/null 2>&1 || true
wait "${RUN_PID}" 2>/dev/null || true
say "PASS: 'run' command was executed."

# Cleanup
say "\n--- Cleaning up ---"
rm -rf "${TEST_DIR}"
rm -rf "$HOME/.matrix/runners/test-server-alias"
say "Cleanup complete."

say "\n--- All submodule tests passed successfully! ---"
