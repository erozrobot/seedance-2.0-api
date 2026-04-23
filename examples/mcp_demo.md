# Running the seeda MCP server

The `seeda-mcp` entry point starts a [FastMCP](https://github.com/jlowin/fastmcp)
server over stdio that exposes the SDK as Model Context Protocol tools. Point
Claude Desktop, Cursor, or any MCP-aware agent at it and ask for images or
videos in natural language.

## Install

```bash
pip install "git+https://github.com/erozrobot/seedance-2.0-api.git#egg=seeda-sdk[mcp]"
```

Grab an API key from <https://seeda.app/settings/apikeys> and export it:

```bash
export SEEDA_API_KEY=sk-...
```

## Run the server

```bash
seeda-mcp
```

The process speaks MCP over stdio, so it is typically launched by a host
application rather than run interactively.

## Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "seeda": {
      "command": "seeda-mcp",
      "env": {
        "SEEDA_API_KEY": "sk-..."
      }
    }
  }
}
```

Restart Claude Desktop. You should see a wrench icon indicating that the
`seeda` tools are available.

## Cursor

Add the following to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "seeda": {
      "command": "seeda-mcp",
      "env": {
        "SEEDA_API_KEY": "sk-..."
      }
    }
  }
}
```

## Exposed tools

| Tool | Description |
| --- | --- |
| `text_to_image` | Generate an image from a prompt (waits for result by default). |
| `image_to_image` | Transform an input image URL using a prompt. |
| `text_to_video` | Generate a video from a prompt. |
| `image_to_video` | Animate an input image into a video. |
| `query_task` | Fetch the latest state of a task id. |
| `cancel_task` | Cancel a pending task and refund credits. |

All generation tools return a compact payload with `status`, `url`, `urls`,
`cost_credits`, and the raw `result` object, so the agent can forward a
usable URL straight to the user.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `SEEDA_API_KEY` | _(required)_ | Bearer token for the seeda.app API. |
| `SEEDA_BASE_URL` | `https://seeda.app` | Override when self-hosting or staging. |
| `SEEDA_WAIT_TIMEOUT` | `600` | Default `timeout` seconds for blocking tools. |
| `SEEDA_POLL_INTERVAL` | `3` | Default polling interval in seconds. |
