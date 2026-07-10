# Ensure local path has absolute priority
import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from serve_dashboard import DashboardHandler, _security_token


class TestServeSecurity(unittest.TestCase):
    def test_validate_request_valid_localhost(self) -> None:
        handler = MagicMock(spec=DashboardHandler)
        handler.headers = {"Host": "localhost:8765"}
        handler.path = "/"

        result = DashboardHandler.validate_request(handler)
        self.assertTrue(result)

    def test_validate_request_valid_127_0_0_1(self) -> None:
        handler = MagicMock(spec=DashboardHandler)
        handler.headers = {"Host": "127.0.0.1"}
        handler.path = "/"

        result = DashboardHandler.validate_request(handler)
        self.assertTrue(result)

    def test_validate_request_invalid_host(self) -> None:
        handler = MagicMock(spec=DashboardHandler)
        handler.headers = {"Host": "malicious-site.com"}
        handler.path = "/"

        result = DashboardHandler.validate_request(handler)
        self.assertFalse(result)
        handler.send_error.assert_called_once_with(400, "Invalid Host header")

    def test_validate_request_api_without_token(self) -> None:
        handler = MagicMock(spec=DashboardHandler)
        handler.headers = {"Host": "localhost:8765"}
        handler.path = "/api/events"

        result = DashboardHandler.validate_request(handler)
        self.assertFalse(result)
        handler.send_error.assert_called_once_with(403, "Forbidden: Invalid security token")

    def test_validate_request_api_with_header_token(self) -> None:
        handler = MagicMock(spec=DashboardHandler)
        handler.headers = {"Host": "localhost:8765", "X-Telemetry-Token": _security_token}
        handler.path = "/api/events"

        result = DashboardHandler.validate_request(handler)
        self.assertTrue(result)

    def test_validate_request_api_with_query_token(self) -> None:
        handler = MagicMock(spec=DashboardHandler)
        handler.headers = {"Host": "localhost:8765"}
        handler.path = f"/api/events?token={_security_token}"

        result = DashboardHandler.validate_request(handler)
        self.assertTrue(result)

    def test_validate_request_api_with_invalid_token(self) -> None:
        handler = MagicMock(spec=DashboardHandler)
        handler.headers = {"Host": "localhost:8765", "X-Telemetry-Token": "bad-token"}
        handler.path = "/api/events"

        result = DashboardHandler.validate_request(handler)
        self.assertFalse(result)
        handler.send_error.assert_called_once_with(403, "Forbidden: Invalid security token")
