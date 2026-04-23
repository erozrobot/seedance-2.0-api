"""Generate an image from a text prompt and print the hosted URL."""

import os

from seeda_sdk import SeedaClient


def main() -> None:
    client = SeedaClient(api_key=os.environ["SEEDA_API_KEY"])

    task = client.text_to_image(
        prompt="a cute cat astronaut floating above neon tokyo",
        resolution="2K",
    )
    print(f"created task {task.id} (cost={task.cost_credits} credits)")

    final = client.wait_for_result(task.id, timeout=600, poll_interval=3)
    if final.is_failed:
        raise SystemExit(f"task failed: {final.error_message}")

    print("image url:", final.url)


if __name__ == "__main__":
    main()
