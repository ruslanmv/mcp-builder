# 🔧 mcp-builder

> Build, package, install, and validate **MCP servers** locally — with **Matrix Hub**–compatible bundles and install plans.

<p align="center">
  <img src="https://placehold.co/480x140/1e293b/ffffff?text=mcp-builder" alt="mcp-builder logo" width="420">
</p>

<p align="center">
  <a href="https://pypi.org/project/mcp-builder/"><img alt="PyPI" src="https://img.shields.io/pypi/v/mcp-builder.svg?label=PyPI&color=4c1"></a>
  <a href="https://github.com/ruslanmv/mcp-builder/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/ruslanmv/mcp-builder/ci.yml?branch=main"></a>
  <a href="https://ruslanmv.github.io/mcp-builder/"><img alt="Docs" src="https://img.shields.io/badge/docs-mkdocs%20material-2962ff"></a>
  <a href="https://github.com/agent-matrix/matrix-hub"><img alt="Matrix Hub" src="https://img.shields.io/badge/compatible%20with-matrix--hub-brightgreen"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
</p>

---

## ✨ What is it?

`mcp-builder` turns a source repo (Python/Node today) into a **verifiable** bundle:

* **Detects** language + transport (SSE / STDIO)
* **Scaffolds** `runner.json` + `mcp.server.json`
* **Packages** to a normalized **zip** + **SHA-256**
* **Emits** a Matrix Hub–compatible **install plan**
* **Installs** locally to `~/.matrix/runners/<alias>/<version>/`
* **Probes** startup (smoke test), with optional port/env overrides

It’s designed to scale: convention-over-configuration, typed validation, and CI-friendly.

---

## 🚀 Quickstart

> Requires **Python 3.11+**. For Node servers, install Node 18+.

```bash
# 0) Install the CLI
pip install mcp-builder

# 1) Detect
mcp-builder detect ./fixtures/hello-python-sse

# 2) Scaffold metadata (if missing)
mcp-builder init ./fixtures/hello-python-sse --transport sse --name hello --version 0.1.0

# 3) Build metadata (zip creation handled by pipeline/package step)
mcp-builder build ./fixtures/hello-python-sse --out ./dist

# 4) Package to zip (+sha256) using the packaging API in your pipeline
#    ... dist/bundle.zip and dist/bundle.zip.sha256

# 5) Emit an install plan for Matrix Hub
mcp-builder plan ./dist/bundle.zip --name hello --transport SSE --out ./dist/hello.plan.json

# 6) Install locally (with a smoke probe)
mcp-builder install ./dist/bundle.zip --as hello-sse --port 8023 --env LOG_LEVEL=debug

# 7) Run on demand
mcp-builder run ~/.matrix/runners/hello-sse/0.1.0 --port 8023
```

**Handy flags**

* `--port N` — sets `PORT` during probe/run (SSE)
* `--env KEY=VAL` — repeatable env for probe/run
* `--no-probe` — skip the post-install smoke test
* `--prefer docker|zip|git` — future multi-surface preference

---

## 🧰 CLI overview

| Command   | What it does                                                      |
| --------- | ----------------------------------------------------------------- |
| `detect`  | Detects language/transport/entry; prints JSON                     |
| `init`    | Scaffolds `runner.json` + `mcp.server.json`                       |
| `build`   | Produces metadata & file list for packaging                       |
| `plan`    | Emits a Matrix Hub–compatible install plan from a bundle          |
| `install` | Installs a bundle/dir into `~/.matrix/runners/<alias>/<version>/` |
| `run`     | Smoke-runs a bundle/dir; supports `--port` and `--env KEY=VAL`    |
| `verify`  | Verifies a bundle against a SHA-256 (`sha256:<hex>` or raw hex)   |

---

## 🧪 Tests & examples

* **Fixtures**: `fixtures/hello-python-sse/` — a minimal SSE server
* **Unit tests**: detectors, validator, zip safety
* **Integration tests**: build → plan shape → install zip

Run everything:

```bash
make venv
. .venv/bin/activate
make test          # lint + unit + integration
make docs-serve    # local docs at http://127.0.0.1:8001
```

---

## 🧱 Architecture (P0–P3)

* **Detect**: `mcp_builder/detect/*` → `DetectReport(lang, transport, entrypoints, …)`
* **Buildpacks**: `buildpacks/python.py`, `buildpacks/node.py` → runner + manifest + files
* **Package**: `package/zip.py` → `bundle.zip` + `.sha256`
* **Validate**: `schema/*.json`, `validator.py` (permissive, tightened later)
* **Plan**: `planner.py` → `install plan` JSON
* **Install**: `installer/install.py` (zip/dir), safe extraction, lock metadata
* **Run/Probe**: `conformance/runner.py` (smoke), `conformance/testspec.py` (basic tests)
* **Integrity**: `signing/checks.py` (sha256 now; cosign later)

---

## 🧭 When to use MCP (and when not to)

**Best fits**: exposing executable capabilities (tools) to AI apps — DB queries, filesystem ops, API calls, workflows.
**Also fits**: read-only resources (files/URLs/DB rows) & reusable prompts/templates.
**Use MCP when**: you need standardized integration, security/permissioning, model-agnostic interop, and observability across clients.
**Don’t use MCP when**: a simple HTTP API/Webhook suffices and model-facing semantics aren’t needed.

---

## 🧑‍🎨 Designing great MCP servers

**Core principles**

* Single responsibility (one auth domain, cohesive feature set)
* Statelessness (replayable; horizontally scalable)
* Explicit contracts (strict JSON Schemas, min/max/enum/pattern)
* Least privilege (read-only default, granular permissions)
* Idempotency & safety (confirm destructive ops)
* Observability first (structured logs, metrics, traces, request IDs)
* Failure-tolerant (timeouts, retries, circuit breakers, cancellation)

**Transports**

* **STDIO**: simplest for local dev/trusted envs
* **HTTP (SSE)**: default for browsers/remote clients; supports streaming & CORS
* **WebSocket**: bidirectional, if you control both ends

**Security checklist**

* Read-only default; explicit write gates
* FS/egress allowlists; sanitize URIs
* AuthN/AuthZ (scopes, rotation), secrets redaction
* Quotas & rate limits; audit logs

**Observability & reliability**

* Metrics: latency, error rate, concurrency, bytes in/out
* Logs: structured JSON with correlation/request IDs
* Tracing: spans across external calls
* Resilience: timeouts, backoff, health/liveness probes

---

## 🧪 Testing strategy

* **Unit**: schema validation, input validators, error mappers
* **Integration**: spin up server; `tools/list`, resource reads, tool calls
* **Protocol**: MCP flows (listing, calling, streaming, cancellation)
* **Performance**: load hot paths; watch tail latencies
* **Model-compat**: exercise across multiple model clients

---

## 🧯 Troubleshooting

* **Editable install fails** with `TypeError: Field project.dependencies must be an array`
  → In `pyproject.toml`, `project.dependencies` must be an **array of strings**, not a TOML table.

* **Zip extraction blocked**
  → The installer protects against zip-slip, absolute paths, and huge members. Rebuild your bundle with normalized relative paths only.

* **Probe timeout**
  → Increase `--timeout`, set a deterministic `--port`, or run with `--no-probe` in CI and test separately.

---

## 🛣️ Roadmap

* P4: **Docker** surface (`docker-image-ref.txt` then actual buildx flow)
* P4: **Schema tightening** (`additionalProperties: false` where safe)
* P5: **Node SSE** detection & build; **Go/Rust** buildpacks
* Supply chain: **SBOM**, **SLSA provenance**, **cosign** signatures
* Conformance: full **handshake** + **tool call** contract tests
* Multi-surface plans: zip / PyPI / npm / Docker / client configs

---

## 🧪 Industrialized blueprint (for many servers & surfaces)

**Guiding principles**

* Convention over config
* One source → many surfaces (zip, PyPI/npm, Docker, OS packages, client configs)
* Reproducible & verifiable (pinned toolchains, SBOM, provenance, signatures)
* Gated releases (conformance/security/perf)

**Canonical `mcp.server.json` (embed in every bundle)**

```json
{
  "schemaVersion": "1.0",
  "name": "hello-mcp",
  "version": "0.2.0",
  "transports": [
    {"type": "stdio", "command": ["python","-m","hello_mcp.server_stdio"]},
    {"type": "sse",   "url": "http://127.0.0.1:8000/messages/", "health": "/healthz"}
  ],
  "tools": ["hello"],
  "limits": {"maxInputKB":128,"maxOutputKB":256,"timeoutMs":15000},
  "security": {
    "readOnlyDefault": true,
    "fsAllowlist": ["${PROJECT_ROOT}/data/**"],
    "egressAllowlist": ["api.github.com:443"]
  },
  "build": {"lang":"python","runner":"uv","lockfiles":["uv.lock"]},
  "digest": {"algo":"sha256","value":"<filled by CI>"}
}
```

**Multi-surface outputs from one build**

* Zip (+ `mcp.server.json`, `runner.json`, SHA-256, signature, SBOM, provenance)
* PyPI/npm (console-script/bin → `uvx`/`npx` installs)
* Docker (SSE preferred, non-root, healthcheck)
* Client configs (VS Code / Claude Desktop snippets)
* OS packages (brew/scoop/winget) – optional

**Conformance & security gates (practical minimum)**

* Protocol: list/call/cancel/stream
* Schemas: strict JSON Schema validation
* Security: read-only default + allowlists
* Perf smoke: concurrent calls within p95 budgets
* Logging: JSON logs include tool, durationMs, status, requestId

---

## 🛠 Development

```bash
# Create a local environment and install dev/docs extras
make venv
. .venv/bin/activate

# Quality gates & tests
make lint
make fmt
make unit
make integration
make test

# Docs
make docs-serve   # live
make docs-build   # static site in ./site

# Package for PyPI
make build
```

---

## 📜 License

Licensed under the **Apache 2.0** License — see [LICENSE](LICENSE).

---

## 🙋 FAQ

**Is this only for Python?**
No. Python is first-class today; Node stdio is included; more languages (Go/Rust) are planned via buildpacks.

**Is it safe to install arbitrary zips?**
We verify SHA-256, block zip-slip/absolute paths, and will add signatures (cosign) + provenance in upcoming releases.

**How do I make my server “Matrix Hub ready”?**
Include `runner.json` + **canonical** `mcp.server.json`, keep tools’ schemas strict, and ensure read-only defaults + allowlists. Use `mcp-builder plan` to emit an install plan with digests.


