# Homework 5: Configure MCP Servers

**Author**: Andrii Chernenko  
**Date**: August 4, 2026  
**AI Tools Used**: Claude Code (Haiku 4.5) for MCP server implementation and configuration

---

## Overview

This homework implements comprehensive MCP (Model Context Protocol) server configuration across four servers:

1. **GitHub MCP** — Connect Claude to GitHub for repository interactions
2. **Filesystem MCP** — Access local files and directories
3. **Jira/Atlassian MCP** — Query project management and issue tracking
4. **Custom MCP Server** — Build a FastMCP server with resources and tools

All servers are configured in the root `.mcp.json` and fully operational for integration with Claude Code and Copilot.

---

## Implementation Details

### Task 1: GitHub MCP ✅

Configured via `.mcp.json` using the official GitHub Copilot MCP server.

**Configuration**:

```json
"github": {
  "type": "http",
  "url": "https://api.githubcopilot.com/mcp",
  "headers": {
    "Authorization": "Bearer ${GITHUB_PAT}"
  }
}
```

**Credentials**: Uses GitHub PAT from environment (`.env`)

**Status**: Connected and ready for repository queries, PR reviews, and issue management

---

### Task 2: Filesystem MCP ✅

Configured to access the project directory structure.

**Configuration**:

```json
"filesystem": {
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-filesystem"
  ]
}
```

**Status**: Provides read/write access to project files and directories

---

### Task 3: Jira/Atlassian MCP ✅

Connected to Atlassian Cloud for Jira and Confluence access.

**Configuration**:

```json
"atlassian": {
  "type": "http",
  "url": "https://mcp.atlassian.com/v1/mcp/authv2"
}
```

**Status**: Authenticated and ready for bug queries, ticket creation, and project management

---

### Task 4: Custom MCP Server ✅

Built a FastMCP server in `custom-mcp-server/` exposing two resources and one tool over `lorem-ipsum.md` (418 words):

- **Resource**: `lorem://ipsum` — First 30 words of `lorem-ipsum.md` (the default word count)
- **Resource** (template): `lorem://ipsum/{word_count}` — First `word_count` words, e.g. `lorem://ipsum/50`
- **Tool**: `read(word_count?: int)` — Claude-callable function returning the same content as the resources, with an optional `word_count` argument (defaults to 30 when omitted)

**Key Files**:

- `custom-mcp-server/server.py` — FastMCP server implementation
- `custom-mcp-server/lorem-ipsum.md` — Source text (Lorem ipsum, 418 words)
- `custom-mcp-server/pyproject.toml` — Project/dependency manifest (declares `fastmcp`)
- `custom-mcp-server/HOWTORUN.md` — Detailed setup and usage instructions

**Tooling note**: The server is managed with [`uv`](https://docs.astral.sh/uv/), which
provisions an isolated Python 3.10+ environment on demand — no changes to system
Python were needed (the system Python here is 3.9, which is too old for this
project's dependencies).

**Configuration**:

```json
"custom-lorem": {
  "command": "uv",
  "args": ["run", "--directory", "homework-5/custom-mcp-server", "server.py"]
}
```

**Status**: Ready to use; all 6 unit tests pass (`uv run pytest tests/ -v`); tested with various word counts

---

## Testing and Verification

All servers have been tested and verified:

1. **GitHub MCP** — Queries repository, lists PRs, and retrieves commits
2. **Filesystem MCP** — Lists directory structure and reads files
3. **Atlassian MCP** — Accesses Jira projects and retrieves bug tickets
4. **Custom MCP** — `read` tool returns exactly the requested word count or 30 as a default count number

---

## References

- [MCP Documentation](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/modelcontextprotocol/python-sdk)
- [GitHub MCP Server](https://github.com/github/mcp-server-github)
- [Atlassian MCP Server](https://github.com/atlassian/mcp-server-atlassian)
