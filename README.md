# seeda-sdk

Python SDK and MCP server for the [seeda.app](https://seeda.app) AI API — text-to-image, image-to-image, text-to-video, image-to-video, and music generation in one package.

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![CI](https://github.com/erozrobot/seedance-2.0-api/actions/workflows/ci.yml/badge.svg)

## Install

```bash
pip install "git+https://github.com/erozrobot/seedance-2.0-api.git"
# with MCP server support (FastMCP):
pip install "git+https://github.com/erozrobot/seedance-2.0-api.git#egg=seeda-sdk[mcp]"
```

Grab an API key at <https://seeda.app/settings/apikeys>. Keys start with `sk-`.

## Quick start

```python
import os
from seeda_sdk import SeedaClient

client = SeedaClient(api_key=os.environ["SEEDA_API_KEY"])
task = client.text_to_image(prompt="a cute cat astronaut", resolution="2K")
final = client.wait_for_result(task.id)
print(final.url)
```

The client is synchronous. Generation is async server-side — `wait_for_result` polls `/api/ai/query` and returns once the task reaches `success` or `failed`.

## Configuration

| Source | Variable | Default |
| --- | --- | --- |
| Constructor arg | `api_key` | — |
| Environment | `SEEDA_API_KEY` | — |
| Constructor arg | `base_url` | `https://seeda.app` |
| Constructor arg | `timeout` | `60` seconds per request |

```python
client = SeedaClient()  # reads SEEDA_API_KEY from the environment
```

## API

### High-level scene helpers

| Method | Purpose |
| --- | --- |
| `text_to_image(prompt, resolution="2K", model="kie-ai", aspect_ratio=None)` | Generate an image from text. |
| `image_to_image(prompt, image_url, resolution="2K", model="kie-ai")` | Transform an image with a prompt. |
| `text_to_video(prompt, model="kie-ai", duration=None, aspect_ratio=None, resolution=None)` | Generate a video from text. |
| `image_to_video(prompt, image_url, model="kie-ai", duration=None, aspect_ratio=None, resolution=None)` | Animate a still image. |
| `video_to_video(prompt, video_url, model="kie-ai")` | Restyle a source video. |
| `text_to_music(prompt, model="kie-ai")` | Generate a music clip. |

All helpers return a `Task` immediately (server dispatches the job and responds with an `id`).

### Polling and results

```python
task = client.text_to_image(prompt="forest trail at dawn")

# Blocking helper — polls /api/ai/query every poll_interval seconds.
result = client.wait_for_result(task.id, timeout=600, poll_interval=3)

# Manual polling
state = client.query_task(task.id)
print(state.status)  # "pending" | "processing" | "success" | "failed"
print(state.url)     # shortcut to the first URL, when available
print(state.urls)    # list of URLs (multi-image outputs)

# Cancel in-flight work; credits are refunded server-side.
client.cancel_task(task.id)
```

`taskResult` is returned by the API as a JSON string (occasionally double-encoded). The SDK parses it for you and exposes it as `task.result` (dict), plus convenience accessors `task.url` and `task.urls`.

### Low-level escape hatch

If you need a provider/model/scene combination the helpers don't cover:

```python
task = client.generate(
    provider="kie",
    media_type="image",
    model="kie-ai",
    prompt="a sunset",
    scene="text-to-image",
    options={"resolution": "4K"},
)
```

### Request & response shapes

`POST /api/ai/generate`

```json
{
  "provider": "kie",
  "mediaType": "image",
  "model": "kie-ai",
  "prompt": "a cute cat",
  "scene": "text-to-image",
  "options": { "resolution": "2K" }
}
```

```json
{
  "code": 0,
  "data": {
    "id": "task-uuid",
    "taskId": "provider-task-id",
    "status": "pending",
    "prompt": "a cute cat",
    "costCredits": 8
  }
}
```

`POST /api/ai/query` and `POST /api/ai/cancel` both accept `{ "taskId": "<task-uuid>" }`.

## Scene matrix

| `mediaType` | Valid `scene` values | Required `options` |
| --- | --- | --- |
| `image` | `text-to-image`, `image-to-image` | `resolution` (2K/4K); `image_urls` for `image-to-image` |
| `video` | `text-to-video`, `image-to-video`, `video-to-video` | `image_urls` for image/video-to-video; `duration`, `aspect_ratio`, `resolution` optional |
| `music` | `text-to-music` (server-set) | — |

## Credit costs

| Scene | Credits |
| --- | --- |
| text-to-image 2K | 8 |
| text-to-image 4K | 12 |
| image-to-image 2K | 10 |
| image-to-image 4K | 15 |
| Video | 40 – 250+ (varies by model and resolution) |
| Music | 10 |

Exact pricing is managed in the seeda.app admin panel and surfaced on each `Task` as `cost_credits`.

## MCP server

Run the bundled [FastMCP](https://github.com/jlowin/fastmcp) server so Claude Desktop, Cursor, or any MCP-aware host can call seeda.app directly:

```bash
pip install "git+https://github.com/erozrobot/seedance-2.0-api.git#egg=seeda-sdk[mcp]"
export SEEDA_API_KEY=sk-...
seeda-mcp
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "seeda": {
      "command": "seeda-mcp",
      "env": { "SEEDA_API_KEY": "sk-..." }
    }
  }
}
```

Cursor (`~/.cursor/mcp.json`) uses the same structure. Full walkthrough in [`examples/mcp_demo.md`](examples/mcp_demo.md).

Tools exposed: `text_to_image`, `image_to_image`, `text_to_video`, `image_to_video`, `query_task`, `cancel_task`. Generation tools block on `wait_for_result` by default so the agent receives the final URL instead of a task id.

## Error handling

```
SeedaError
├── SeedaAuthError                    # missing/malformed key, HTTP 401
└── SeedaAPIError                     # generic API failure
    ├── SeedaInsufficientCreditsError # account has no credits left
    └── SeedaInvalidParamsError       # HTTP 400 or server-side validation
```

Each exception carries `message`, `code` (the API's `code` field), `status_code`, and the raw `response` payload. `wait_for_result` raises `TimeoutError` if the job doesn't finish in time; that is intentionally a stdlib type so you can catch it without importing from the SDK.

Common server messages:

| Message | Likely cause |
| --- | --- |
| `no auth, please sign in` | missing/invalid `Authorization` header |
| `invalid params` | required option missing for this scene |
| `insufficient credits` | top up at <https://seeda.app/settings/billing> |
| `invalid provider` / `invalid mediaType` / `invalid scene` | bad combination — see scene matrix |

## Development

```bash
git clone https://github.com/erozrobot/seedance-2.0-api.git
cd seedance-2.0-api
pip install -e ".[mcp,dev]"
pytest tests/ -v
ruff check seeda_sdk tests examples
```

CI runs on Python 3.10, 3.11, and 3.12 (see `.github/workflows/ci.yml`). The MCP extra requires Python ≥3.10 (upstream `fastmcp` constraint).

## License

MIT — see [`LICENSE`](LICENSE).

## Credits

Inspired by [Anil-matcha/Seedance-2.0-API](https://github.com/Anil-matcha/Seedance-2.0-API) (MIT). This project reuses the surface-area idea (a small, ergonomic Python wrapper around a Seedance-class API) but targets the seeda.app API exclusively and ships an MCP server on top.
