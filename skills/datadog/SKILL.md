---
name: datadog
description: Dynamic access to datadog MCP server (1 tools)
version: 1.0.0
---

# datadog Skill

This skill provides dynamic access to the datadog MCP server without loading all tool definitions into context.

## Transport Type

This skill connects via: **HTTP (https://mcp.datadoghq.eu/api/unstable/mcp-server/mcp?toolsets=core)**

## Context Efficiency

Traditional MCP approach:
- All 1 tools loaded at startup
- Estimated context: 500 tokens

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

- `example_tool`: An example tool from the MCP server

## Usage Pattern

When the user's request matches this skill's capabilities:

**Step 1: Identify the right tool** from the list above

**Step 2: Generate a tool call** in this JSON format:

```json
{
  "tool": "tool_name",
  "arguments": {
    "param1": "value1",
    "param2": "value2"
  }
}
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

User: "Use datadog to do X"

Your workflow:
1. Identify tool: `example_tool`
2. Generate call JSON
3. Execute:

```bash
cd $SKILL_DIR
python executor.py --call '{"tool": "example_tool", "arguments": {"param1": "value"}}'
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
| Idle | 500 tokens | 100 tokens |
| Active | 500 tokens | 5k tokens |
| Executing | 500 tokens | 0 tokens |

Savings: ~-900% reduction in typical usage

---

*This skill was auto-generated from an MCP server configuration.*
*Generator: mcp_to_skill.py*
