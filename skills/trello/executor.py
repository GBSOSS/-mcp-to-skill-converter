#!/usr/bin/env python3
"""
MCP Skill Executor
==================
Handles dynamic communication with the MCP server.
"""

import json
import sys
import asyncio
import argparse
from pathlib import Path
from contextlib import asynccontextmanager

# Check if mcp package is available
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamablehttp_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    print("Warning: mcp package not installed. Install with: pip install mcp", file=sys.stderr)


@asynccontextmanager
async def mcp_connection(config):
    """Context manager for MCP server connection."""
    transport_type = config.get("type", "stdio")

    if transport_type == "http":
        url = config["url"]
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    else:
        server_params = StdioServerParameters(
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env")
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


async def list_tools(session):
    """Get list of available tools."""
    response = await session.list_tools()
    return [{"name": t.name, "description": t.description} for t in response.tools]


async def describe_tool(session, tool_name: str):
    """Get detailed schema for a specific tool."""
    response = await session.list_tools()
    for tool in response.tools:
        if tool.name == tool_name:
            return {"name": tool.name, "description": tool.description, "inputSchema": tool.inputSchema}
    return None


async def call_tool(session, tool_name: str, arguments: dict):
    """Execute a tool call."""
    response = await session.call_tool(tool_name, arguments)
    return response.content


async def main():
    parser = argparse.ArgumentParser(description="MCP Skill Executor")
    parser.add_argument("--call", help="JSON tool call to execute")
    parser.add_argument("--describe", help="Get tool schema")
    parser.add_argument("--list", action="store_true", help="List all tools")

    args = parser.parse_args()

    config_path = Path(__file__).parent / "mcp-config.json"
    if not config_path.exists():
        print(f"Error: Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    if not HAS_MCP:
        print("Error: mcp package not installed. Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)

    try:
        async with mcp_connection(config) as session:
            if args.list:
                tools = await list_tools(session)
                print(json.dumps(tools, indent=2))

            elif args.describe:
                schema = await describe_tool(session, args.describe)
                if schema:
                    print(json.dumps(schema, indent=2))
                else:
                    print(f"Tool not found: {args.describe}", file=sys.stderr)
                    sys.exit(1)

            elif args.call:
                call_data = json.loads(args.call)
                result = await call_tool(session, call_data["tool"], call_data.get("arguments", {}))
                if isinstance(result, list):
                    for item in result:
                        print(item.text if hasattr(item, 'text') else json.dumps(item, indent=2))
                else:
                    print(json.dumps(result, indent=2))
            else:
                parser.print_help()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
