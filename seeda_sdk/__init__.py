"""seeda-sdk: Python client and MCP server for the seeda.app AI API.

Example:
    >>> from seeda_sdk import SeedaClient
    >>> client = SeedaClient(api_key="sk-...")
    >>> task = client.text_to_image(prompt="a cute cat", resolution="2K")
    >>> result = client.wait_for_result(task.id)
    >>> print(result.result)  # {"url": "https://..."}
"""

from .client import DEFAULT_BASE_URL, SeedaClient
from .exceptions import (
    SeedaAPIError,
    SeedaAuthError,
    SeedaError,
    SeedaInsufficientCreditsError,
    SeedaInvalidParamsError,
)
from .types import MediaType, Provider, Scene, Task, TaskStatus

__all__ = [
    "DEFAULT_BASE_URL",
    "MediaType",
    "Provider",
    "Scene",
    "SeedaAPIError",
    "SeedaAuthError",
    "SeedaClient",
    "SeedaError",
    "SeedaInsufficientCreditsError",
    "SeedaInvalidParamsError",
    "Task",
    "TaskStatus",
]

__version__ = "0.1.0"
