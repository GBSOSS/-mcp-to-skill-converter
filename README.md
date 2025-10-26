# mcp-to-skill-converter

Convert any MCP server into a Claude Skill with 90% context savings.

## Why This Exists

MCP servers are great but load all tool definitions into context at startup. With 20+ tools, that's 30-50k tokens gone before Claude does any work.

This converter applies the "progressive disclosure" pattern (inspired by playwright-skill) to any MCP server:
- **Startup**: ~100 tokens (just metadata)
- **When used**: ~5k tokens (full instructions)
- **Executing**: 0 tokens (runs externally)

## Quick Start

```bash
# 1. Create your MCP config file
cat > github-mcp.json << 'EOF'
{
  "name": "github",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {"GITHUB_TOKEN": "your-token-here"}
}
EOF

# 2. Convert to Skill
python mcp_to_skill.py \
  --mcp-config github-mcp.json \
  --output-dir ./skills/github

# 3. Install dependencies
cd skills/github
pip install mcp

# 4. Copy to Claude
cp -r . ~/.claude/skills/github
```

Done! Claude can now use GitHub tools with minimal context.

## What It Does

The converter:
1. Reads your MCP server config
2. Generates a Skill structure with:
   - `SKILL.md` - Instructions for Claude
   - `executor.py` - Handles MCP calls dynamically
   - Config files
3. Claude loads metadata only (~100 tokens)
4. Full instructions load when the skill is needed
5. Executor runs MCP tools outside context

## Context Savings

**Before (MCP)**:
```
20 tools = 30k tokens always loaded
Context available: 170k / 200k = 85%
```

**After (Skills)**:
```
20 skills = 2k tokens metadata
When 1 skill active: 7k tokens
Context available: 193k / 200k = 96.5%
```

## Real Example

GitHub MCP server (8 tools):

| Metric | MCP | Skill | Savings |
|--------|-----|-------|---------|
| Idle | 8,000 tokens | 100 tokens | 98.75% |
| Active | 8,000 tokens | 5,000 tokens | 37.5% |

## Works With

Any standard MCP server:
- ✅ @modelcontextprotocol/server-github
- ✅ @modelcontextprotocol/server-slack  
- ✅ @modelcontextprotocol/server-filesystem
- ✅ @modelcontextprotocol/server-postgres
- ✅ Your custom MCP servers

## When To Use

**Use this converter when:**
- You have 10+ tools
- Context space is tight
- Most tools won't be used in each conversation
- Tools are independent

**Stick with MCP when:**
- You have 1-5 tools
- Need complex OAuth flows
- Need persistent connections
- Cross-platform compatibility critical

**Best approach: Use both**
- MCP for core tools
- Skills for extended toolset

## Requirements

```bash
pip install mcp
```

Python 3.8+ required.

## How It Works

```
┌─────────────────────────────────────┐
│ Your MCP Config                     │
│ (JSON file)                         │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ mcp_to_skill.py                     │
│ - Reads config                      │
│ - Generates Skill structure         │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ Generated Skill                     │
│ ├── SKILL.md (100 tokens)           │
│ ├── executor.py (dynamic calls)     │
│ └── config files                    │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ Claude                              │
│ - Loads metadata only               │
│ - Full docs when needed             │
│ - Calls executor for tools          │
└─────────────────────────────────────┘
```

## Examples

### Example 1: GitHub Integration

```bash
# Create config
cat > github.json << 'EOF'
{
  "name": "github",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {"GITHUB_TOKEN": "ghp_your_token"}
}
EOF

# Convert
python mcp_to_skill.py --mcp-config github.json --output-dir ./skills/github

# Result: GitHub tools accessible with 100 tokens vs 8k
```

### Example 2: Multiple Servers

```bash
# Convert multiple MCP servers
for config in configs/*.json; do
  name=$(basename "$config" .json)
  python mcp_to_skill.py --mcp-config "$config" --output-dir "./skills/$name"
done
```

## Troubleshooting

### "mcp package not found"
```bash
pip install mcp
```

### "MCP server not responding"
Check your config file:
- Command is correct
- Environment variables set
- Server is accessible

### Testing the generated skill
```bash
cd skills/your-skill

# List tools
python executor.py --list

# Describe a tool
python executor.py --describe tool_name

# Call a tool
python executor.py --call '{"tool": "tool_name", "arguments": {...}}'
```

## Limitations

- Early stage (feedback welcome)
- Requires `mcp` Python package
- Some complex auth may need adjustments
- Not all MCP servers tested

## Contributing

This is a proof of concept. Contributions welcome:
- Test with more MCP servers
- Improve error handling
- Add more examples
- Better documentation

## Credits

Inspired by:
- [playwright-skill](https://github.com/lackeyjb/playwright-skill) by @lackeyjb
- [Anthropic Skills](https://www.anthropic.com/news/skills) framework
- [Model Context Protocol](https://modelcontextprotocol.io/)

## License

MIT

## Learn More

- [Detailed writeup](link-to-your-gist)
- [Anthropic Skills docs](https://www.anthropic.com/news/skills)
- [MCP specification](https://modelcontextprotocol.io/)

---

**Status**: Functional but early stage  
**Feedback**: Issues and PRs welcome  
**Questions**: Open an issue
