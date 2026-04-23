"""FastMCP server that exposes the seeda.app SDK as Model Context Protocol tools.

Run it:

    export SEEDA_API_KEY=sk-...
    seeda-mcp           # or: python -m seeda_sdk.mcp_server

The MCP tools wrap :class:`~seeda_sdk.SeedaClient` and, for generation tools,
block until a result is available (via ``wait_for_result``) so the calling
agent gets a usable URL back instead of only a task id.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from .client import (
    DEFAULT_IMAGE_MODEL,
    DEFAULT_PROVIDER,
    DEFAULT_VIDEO_MODEL,
    SeedaClient,
)
from .types import Task

DEFAULT_WAIT_TIMEOUT = int(os.environ.get("SEEDA_WAIT_TIMEOUT", "600"))
DEFAULT_POLL_INTERVAL = float(os.environ.get("SEEDA_POLL_INTERVAL", "3"))


def _task_to_payload(task: Task) -> Dict[str, Any]:
    """Shape a :class:`Task` into a compact dict for MCP responses."""
    return {
        "id": task.id,
        "status": task.status,
        "prompt": task.prompt,
        "cost_credits": task.cost_credits,
        "url": task.url,
        "urls": task.urls,
        "result": task.result,
        "error_message": task.error_message,
    }


def _build_client() -> SeedaClient:
    api_key = os.environ.get("SEEDA_API_KEY")
    base_url = os.environ.get("SEEDA_BASE_URL", "https://seeda.app")
    return SeedaClient(api_key=api_key, base_url=base_url)


def build_server():  # type: ignore[no-untyped-def]
    """Construct the FastMCP server with seeda tools registered."""
    try:
        from fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - import-time error
        raise SystemExit(
            "fastmcp is not installed. Install the optional MCP extra:\n"
            "    pip install 'seeda-sdk[mcp]'"
        ) from exc

    mcp = FastMCP("seeda")

    @mcp.tool()
    def text_to_image(
        prompt: str,
        resolution: str = "2K",
        model: str = DEFAULT_IMAGE_MODEL,
        provider: str = DEFAULT_PROVIDER,
        aspect_ratio: Optional[str] = None,
        wait: bool = True,
        timeout: int = DEFAULT_WAIT_TIMEOUT,
    ) -> Dict[str, Any]:
        """Generate an image from a text prompt. Returns the final URL when wait=True."""
        client = _build_client()
        task = client.text_to_image(
            prompt=prompt,
            resolution=resolution,
            model=model,
            provider=provider,  # type: ignore[arg-type]
            aspect_ratio=aspect_ratio,
        )
        if wait:
            task = client.wait_for_result(
                task.id, timeout=timeout, poll_interval=DEFAULT_POLL_INTERVAL
            )
        return _task_to_payload(task)

    @mcp.tool()
    def image_to_image(
        prompt: str,
        image_url: str,
        resolution: str = "2K",
        model: str = DEFAULT_IMAGE_MODEL,
        provider: str = DEFAULT_PROVIDER,
        wait: bool = True,
        timeout: int = DEFAULT_WAIT_TIMEOUT,
    ) -> Dict[str, Any]:
        """Transform a source image with a text prompt."""
        client = _build_client()
        task = client.image_to_image(
            prompt=prompt,
            image_url=image_url,
            resolution=resolution,
            model=model,
            provider=provider,  # type: ignore[arg-type]
        )
        if wait:
            task = client.wait_for_result(
                task.id, timeout=timeout, poll_interval=DEFAULT_POLL_INTERVAL
            )
        return _task_to_payload(task)

    @mcp.tool()
    def text_to_video(
        prompt: str,
        model: str = DEFAULT_VIDEO_MODEL,
        provider: str = DEFAULT_PROVIDER,
        duration: Optional[int] = None,
        aspect_ratio: Optional[str] = None,
        resolution: Optional[str] = None,
        wait: bool = True,
        timeout: int = DEFAULT_WAIT_TIMEOUT,
    ) -> Dict[str, Any]:
        """Generate a video from a text prompt."""
        client = _build_client()
        task = client.text_to_video(
            prompt=prompt,
            model=model,
            provider=provider,  # type: ignore[arg-type]
            duration=duration,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )
        if wait:
            task = client.wait_for_result(
                task.id, timeout=timeout, poll_interval=DEFAULT_POLL_INTERVAL
            )
        return _task_to_payload(task)

    @mcp.tool()
    def image_to_video(
        prompt: str,
        image_url: str,
        model: str = DEFAULT_VIDEO_MODEL,
        provider: str = DEFAULT_PROVIDER,
        duration: Optional[int] = None,
        aspect_ratio: Optional[str] = None,
        resolution: Optional[str] = None,
        wait: bool = True,
        timeout: int = DEFAULT_WAIT_TIMEOUT,
    ) -> Dict[str, Any]:
        """Animate a still image into a video driven by a text prompt."""
        client = _build_client()
        task = client.image_to_video(
            prompt=prompt,
            image_url=image_url,
            model=model,
            provider=provider,  # type: ignore[arg-type]
            duration=duration,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )
        if wait:
            task = client.wait_for_result(
                task.id, timeout=timeout, poll_interval=DEFAULT_POLL_INTERVAL
            )
        return _task_to_payload(task)

    @mcp.tool()
    def query_task(task_id: str) -> Dict[str, Any]:
        """Fetch the latest state of a generation task by its id."""
        client = _build_client()
        task = client.query_task(task_id)
        return _task_to_payload(task)

    @mcp.tool()
    def cancel_task(task_id: str) -> Dict[str, Any]:
        """Cancel a pending/processing task and refund credits."""
        client = _build_client()
        task = client.cancel_task(task_id)
        return _task_to_payload(task)

    return mcp


def main() -> None:
    """Entry point for the ``seeda-mcp`` script (stdio transport)."""
    server = build_server()
    server.run()


if __name__ == "__main__":  # pragma: no cover
    main()
