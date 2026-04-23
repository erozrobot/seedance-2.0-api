"""Typed primitives and the :class:`Task` dataclass used throughout the SDK."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional

Provider = Literal["kie", "replicate", "fal", "gemini", "go-worker"]
MediaType = Literal["image", "video", "music"]
Scene = Literal[
    "text-to-image",
    "image-to-image",
    "text-to-video",
    "image-to-video",
    "video-to-video",
    "text-to-music",
]
TaskStatus = Literal["pending", "processing", "success", "failed"]

TERMINAL_STATUSES: frozenset[str] = frozenset({"success", "failed"})


@dataclass
class Task:
    """A generation task returned by ``/api/ai/generate`` or ``/api/ai/query``.

    The seeda.app API encodes ``taskResult`` as a JSON string; this class stores
    the raw string in :attr:`task_result_raw` and the parsed dict in
    :attr:`result` for convenience.
    """

    id: str
    status: TaskStatus
    task_id: Optional[str] = None
    prompt: Optional[str] = None
    cost_credits: Optional[int] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    media_type: Optional[str] = None
    scene: Optional[str] = None
    task_result_raw: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_response(cls, data: Dict[str, Any]) -> "Task":
        """Build a :class:`Task` from a raw ``data`` object.

        Handles ``taskResult`` being encoded as a JSON string (sometimes
        double-encoded). Safe on ``None``/empty/unparseable values.
        """
        task_result_raw = data.get("taskResult")
        parsed: Optional[Dict[str, Any]] = None
        if isinstance(task_result_raw, str) and task_result_raw:
            try:
                parsed = json.loads(task_result_raw)
                # Defensive: handle double-encoded JSON strings.
                if isinstance(parsed, str):
                    parsed = json.loads(parsed)
            except (json.JSONDecodeError, TypeError):
                parsed = None
        elif isinstance(task_result_raw, dict):
            parsed = task_result_raw

        return cls(
            id=str(data.get("id") or data.get("taskId") or ""),
            status=data.get("status", "pending"),
            task_id=data.get("taskId"),
            prompt=data.get("prompt"),
            cost_credits=data.get("costCredits"),
            provider=data.get("provider"),
            model=data.get("model"),
            media_type=data.get("mediaType"),
            scene=data.get("scene"),
            task_result_raw=task_result_raw if isinstance(task_result_raw, str) else None,
            result=parsed if isinstance(parsed, dict) else None,
            error_message=data.get("errorMessage") or data.get("message"),
            raw=dict(data),
        )

    @property
    def is_terminal(self) -> bool:
        """``True`` when the task reached ``success`` or ``failed``."""
        return self.status in TERMINAL_STATUSES

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def url(self) -> Optional[str]:
        """Shortcut to the single-result URL, if the provider returned one."""
        if not self.result:
            return None
        if isinstance(self.result.get("url"), str):
            return self.result["url"]
        urls = self.result.get("urls")
        if isinstance(urls, list) and urls:
            first = urls[0]
            if isinstance(first, str):
                return first
        return None

    @property
    def urls(self) -> list[str]:
        """All output URLs, when the provider returned a multi-image result."""
        if not self.result:
            return []
        urls = self.result.get("urls")
        if isinstance(urls, list):
            return [u for u in urls if isinstance(u, str)]
        single = self.result.get("url")
        if isinstance(single, str):
            return [single]
        return []
