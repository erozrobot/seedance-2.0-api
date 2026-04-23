"""Transform an input image with a text prompt."""

import os

from seeda_sdk import SeedaClient


def main() -> None:
    client = SeedaClient(api_key=os.environ["SEEDA_API_KEY"])

    task = client.image_to_image(
        prompt="make it cyberpunk with rain and neon signs",
        image_url="https://example.com/input.png",
        resolution="4K",
    )
    print(f"created task {task.id}")

    final = client.wait_for_result(task.id)
    print("output url:", final.url)


if __name__ == "__main__":
    main()
