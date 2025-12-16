#!/usr/bin/env python3
"""
MCP to Skill Converter
======================
Converts any MCP server into a Claude Skill with dynamic tool invocation.

This implements the "progressive disclosure" pattern:
- At startup: Only skill metadata is loaded (~100 tokens)
- On use: Full tool list and instructions are loaded (~5k tokens)
- On execution: Tools are called dynamically (0 context tokens)

Usage:
    python mcp_to_skill.py --mcp-config mcp-server-config.json --output-dir ./skills/my-mcp-skill
"""

import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import argparse


class MCPSkillGenerator:
    """Generate a Skill from an MCP server configuration."""

    def __init__(self, mcp_config: Dict[str, Any], output_dir: Path):
        self.mcp_config = mcp_config
        self.output_dir = Path(output_dir)
        self.server_name = mcp_config.get("name", "unnamed-mcp-server")

    def _get_transport_type(self) -> str:
        """Return transport type description."""
        if self.mcp_config.get("type") == "http":
            return f"HTTP ({self.mcp_config.get('url', 'unknown')})"
        return "stdio (local process)"

    async def generate(self):
        """Generate the complete skill structure."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print(f"Generating skill for MCP server: {self.server_name}")

        # 1. Introspect MCP server to get tool list
        tools = await self._get_mcp_tools()

        # 2. Generate SKILL.md
        self._generate_skill_md(tools)

        # 3. Generate executor script
        self._generate_executor()

        # 4. Generate config file
        self._generate_config()

        # 5. Generate package.json (if needed)
        self._generate_package_json()

        print(f"✓ Skill generated at: {self.output_dir}")
        print(f"✓ Tools available: {len(tools)}")

    async def _get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Connect to MCP server and get available tools."""
        command = self.mcp_config.get("command", "")

        print(f"Introspecting MCP server: {command}")

        # In a real implementation, this would:
        # 1. Start the MCP server process
        # 2. Send tools/list request
        # 3. Parse the response

        # Mock response for demonstration
        return [
            {
                "name": "example_tool",
                "description": "An example tool from the MCP server",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string", "description": "First parameter"}
                    },
                    "required": ["param1"],
                },
            }
        ]

    def _generate_skill_md(self, tools: List[Dict[str, Any]]):
        """Generate the SKILL.md file with instructions for Claude."""

        # Create tool list for Claude
        tool_list = "\n".join(
            [
                f"- `{t['name']}`: {t.get('description', 'No description')}"
                for t in tools
            ]
        )

        # Count tools
        tool_count = len(tools)

        content = f"""---
name: {self.server_name}
description: Dynamic access to {self.server_name} MCP server ({tool_count} tools)
version: 1.0.0
---

# {self.server_name} Skill

This skill provides dynamic access to the {self.server_name} MCP server without loading all tool definitions into context.

## Transport Type

This skill connects via: **{self._get_transport_type()}**

## Context Efficiency

Traditional MCP approach:
- All {tool_count} tools loaded at startup
- Estimated context: {tool_count * 500} tokens

This skill approach:
- Metadata only: ~100 tokens
- Full instructions (when used): ~5k tokens
- Tool execution: 0 tokens (runs externally)

## How This Works

Instead of loading all MCP tool definitions upfront, this skill:
1. Tells you what tools are available (just names and brief descriptions)
2. You decide which tool to call based on the user's request
3. Generate a JSON command to invoke the tool
4. The executor handles the actual MCP communication

## Available Tools

{tool_list}

## Usage Pattern

When the user's request matches this skill's capabilities:

**Step 1: Identify the right tool** from the list above

**Step 2: Generate a tool call** in this JSON format:

```json
{{
  "tool": "tool_name",
  "arguments": {{
    "param1": "value1",
    "param2": "value2"
  }}
}}
```

**Step 3: Execute via bash:**

```bash
cd $SKILL_DIR
python executor.py --call 'YOUR_JSON_HERE'
```

IMPORTANT: Replace $SKILL_DIR with the actual discovered path of this skill directory.

## Getting Tool Details

If you need detailed information about a specific tool's parameters:

```bash
cd $SKILL_DIR
python executor.py --describe tool_name
```

This loads ONLY that tool's schema, not all tools.

## Examples

### Example 1: Simple tool call

User: "Use {self.server_name} to do X"

Your workflow:
1. Identify tool: `example_tool`
2. Generate call JSON
3. Execute:

```bash
cd $SKILL_DIR
python executor.py --call '{{"tool": "example_tool", "arguments": {{"param1": "value"}}}}'
```

### Example 2: Get tool details first

```bash
cd $SKILL_DIR
python executor.py --describe example_tool
```

Returns the full schema, then you can generate the appropriate call.

## Error Handling

If the executor returns an error:
- Check the tool name is correct
- Verify required arguments are provided
- Ensure the MCP server is accessible

## Performance Notes

Context usage comparison for this skill:

| Scenario | MCP (preload) | Skill (dynamic) |
|----------|---------------|-----------------|
| Idle | {tool_count * 500} tokens | 100 tokens |
| Active | {tool_count * 500} tokens | 5k tokens |
| Executing | {tool_count * 500} tokens | 0 tokens |

Savings: ~{int((1 - 5000/(tool_count * 500)) * 100)}% reduction in typical usage

---

*This skill was auto-generated from an MCP server configuration.*
*Generator: mcp_to_skill.py*
"""

        skill_path = self.output_dir / "SKILL.md"
        skill_path.write_text(content)
        print(f"✓ Generated: {skill_path}")

    def _generate_executor(self):
        """Generate the executor script that communicates with MCP server."""

        executor_code = '''#!/usr/bin/env python3
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
'''

        executor_path = self.output_dir / "executor.py"
        executor_path.write_text(executor_code)
        executor_path.chmod(0o755)
        print(f"✓ Generated: {executor_path}")

    def _generate_config(self):
        """Save MCP server config for the executor."""
        config_path = self.output_dir / "mcp-config.json"
        with open(config_path, "w") as f:
            json.dump(self.mcp_config, f, indent=2)
        print(f"✓ Generated: {config_path}")

    def _generate_package_json(self):
        """Generate package.json for dependencies."""
        package = {
            "name": f"skill-{self.server_name}",
            "version": "1.0.0",
            "description": f"Claude Skill wrapper for {self.server_name} MCP server",
            "scripts": {"setup": "pip install mcp"},
        }

        package_path = self.output_dir / "package.json"
        with open(package_path, "w") as f:
            json.dump(package, f, indent=2)
        print(f"✓ Generated: {package_path}")


def parse_mcp_config(config_path: str, server_name: str = None) -> List[Dict[str, Any]]:
    """Parse MCP config, supporting both single-server and mcpServers formats.

    Returns list of (name, config) tuples.
    """
    with open(config_path) as f:
        data = json.load(f)

    # Standard mcpServers format: {"mcpServers": {"name": {...}, ...}}
    if "mcpServers" in data:
        servers = []
        for name, config in data["mcpServers"].items():
            if server_name and name != server_name:
                continue
            config["name"] = name
            servers.append(config)
        return servers

    # Single-server format: {"name": "...", "command": "...", ...}
    if "command" in data or "url" in data:
        return [data]

    raise ValueError("Invalid config format. Expected 'mcpServers' or single server config.")


async def convert_mcp_to_skill(mcp_config_path: str, output_dir: str, server_name: str = None):
    """Convert MCP server configuration(s) to Skill(s)."""

    servers = parse_mcp_config(mcp_config_path, server_name)

    if not servers:
        if server_name:
            print(f"Error: Server '{server_name}' not found in config")
            return
        print("Error: No servers found in config")
        return

    output_base = Path(output_dir)

    for config in servers:
        name = config.get("name", "unnamed-mcp-server")
        # Always use server name as subdirectory
        skill_dir = output_base / name

        generator = MCPSkillGenerator(config, skill_dir)
        await generator.generate()

    print("\n" + "=" * 60)
    print(f"✓ Generated {len(servers)} skill(s)!")
    print("=" * 60)

    print(f"\nTo use:")
    print(f"  pip install mcp")
    print(f"  cp -r {output_dir}/* ~/.claude/skills/")


def main():
    parser = argparse.ArgumentParser(
        description="Convert MCP server(s) to Claude Skill(s)",
        epilog="""Examples:
  # Single server config
  python mcp_to_skill.py --mcp-config server.json --output-dir ./skills/myserver

  # Standard mcpServers format (all servers)
  python mcp_to_skill.py --mcp-config mcp.json --output-dir ./skills

  # Standard mcpServers format (specific server)
  python mcp_to_skill.py --mcp-config mcp.json --output-dir ./skills/github --server github
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mcp-config", required=True, help="Path to MCP config JSON (single or mcpServers format)"
    )
    parser.add_argument(
        "--output-dir", required=True, help="Output directory for generated skill(s)"
    )
    parser.add_argument(
        "--server", help="Specific server name to convert (for mcpServers format)"
    )

    args = parser.parse_args()

    asyncio.run(convert_mcp_to_skill(args.mcp_config, args.output_dir, args.server))


if __name__ == "__main__":
    main()
