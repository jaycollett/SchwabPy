"""
Unit tests for SchwabClient, focusing on retry logic, rate limiting,
response handling, and session lifecycle.
"""

import time
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

from schwabpy.client import SchwabClient
from schwabpy.exceptions import (
    APIError,
    BadRequestError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServerError,
    UnauthorizedError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Create a SchwabClient with mocked auth so no real tokens are needed."""
    with patch("schwabpy.client.OAuthManager") as MockAuth:
        mock_auth = MockAuth.return_value
        mock_auth._access_token = "fake_token"
        mock_auth.get_access_token.return_value = "fake_token"
        mock_auth.token_file = ".test_tokens.json"

        c = SchwabClient(
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="https://127.0.0.1",
        )
        yield c
        # Ensure session is cleaned up
        if c._session is not None:
            c.close()


@pytest.fixture
def mock_response():
    """Factory for creating mock Response objects."""
    def _make(status_code=200, json_data=None, text=""):
        resp = Mock(spec=requests.Response)
        resp.status_code = status_code
        resp.content = b"content" if json_data or text else b""
        resp.text = text or (str(json_data) if json_data else "")
        resp.headers = {}
        if json_data is not None:
            resp.json.return_value = json_data
        else:
            resp.json.side_effect = ValueError("No JSON")
        return resp
    return _make


# ---------------------------------------------------------------------------
# Retry logic tests
# ---------------------------------------------------------------------------

class TestRetryLogic:
    """Verify that POST requests are NOT retried, while GET/PUT/DELETE are."""

    def test_get_retries_on_timeout(self, client, mock_response):
        """GET requests should be retried on Timeout."""
        ok = mock_response(200, {"data": "ok"})
        client._session.request = Mock(
            side_effect=[requests.exceptions.Timeout("timeout"), ok]
        )

        result = client.get("/test")

        assert result == {"data": "ok"}
        assert client._session.request.call_count == 2

    def test_get_retries_on_connection_error(self, client, mock_response):
        """GET requests should be retried on ConnectionError."""
        ok = mock_response(200, {"data": "ok"})
        client._session.request = Mock(
            side_effect=[requests.exceptions.ConnectionError("conn err"), ok]
        )

        result = client.get("/test")

        assert result == {"data": "ok"}
        assert client._session.request.call_count == 2

    def test_get_retries_on_server_error(self, client, mock_response):
        """GET requests should be retried on 5xx ServerError."""
        err = mock_response(500, None, "Internal Server Error")
        ok = mock_response(200, {"data": "ok"})
        # First call: returns 500 (which _handle_response converts to ServerError)
        # Second call: returns 200
        client._session.request = Mock(side_effect=[err, ok])

        result = client.get("/test")

        assert result == {"data": "ok"}
        assert client._session.request.call_count == 2

    def test_post_not_retried_on_timeout(self, client):
        """POST requests must NOT be retried on Timeout (non-idempotent)."""
        client._session.request = Mock(
            side_effect=requests.exceptions.Timeout("timeout")
        )

        with pytest.raises(APIError, match="timeout"):
            client.post("/trader/v1/accounts/ABC/orders", json={"orderType": "MARKET"})

        # Should only be called once — no retry
        assert client._session.request.call_count == 1

    def test_post_not_retried_on_connection_error(self, client):
        """POST requests must NOT be retried on ConnectionError."""
        client._session.request = Mock(
            side_effect=requests.exceptions.ConnectionError("conn err")
        )

        with pytest.raises(APIError, match="connection error"):
            client.post("/trader/v1/accounts/ABC/orders", json={"orderType": "MARKET"})

        assert client._session.request.call_count == 1

    def test_post_not_retried_on_server_error(self, client, mock_response):
        """POST requests must NOT be retried on 5xx ServerError."""
        err = mock_response(500, None, "Internal Server Error")
        client._session.request = Mock(return_value=err)

        with pytest.raises(ServerError):
            client.post("/trader/v1/accounts/ABC/orders", json={"orderType": "MARKET"})

        assert client._session.request.call_count == 1

    def test_delete_retries_on_timeout(self, client, mock_response):
        """DELETE requests (idempotent) should be retried."""
        ok = mock_response(200, {"status": "cancelled"})
        client._session.request = Mock(
            side_effect=[requests.exceptions.Timeout("timeout"), ok]
        )

        result = client.delete("/trader/v1/accounts/ABC/orders/123")

        assert result == {"status": "cancelled"}
        assert client._session.request.call_count == 2

    def test_put_retries_on_timeout(self, client, mock_response):
        """PUT requests (idempotent) should be retried."""
        ok = mock_response(200, {"status": "replaced"})
        client._session.request = Mock(
            side_effect=[requests.exceptions.Timeout("timeout"), ok]
        )

        result = client.put("/trader/v1/accounts/ABC/orders/123", json={"orderType": "LIMIT"})

        assert result == {"status": "replaced"}
        assert client._session.request.call_count == 2

    def test_get_exhausts_retries(self, client):
        """GET should fail after max_retries + 1 attempts."""
        client._session.request = Mock(
            side_effect=requests.exceptions.Timeout("timeout")
        )

        with pytest.raises(APIError, match="timeout after 4 attempts"):
            client.get("/test")

        assert client._session.request.call_count == 4  # 1 + 3 retries


# ---------------------------------------------------------------------------
# Response handling tests
# ---------------------------------------------------------------------------

class TestResponseHandling:
    """Verify _handle_response maps status codes to exceptions correctly."""

    def test_200_returns_json(self, client, mock_response):
        """2xx with JSON body returns parsed data."""
        resp = mock_response(200, {"key": "value"})
        assert client._handle_response(resp) == {"key": "value"}

    def test_204_returns_empty_dict(self, client, mock_response):
        """204 No Content returns empty dict."""
        resp = mock_response(204)
        resp.content = b""
        assert client._handle_response(resp) == {}

    def test_200_empty_body_returns_empty_dict(self, client, mock_response):
        """200 with empty body returns empty dict."""
        resp = mock_response(200)
        resp.content = b""
        assert client._handle_response(resp) == {}

    def test_200_non_json_returns_text(self, client, mock_response):
        """200 with non-JSON body returns text."""
        resp = mock_response(200, text="plain text")
        resp.content = b"plain text"
        resp.json.side_effect = ValueError("Not JSON")
        assert client._handle_response(resp) == "plain text"

    def test_400_raises_bad_request(self, client, mock_response):
        """400 raises BadRequestError."""
        resp = mock_response(400, {"message": "bad input"})
        with pytest.raises(BadRequestError, match="bad input"):
            client._handle_response(resp)

    def test_401_raises_unauthorized(self, client, mock_response):
        """401 raises UnauthorizedError."""
        resp = mock_response(401, {"error": "invalid_token"})
        with pytest.raises(UnauthorizedError, match="invalid_token"):
            client._handle_response(resp)

    def test_403_raises_forbidden(self, client, mock_response):
        """403 raises ForbiddenError."""
        resp = mock_response(403, {"message": "access denied"})
        with pytest.raises(ForbiddenError, match="access denied"):
            client._handle_response(resp)

    def test_404_raises_not_found(self, client, mock_response):
        """404 raises NotFoundError."""
        resp = mock_response(404, {"message": "not found"})
        with pytest.raises(NotFoundError, match="not found"):
            client._handle_response(resp)

    def test_429_raises_rate_limit(self, client, mock_response):
        """429 raises RateLimitError."""
        resp = mock_response(429, {"message": "too many requests"})
        with pytest.raises(RateLimitError, match="too many requests"):
            client._handle_response(resp)

    def test_500_raises_server_error(self, client, mock_response):
        """500 raises ServerError."""
        resp = mock_response(500, {"message": "internal error"})
        with pytest.raises(ServerError, match="internal error"):
            client._handle_response(resp)

    def test_error_with_error_field(self, client, mock_response):
        """Error response with 'error' field instead of 'message'."""
        resp = mock_response(400, {"error": "validation_failed"})
        with pytest.raises(BadRequestError, match="validation_failed"):
            client._handle_response(resp)

    def test_error_with_plain_text(self, client, mock_response):
        """Error response with non-JSON body uses text."""
        resp = mock_response(500, text="Service Unavailable")
        resp.json.side_effect = ValueError("Not JSON")
        with pytest.raises(ServerError, match="Service Unavailable"):
            client._handle_response(resp)


# ---------------------------------------------------------------------------
# Rate limiting tests
# ---------------------------------------------------------------------------

class TestRateLimiting:
    """Verify the sliding window rate limiter."""

    def test_under_limit_no_delay(self, client):
        """Requests under the limit should not sleep."""
        with patch("time.sleep") as mock_sleep:
            for _ in range(5):
                client._check_rate_limit()
            mock_sleep.assert_not_called()

    def test_at_limit_triggers_sleep(self, client):
        """Hitting the rate limit should trigger a sleep."""
        # Set a very low limit for testing
        client._rate_limit_per_minute = 2
        client._request_times.clear()

        # Make 2 requests (fills the window)
        client._check_rate_limit()
        client._check_rate_limit()

        with patch("time.sleep") as mock_sleep:
            client._check_rate_limit()
            # Should have slept
            mock_sleep.assert_called_once()


# ---------------------------------------------------------------------------
# Session lifecycle tests
# ---------------------------------------------------------------------------

class TestSessionLifecycle:
    """Verify context manager and close() behavior."""

    def test_context_manager_closes_session(self):
        """Context manager should close the session on exit."""
        with patch("schwabpy.client.OAuthManager"):
            with SchwabClient("id", "secret") as client:
                assert client._session is not None
            assert client._session is None

    def test_close_is_idempotent(self, client):
        """Calling close() multiple times should not raise."""
        client.close()
        client.close()  # Should not raise
        assert client._session is None

    def test_request_after_close_raises(self, client):
        """Using the client after close() raises a clear error."""
        client.close()
        with pytest.raises(APIError, match="Client session is closed"):
            client.get("/test")

    def test_repr(self, client):
        """__repr__ should include client_id and auth status."""
        r = repr(client)
        assert "SchwabClient" in r
        assert "test_id" in r


# ---------------------------------------------------------------------------
# Authentication flow tests
# ---------------------------------------------------------------------------

class TestAuthenticationFlow:
    """Test authenticate/authorize methods on SchwabClient."""

    @patch("schwabpy.client.OAuthManager.parse_callback_url", return_value="code123")
    def test_authorize_from_callback(self, mock_parse, client, capsys):
        """authorize_from_callback parses URL and fetches token."""
        client.auth.fetch_access_token = Mock()
        client.auth.token_file = ".test_tokens.json"

        client.authorize_from_callback("https://127.0.0.1/?code=code123")

        mock_parse.assert_called_once_with("https://127.0.0.1/?code=code123")
        client.auth.fetch_access_token.assert_called_once_with("code123")

    def test_authorize_from_code(self, client, capsys):
        """authorize_from_code passes the code directly."""
        client.auth.fetch_access_token = Mock()
        client.auth.token_file = ".test_tokens.json"

        client.authorize_from_code("direct_code_123")

        client.auth.fetch_access_token.assert_called_once_with("direct_code_123")
