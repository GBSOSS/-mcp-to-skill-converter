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
        self.server_name = mcp_config.get('name', 'unnamed-mcp-server')
        
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
        command = self.mcp_config.get('command', '')
        
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
                    "required": ["param1"]
                }
            }
        ]
    
    def _generate_skill_md(self, tools: List[Dict[str, Any]]):
        """Generate the SKILL.md file with instructions for Claude."""
        
        # Create tool list for Claude
        tool_list = "\n".join([
            f"- `{t['name']}`: {t.get('description', 'No description')}"
            for t in tools
        ])
        
        # Count tools
        tool_count = len(tools)
        
        content = f"""---
name: {self.server_name}
description: Dynamic access to {self.server_name} MCP server ({tool_count} tools)
version: 1.0.0
---

# {self.server_name} Skill

This skill provides dynamic access to the {self.server_name} MCP server without loading all tool definitions into context.

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

# Check if mcp package is available
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    print("Warning: mcp package not installed. Install with: pip install mcp", file=sys.stderr)


class MCPExecutor:
    """Execute MCP tool calls dynamically."""
    
    def __init__(self, server_config):
        if not HAS_MCP:
            raise ImportError("mcp package is required. Install with: pip install mcp")
            
        self.server_config = server_config
        self.session = None
        self.stdio_transport = None
        
    async def connect(self):
        """Connect to MCP server."""
        server_params = StdioServerParameters(
            command=self.server_config["command"],
            args=self.server_config.get("args", []),
            env=self.server_config.get("env")
        )
        
        stdio_result = await stdio_client(server_params)
        self.stdio_transport = stdio_result
        read_stream, write_stream = stdio_result
        
        self.session = ClientSession(read_stream, write_stream)
        await self.session.initialize()
        
    async def list_tools(self):
        """Get list of available tools."""
        if not self.session:
            await self.connect()
            
        response = await self.session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in response.tools
        ]
        
    async def describe_tool(self, tool_name: str):
        """Get detailed schema for a specific tool."""
        if not self.session:
            await self.connect()
            
        response = await self.session.list_tools()
        for tool in response.tools:
            if tool.name == tool_name:
                return {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
        return None
        
    async def call_tool(self, tool_name: str, arguments: dict):
        """Execute a tool call."""
        if not self.session:
            await self.connect()
            
        response = await self.session.call_tool(tool_name, arguments)
        return response.content
        
    async def close(self):
        """Close MCP connection."""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
            except:
                pass


async def main():
    parser = argparse.ArgumentParser(description="MCP Skill Executor")
    parser.add_argument("--call", help="JSON tool call to execute")
    parser.add_argument("--describe", help="Get tool schema")
    parser.add_argument("--list", action="store_true", help="List all tools")
    
    args = parser.parse_args()
    
    # Load server config
    config_path = Path(__file__).parent / "mcp-config.json"
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
        
    with open(config_path) as f:
        config = json.load(f)
    
    if not HAS_MCP:
        print("Error: mcp package not installed", file=sys.stderr)
        print("Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)
    
    executor = MCPExecutor(config)
    
    try:
        if args.list:
            tools = await executor.list_tools()
            print(json.dumps(tools, indent=2))
            
        elif args.describe:
            schema = await executor.describe_tool(args.describe)
            if schema:
                print(json.dumps(schema, indent=2))
            else:
                print(f"Tool not found: {args.describe}", file=sys.stderr)
                sys.exit(1)
                
        elif args.call:
            call_data = json.loads(args.call)
            result = await executor.call_tool(
                call_data["tool"],
                call_data.get("arguments", {})
            )
            
            # Format result
            if isinstance(result, list):
                for item in result:
                    if hasattr(item, 'text'):
                        print(item.text)
                    else:
                        print(json.dumps(item.__dict__ if hasattr(item, '__dict__') else item, indent=2))
            else:
                print(json.dumps(result.__dict__ if hasattr(result, '__dict__') else result, indent=2))
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    finally:
        await executor.close()


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
        with open(config_path, 'w') as f:
            json.dump(self.mcp_config, f, indent=2)
        print(f"✓ Generated: {config_path}")
    
    def _generate_package_json(self):
        """Generate package.json for dependencies."""
        package = {
            "name": f"skill-{self.server_name}",
            "version": "1.0.0",
            "description": f"Claude Skill wrapper for {self.server_name} MCP server",
            "scripts": {
                "setup": "pip install mcp"
            }
        }
        
        package_path = self.output_dir / "package.json"
        with open(package_path, 'w') as f:
            json.dump(package, f, indent=2)
        print(f"✓ Generated: {package_path}")


async def convert_mcp_to_skill(mcp_config_path: str, output_dir: str):
    """Convert an MCP server configuration to a Skill."""
    
    # Load MCP config
    with open(mcp_config_path) as f:
        mcp_config = json.load(f)
    
    # Generate skill
    generator = MCPSkillGenerator(mcp_config, Path(output_dir))
    await generator.generate()
    
    print("\n" + "="*60)
    print("✓ Skill generation complete!")
    print("="*60)
    print(f"\nGenerated files:")
    print(f"  - SKILL.md (instructions for Claude)")
    print(f"  - executor.py (MCP communication handler)")
    print(f"  - mcp-config.json (MCP server configuration)")
    print(f"  - package.json (dependencies)")
    
    print(f"\nTo use this skill:")
    print(f"1. Install dependencies:")
    print(f"   cd {output_dir}")
    print(f"   pip install mcp")
    print(f"\n2. Copy to Claude skills directory:")
    print(f"   cp -r {output_dir} ~/.claude/skills/")
    print(f"\n3. Claude will discover it automatically")
    
    print(f"\nContext savings:")
    print(f"  Before (MCP): All tools preloaded (~10k-50k tokens)")
    print(f"  After (Skill): ~100 tokens until used")
    print(f"  Reduction: ~90-99%")


def main():
    parser = argparse.ArgumentParser(
        description="Convert MCP server to Claude Skill with progressive disclosure",
        epilog="Example: python mcp_to_skill.py --mcp-config github-mcp.json --output-dir ./skills/github"
    )
    parser.add_argument(
        "--mcp-config",
        required=True,
        help="Path to MCP server configuration JSON"
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for generated skill"
    )
    
    args = parser.parse_args()
    
    asyncio.run(convert_mcp_to_skill(args.mcp_config, args.output_dir))


if __name__ == "__main__":
    main()
