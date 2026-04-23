"""Unit tests for :mod:`seeda_sdk.client` with a fully mocked HTTP layer."""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from seeda_sdk import (
    SeedaAPIError,
    SeedaAuthError,
    SeedaClient,
    SeedaInsufficientCreditsError,
    SeedaInvalidParamsError,
    Task,
)


def _response(
    *,
    ok: bool = True,
    status_code: int = 200,
    body=None,
    raise_json: bool = False,
) -> MagicMock:
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status_code
    if raise_json:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = body
    return resp


def _ok(data):
    return _response(ok=True, status_code=200, body={"code": 0, "data": data})


def _err(status_code, body):
    return _response(ok=False, status_code=status_code, body=body)


class AuthValidationTests(unittest.TestCase):
    def test_missing_key_raises_auth_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(SeedaAuthError):
                SeedaClient(api_key=None)

    def test_malformed_key_raises_auth_error(self):
        with self.assertRaises(SeedaAuthError):
            SeedaClient(api_key="not-an-sk-key")

    def test_env_key_picked_up(self):
        with patch.dict("os.environ", {"SEEDA_API_KEY": "sk-env"}):
            c = SeedaClient()
            self.assertEqual(c.api_key, "sk-env")


class HappyPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = SeedaClient(api_key="sk-test")

    @patch("seeda_sdk.client.requests.Session.post")
    def test_text_to_image_builds_expected_payload(self, mock_post):
        mock_post.return_value = _ok(
            {
                "id": "task-1",
                "status": "pending",
                "prompt": "a cute cat",
                "costCredits": 8,
                "taskId": "provider-1",
            }
        )

        task = self.client.text_to_image(prompt="a cute cat", resolution="2K")

        self.assertIsInstance(task, Task)
        self.assertEqual(task.id, "task-1")
        self.assertEqual(task.status, "pending")
        self.assertEqual(task.cost_credits, 8)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertTrue(args[0].endswith("/api/ai/generate"))
        payload = kwargs["json"]
        self.assertEqual(payload["provider"], "kie")
        self.assertEqual(payload["mediaType"], "image")
        self.assertEqual(payload["scene"], "text-to-image")
        self.assertEqual(payload["options"]["resolution"], "2K")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer sk-test")

    @patch("seeda_sdk.client.requests.Session.post")
    def test_image_to_image_includes_image_urls(self, mock_post):
        mock_post.return_value = _ok({"id": "t", "status": "pending"})

        self.client.image_to_image(
            prompt="cyberpunk",
            image_url="https://x/img.png",
            resolution="4K",
        )

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["scene"], "image-to-image")
        self.assertEqual(payload["options"]["image_urls"], ["https://x/img.png"])
        self.assertEqual(payload["options"]["resolution"], "4K")

    @patch("seeda_sdk.client.requests.Session.post")
    def test_image_to_video_requires_image_url(self, mock_post):
        with self.assertRaises(SeedaInvalidParamsError):
            self.client.image_to_video(prompt="go", image_url="")
        mock_post.assert_not_called()

    @patch("seeda_sdk.client.requests.Session.post")
    def test_text_to_video_options(self, mock_post):
        mock_post.return_value = _ok({"id": "t", "status": "pending"})
        self.client.text_to_video(
            prompt="dog surfs", duration=5, aspect_ratio="16:9", resolution="720p"
        )
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["scene"], "text-to-video")
        self.assertEqual(payload["options"]["duration"], 5)
        self.assertEqual(payload["options"]["aspect_ratio"], "16:9")
        self.assertEqual(payload["options"]["resolution"], "720p")

    @patch("seeda_sdk.client.requests.Session.post")
    def test_generate_low_level(self, mock_post):
        mock_post.return_value = _ok({"id": "t", "status": "pending"})
        self.client.generate(
            provider="kie",
            media_type="image",
            model="kie-ai",
            prompt="x",
            scene="text-to-image",
            options={"resolution": "2K"},
        )
        self.assertTrue(mock_post.call_args.args[0].endswith("/api/ai/generate"))


class TaskResultParsingTests(unittest.TestCase):
    def test_task_result_json_string_is_parsed(self):
        data = {
            "id": "task-1",
            "status": "success",
            "taskResult": json.dumps({"url": "https://cdn/out.png"}),
        }
        task = Task.from_response(data)
        self.assertEqual(task.result, {"url": "https://cdn/out.png"})
        self.assertEqual(task.url, "https://cdn/out.png")

    def test_task_result_double_encoded_is_parsed(self):
        inner = json.dumps({"urls": ["https://a", "https://b"]})
        data = {
            "id": "task-1",
            "status": "success",
            "taskResult": json.dumps(inner),
        }
        task = Task.from_response(data)
        self.assertEqual(task.urls, ["https://a", "https://b"])
        self.assertEqual(task.url, "https://a")

    def test_task_result_invalid_json_is_none(self):
        data = {"id": "t", "status": "failed", "taskResult": "not json at all"}
        task = Task.from_response(data)
        self.assertIsNone(task.result)
        self.assertEqual(task.status, "failed")

    def test_task_result_missing(self):
        task = Task.from_response({"id": "t", "status": "pending"})
        self.assertIsNone(task.result)
        self.assertIsNone(task.url)
        self.assertEqual(task.urls, [])

    def test_terminal_flags(self):
        self.assertTrue(Task.from_response({"id": "x", "status": "success"}).is_terminal)
        self.assertTrue(Task.from_response({"id": "x", "status": "failed"}).is_terminal)
        self.assertFalse(Task.from_response({"id": "x", "status": "pending"}).is_terminal)


class ErrorMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = SeedaClient(api_key="sk-test")

    @patch("seeda_sdk.client.requests.Session.post")
    def test_401_raises_auth_error(self, mock_post):
        mock_post.return_value = _err(401, {"code": -1, "message": "no auth, please sign in"})
        with self.assertRaises(SeedaAuthError):
            self.client.query_task("task-1")

    @patch("seeda_sdk.client.requests.Session.post")
    def test_402_insufficient_credits(self, mock_post):
        mock_post.return_value = _err(402, {"code": -1, "message": "insufficient credits"})
        with self.assertRaises(SeedaInsufficientCreditsError):
            self.client.text_to_image(prompt="x")

    @patch("seeda_sdk.client.requests.Session.post")
    def test_invalid_params_http_400(self, mock_post):
        mock_post.return_value = _err(400, {"code": -1, "message": "invalid params"})
        with self.assertRaises(SeedaInvalidParamsError):
            self.client.text_to_image(prompt="x")

    @patch("seeda_sdk.client.requests.Session.post")
    def test_body_code_nonzero_raises(self, mock_post):
        mock_post.return_value = _response(
            ok=True,
            status_code=200,
            body={"code": -1, "message": "invalid provider"},
        )
        with self.assertRaises(SeedaInvalidParamsError):
            self.client.text_to_image(prompt="x")

    @patch("seeda_sdk.client.requests.Session.post")
    def test_missing_data_raises(self, mock_post):
        mock_post.return_value = _response(
            ok=True, status_code=200, body={"code": 0, "data": None}
        )
        with self.assertRaises(SeedaAPIError):
            self.client.text_to_image(prompt="x")

    @patch("seeda_sdk.client.requests.Session.post")
    def test_network_error_raises_seeda_api_error(self, mock_post):
        import requests as _requests

        mock_post.side_effect = _requests.ConnectionError("boom")
        with self.assertRaises(SeedaAPIError):
            self.client.text_to_image(prompt="x")


class PollingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = SeedaClient(api_key="sk-test")

    @patch("seeda_sdk.client.time.sleep", return_value=None)
    @patch("seeda_sdk.client.requests.Session.post")
    def test_wait_for_result_success(self, mock_post, _sleep):
        responses = [
            _ok({"id": "task-1", "status": "pending"}),
            _ok({"id": "task-1", "status": "processing"}),
            _ok(
                {
                    "id": "task-1",
                    "status": "success",
                    "taskResult": json.dumps({"url": "https://cdn/out.png"}),
                }
            ),
        ]
        mock_post.side_effect = responses

        task = self.client.wait_for_result("task-1", timeout=30, poll_interval=0.5)

        self.assertTrue(task.is_success)
        self.assertEqual(task.url, "https://cdn/out.png")
        self.assertEqual(mock_post.call_count, 3)

    @patch("seeda_sdk.client.time.sleep", return_value=None)
    @patch("seeda_sdk.client.requests.Session.post")
    def test_wait_for_result_failed(self, mock_post, _sleep):
        mock_post.side_effect = [
            _ok({"id": "t", "status": "pending"}),
            _ok({"id": "t", "status": "failed", "errorMessage": "nsfw blocked"}),
        ]
        task = self.client.wait_for_result("t", timeout=30, poll_interval=0.5)
        self.assertTrue(task.is_failed)
        self.assertEqual(task.error_message, "nsfw blocked")

    @patch("seeda_sdk.client.time.sleep", return_value=None)
    @patch("seeda_sdk.client.requests.Session.post")
    def test_wait_for_result_timeout(self, mock_post, _sleep):
        mock_post.return_value = _ok({"id": "t", "status": "processing"})

        # Patch monotonic so the deadline trips after exactly one iteration.
        times = iter([1000.0, 1000.0, 9999.0])

        def fake_monotonic():
            return next(times)

        with patch("seeda_sdk.client.time.monotonic", side_effect=fake_monotonic):
            with self.assertRaises(TimeoutError):
                self.client.wait_for_result("t", timeout=10, poll_interval=0.5)


class QueryAndCancelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = SeedaClient(api_key="sk-test")

    @patch("seeda_sdk.client.requests.Session.post")
    def test_query_task_payload(self, mock_post):
        mock_post.return_value = _ok({"id": "t", "status": "processing"})
        self.client.query_task("t")
        args, kwargs = mock_post.call_args
        self.assertTrue(args[0].endswith("/api/ai/query"))
        self.assertEqual(kwargs["json"], {"taskId": "t"})

    @patch("seeda_sdk.client.requests.Session.post")
    def test_cancel_task_payload(self, mock_post):
        mock_post.return_value = _ok({"id": "t", "status": "failed"})
        self.client.cancel_task("t")
        args, kwargs = mock_post.call_args
        self.assertTrue(args[0].endswith("/api/ai/cancel"))
        self.assertEqual(kwargs["json"], {"taskId": "t"})

    def test_query_task_requires_id(self):
        with self.assertRaises(SeedaInvalidParamsError):
            self.client.query_task("")

    def test_cancel_task_requires_id(self):
        with self.assertRaises(SeedaInvalidParamsError):
            self.client.cancel_task("")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
