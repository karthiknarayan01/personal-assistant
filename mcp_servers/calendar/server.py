"""MCP server exposing read-only Google Calendar access as an MCP tool.

The orchestrator spawns this automatically over stdio via MCPToolset (see
orchestrator/agent.py) — there's no separate process to start by hand.
For standalone testing, run:

    python3 -m mcp_servers.calendar.server
"""

import asyncio
import json
import os

import mcp.server.stdio
from dotenv import load_dotenv
from mcp import types as mcp_types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

from .tool import list_calendar_events

# Falls back to loading the shared .env directly, in case this is ever run
# standalone rather than spawned by the orchestrator (which already has it
# loaded and passes its environment through to this subprocess).
load_dotenv(
    os.path.join(os.path.dirname(__file__), "..", "..", "orchestrator", ".env")
)

_adk_tool = FunctionTool(list_calendar_events)
app = Server("calendar-mcp-server")


@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [adk_to_mcp_tool_type(_adk_tool)]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    if name != _adk_tool.name:
        result = {
            "status": "error",
            "error_message": f"Unknown tool '{name}'.",
        }
    else:
        try:
            result = await _adk_tool.run_async(args=arguments, tool_context=None)
        except Exception:
            # Defense in depth: tool.py already sanitizes its own errors,
            # but nothing that reaches an MCP client should ever include
            # raw exception text, file paths, or credential details.
            result = {
                "status": "error",
                "error_message": "An unexpected error occurred while running the calendar tool.",
            }
    return [mcp_types.TextContent(type="text", text=json.dumps(result))]


async def _run_stdio() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=app.name,
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(_run_stdio())
