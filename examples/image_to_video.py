"""Animate a still image into a short video."""

import os

from seeda_sdk import SeedaClient


def main() -> None:
    client = SeedaClient(api_key=os.environ["SEEDA_API_KEY"])

    task = client.image_to_video(
        prompt="the character waves at the camera and smiles",
        image_url="https://example.com/portrait.png",
        duration=5,
        aspect_ratio="9:16",
    )
    print(f"created task {task.id}")

    final = client.wait_for_result(task.id, timeout=900, poll_interval=5)
    if final.is_failed:
        raise SystemExit(f"task failed: {final.error_message}")

    print("video url:", final.url)


if __name__ == "__main__":
    main()
