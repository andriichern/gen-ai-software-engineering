# HOWTORUN — Custom MCP Server (Lorem Ipsum)

## What this is

A FastMCP server exposing:
- **Resources** — URIs Claude can read from directly:
  - `lorem://ipsum` — first 30 words of `lorem-ipsum.md` (the default).
  - `lorem://ipsum/{word_count}` — first `word_count` words, e.g. `lorem://ipsum/50`.
- **Tool** — an action Claude can call with arguments:
  - `read(word_count?: int)` — same content as the resource, callable with an
    optional `word_count` (defaults to 30 when omitted).

Resources are for Claude to *read* passively (like opening a file); the `read`
tool is for Claude to *call* with a specific parameter value at request time.

## Install dependencies

Requires [`uv`](https://docs.astral.sh/uv/) (manages an isolated Python 3.10+
environment; no system Python changes needed):

```bash
cd homework-5/custom-mcp-server
uv sync
```

This creates `.venv/` and installs `fastmcp` (and `pytest` for tests) per
`pyproject.toml`.

## Run the server standalone

```bash
uv run server.py
```

The server communicates over stdio — it will appear to hang with no output,
which is expected for an MCP stdio server waiting for a client.

## Run the MCP Inspector (manual testing)

```bash
uv run fastmcp dev server.py
```

Opens a browser-based inspector where you can list resources/tools and call
`read` directly with different `word_count` values.

## Connect via MCP configuration

The root `.mcp.json` (`/Users/andriichern/Projects/gen-ai-software-engineering/.mcp.json`)
registers this server as `custom-lorem`:

```json
"custom-lorem": {
  "command": "uv",
  "args": ["run", "--directory", "homework-5/custom-mcp-server", "server.py"]
}
```

Restart Claude Code (or reload MCP servers) after editing `.mcp.json` for the
new server to connect.

## Use/test the `read` tool from Claude Code

Once connected, ask Claude something like:

> Use the `read` tool from the custom-lorem MCP server to get 15 words of lorem ipsum text.

Claude will call `read(word_count=15)` and return exactly 15 words back.

## Run the unit tests

```bash
uv run pytest tests/ -v
```

## Verified

- [ ] `uv run server.py` starts without error (stdio server, blocks waiting for a client).
- [ ] `.mcp.json` at the repo root has a `custom-lorem` entry pointing at this directory.
- [ ] `fastmcp` is listed as a dependency in `pyproject.toml`.
- [ ] `uv run pytest tests/ -v` passes all tests.
