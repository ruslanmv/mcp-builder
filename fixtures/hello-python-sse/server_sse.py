"""Minimal SSE MCP server for fixtures/testing.

This app exposes a single `hello` tool over Server-Sent Events at /messages/.
It also provides a /healthz endpoint for readiness checks.
"""
from __future__ import annotations

import anyio
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from mcp.server.lowlevel import Server
from mcp.server.sse import SseServerTransport
from mcp.server.models import InitializationOptions
import mcp.types as types

server = Server("hello")
transport = SseServerTransport(endpoint="/messages/")


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="hello",
            description="Return a friendly greeting.",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "additionalProperties": False,
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "hello":
        raise ValueError("unknown tool")
    who = (arguments or {}).get("name") or "World"
    return [types.TextContent(type="text", text=f"Hello, {who}!")]


async def health(_request):
    return PlainTextResponse("ok")


app = Starlette(routes=[Route("/healthz", health)])


async def main() -> None:
    async with transport.serve_app(app) as (reader, writer):
        await server.run(
            reader,
            writer,
            InitializationOptions(
                server_name="hello-fixture",
                server_version="0.1.0",
                capabilities=server.get_capabilities(),
            ),
        )


if __name__ == "__main__":
    anyio.run(main)
