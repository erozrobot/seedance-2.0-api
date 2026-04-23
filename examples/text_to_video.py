"""Generate a video from a text prompt."""

import os

from seeda_sdk import SeedaClient


def main() -> None:
    client = SeedaClient(api_key=os.environ["SEEDA_API_KEY"])

    task = client.text_to_video(
        prompt="a golden retriever surfing a wave at sunset, cinematic",
        duration=5,
        aspect_ratio="16:9",
    )
    print(f"created task {task.id} (cost={task.cost_credits} credits)")

    final = client.wait_for_result(task.id, timeout=900, poll_interval=5)
    print("video url:", final.url)


if __name__ == "__main__":
    main()
