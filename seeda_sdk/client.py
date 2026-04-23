"""Synchronous HTTP client for the seeda.app AI API."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import requests

from .exceptions import (
    SeedaAPIError,
    SeedaAuthError,
    SeedaInsufficientCreditsError,
    SeedaInvalidParamsError,
)
from .types import MediaType, Provider, Scene, Task

DEFAULT_BASE_URL = "https://seeda.app"
DEFAULT_TIMEOUT = 60

# Default provider/model pairs. These can be overridden per-call.
DEFAULT_IMAGE_MODEL = "kie-ai"
DEFAULT_VIDEO_MODEL = "kie-ai"
DEFAULT_MUSIC_MODEL = "kie-ai"
DEFAULT_PROVIDER: Provider = "kie"


def _classify_error(message: str, code: Optional[int], status: Optional[int]) -> SeedaAPIError:
    """Map a server ``message`` / HTTP ``status`` pair to a specific exception."""
    lower = (message or "").lower()
    if status == 401 or "no auth" in lower or "please sign in" in lower or "unauthorized" in lower:
        return SeedaAuthError(message or "authentication failed")
    if "insufficient credit" in lower or "not enough credit" in lower:
        return SeedaInsufficientCreditsError(
            message or "insufficient credits", code=code, status_code=status
        )
    if "invalid params" in lower or "invalid provider" in lower or "invalid mediatype" in lower \
            or "invalid scene" in lower or status == 400:
        return SeedaInvalidParamsError(
            message or "invalid params", code=code, status_code=status
        )
    return SeedaAPIError(message or "seeda api error", code=code, status_code=status)


class SeedaClient:
    """Synchronous client for the seeda.app AI API.

    Args:
        api_key: Your seeda.app API key (starts with ``sk-``). If omitted,
            the ``SEEDA_API_KEY`` environment variable is read.
        base_url: Override the API base URL. Defaults to ``https://seeda.app``.
        timeout: Per-request timeout in seconds.
        session: Optional pre-configured :class:`requests.Session`.

    Example:
        >>> client = SeedaClient(api_key="sk-...")
        >>> task = client.text_to_image(prompt="a cute cat", resolution="2K")
        >>> final = client.wait_for_result(task.id)
        >>> print(final.url)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
    ) -> None:
        key = api_key or os.environ.get("SEEDA_API_KEY")
        if not key:
            raise SeedaAuthError(
                "api_key is required; pass it explicitly or set SEEDA_API_KEY"
            )
        if not isinstance(key, str) or not key.startswith("sk-"):
            raise SeedaAuthError(
                "api_key looks malformed; expected a string starting with 'sk-'"
            )

        self.api_key = key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()

    # ------------------------------------------------------------------ HTTP --

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "seeda-sdk-python/0.1.0",
        }

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self._session.post(
                url, json=payload, headers=self._headers(), timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise SeedaAPIError(f"network error: {exc}") from exc

        try:
            body = response.json()
        except ValueError:
            body = None

        if not response.ok:
            message = (
                (body or {}).get("message")
                if isinstance(body, dict)
                else None
            ) or f"HTTP {response.status_code}"
            raise _classify_error(
                message,
                code=(body or {}).get("code") if isinstance(body, dict) else None,
                status=response.status_code,
            )

        if not isinstance(body, dict):
            raise SeedaAPIError("invalid response body", status_code=response.status_code)

        if body.get("code") not in (0, None):
            raise _classify_error(
                body.get("message") or "seeda api error",
                code=body.get("code"),
                status=response.status_code,
            )

        data = body.get("data")
        if not isinstance(data, dict):
            raise SeedaAPIError("missing data object in response", response=body)
        return data

    # ------------------------------------------------------------- Low level --

    def generate(
        self,
        *,
        provider: Provider,
        media_type: MediaType,
        model: str,
        prompt: str,
        scene: Scene,
        options: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Create a new generation task (low-level escape hatch).

        Prefer the ``text_to_image`` / ``image_to_video`` / ... helpers for
        common workflows; this method is a thin wrapper around
        ``POST /api/ai/generate``.
        """
        payload: Dict[str, Any] = {
            "provider": provider,
            "mediaType": media_type,
            "model": model,
            "prompt": prompt,
            "scene": scene,
        }
        if options:
            payload["options"] = options
        data = self._post("/api/ai/generate", payload)
        return Task.from_response(data)

    def query_task(self, task_id: str) -> Task:
        """Fetch the current state of a task by its ``id``."""
        if not task_id:
            raise SeedaInvalidParamsError("task_id is required")
        data = self._post("/api/ai/query", {"taskId": task_id})
        return Task.from_response(data)

    def cancel_task(self, task_id: str) -> Task:
        """Cancel a pending/processing task. Refunds credits server-side."""
        if not task_id:
            raise SeedaInvalidParamsError("task_id is required")
        data = self._post("/api/ai/cancel", {"taskId": task_id})
        return Task.from_response(data)

    # -------------------------------------------------------- Scene helpers --

    def text_to_image(
        self,
        *,
        prompt: str,
        resolution: str = "2K",
        model: str = DEFAULT_IMAGE_MODEL,
        provider: Provider = DEFAULT_PROVIDER,
        aspect_ratio: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Generate an image from a text prompt.

        Example:
            >>> task = client.text_to_image(prompt="a cute cat", resolution="2K")
        """
        merged: Dict[str, Any] = {"resolution": resolution}
        if aspect_ratio:
            merged["aspect_ratio"] = aspect_ratio
        if options:
            merged.update(options)
        return self.generate(
            provider=provider,
            media_type="image",
            model=model,
            prompt=prompt,
            scene="text-to-image",
            options=merged,
        )

    def image_to_image(
        self,
        *,
        prompt: str,
        image_url: str,
        resolution: str = "2K",
        model: str = DEFAULT_IMAGE_MODEL,
        provider: Provider = DEFAULT_PROVIDER,
        options: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Transform an input image using a text prompt."""
        if not image_url:
            raise SeedaInvalidParamsError("image_url is required for image_to_image")
        merged: Dict[str, Any] = {
            "resolution": resolution,
            "image_urls": [image_url],
        }
        if options:
            merged.update(options)
        return self.generate(
            provider=provider,
            media_type="image",
            model=model,
            prompt=prompt,
            scene="image-to-image",
            options=merged,
        )

    def text_to_video(
        self,
        *,
        prompt: str,
        model: str = DEFAULT_VIDEO_MODEL,
        provider: Provider = DEFAULT_PROVIDER,
        duration: Optional[int] = None,
        aspect_ratio: Optional[str] = None,
        resolution: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Generate a video from a text prompt."""
        merged: Dict[str, Any] = {}
        if duration is not None:
            merged["duration"] = duration
        if aspect_ratio:
            merged["aspect_ratio"] = aspect_ratio
        if resolution:
            merged["resolution"] = resolution
        if options:
            merged.update(options)
        return self.generate(
            provider=provider,
            media_type="video",
            model=model,
            prompt=prompt,
            scene="text-to-video",
            options=merged or None,
        )

    def image_to_video(
        self,
        *,
        prompt: str,
        image_url: str,
        model: str = DEFAULT_VIDEO_MODEL,
        provider: Provider = DEFAULT_PROVIDER,
        duration: Optional[int] = None,
        aspect_ratio: Optional[str] = None,
        resolution: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Animate an image into a video with a text prompt."""
        if not image_url:
            raise SeedaInvalidParamsError("image_url is required for image_to_video")
        merged: Dict[str, Any] = {"image_urls": [image_url]}
        if duration is not None:
            merged["duration"] = duration
        if aspect_ratio:
            merged["aspect_ratio"] = aspect_ratio
        if resolution:
            merged["resolution"] = resolution
        if options:
            merged.update(options)
        return self.generate(
            provider=provider,
            media_type="video",
            model=model,
            prompt=prompt,
            scene="image-to-video",
            options=merged,
        )

    def video_to_video(
        self,
        *,
        prompt: str,
        video_url: str,
        model: str = DEFAULT_VIDEO_MODEL,
        provider: Provider = DEFAULT_PROVIDER,
        options: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Transform a source video using a text prompt."""
        if not video_url:
            raise SeedaInvalidParamsError("video_url is required for video_to_video")
        merged: Dict[str, Any] = {"image_urls": [video_url]}
        if options:
            merged.update(options)
        return self.generate(
            provider=provider,
            media_type="video",
            model=model,
            prompt=prompt,
            scene="video-to-video",
            options=merged,
        )

    def text_to_music(
        self,
        *,
        prompt: str,
        model: str = DEFAULT_MUSIC_MODEL,
        provider: Provider = DEFAULT_PROVIDER,
        options: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Generate a music clip from a text prompt.

        The server sets the scene to ``text-to-music`` regardless of input.
        """
        return self.generate(
            provider=provider,
            media_type="music",
            model=model,
            prompt=prompt,
            scene="text-to-music",
            options=options,
        )

    # ------------------------------------------------------------- Polling --

    def wait_for_result(
        self,
        task_id: str,
        *,
        timeout: int = 600,
        poll_interval: float = 3.0,
    ) -> Task:
        """Poll ``/api/ai/query`` until the task is terminal or ``timeout`` expires.

        Args:
            task_id: The ``id`` returned by :meth:`generate` or a scene helper.
            timeout: Maximum seconds to wait before raising :class:`TimeoutError`.
            poll_interval: Seconds between polls (minimum 0.5s).

        Returns:
            The terminal :class:`Task` (either ``success`` or ``failed``).

        Raises:
            TimeoutError: If the task does not finish within ``timeout``.
        """
        if not task_id:
            raise SeedaInvalidParamsError("task_id is required")
        interval = max(float(poll_interval), 0.5)
        deadline = time.monotonic() + timeout
        while True:
            task = self.query_task(task_id)
            if task.is_terminal:
                return task
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"task {task_id} still {task.status} after {timeout}s"
                )
            time.sleep(interval)
