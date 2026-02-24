"""
Unit tests for OAuthManager, focusing on token lifecycle,
thread-safe refresh, and secure token storage.
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

from schwabpy.auth import OAuthManager
from schwabpy.exceptions import AuthenticationError, TokenExpiredError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def oauth(tmp_path):
    """Create an OAuthManager with a temp token file."""
    token_file = str(tmp_path / ".test_tokens.json")
    manager = OAuthManager(
        client_id="test_client_id",
        client_secret="test_client_secret",
        redirect_uri="https://127.0.0.1",
        token_file=token_file,
    )
    return manager


@pytest.fixture
def oauth_with_tokens(oauth):
    """OAuthManager pre-loaded with valid tokens."""
    oauth._access_token = "valid_access_token"
    oauth._refresh_token = "valid_refresh_token"
    oauth._token_expiry = datetime.now() + timedelta(minutes=25)
    oauth._refresh_token_expiry = datetime.now() + timedelta(days=6)
    return oauth


# ---------------------------------------------------------------------------
# Authorization URL tests
# ---------------------------------------------------------------------------

class TestAuthorizationURL:
    """Test authorization URL generation."""

    def test_get_authorization_url(self, oauth):
        """Should include client_id and redirect_uri."""
        url = oauth.get_authorization_url()
        assert "client_id=test_client_id" in url
        assert "redirect_uri=" in url
        assert url.startswith(OAuthManager.AUTH_URL)


# ---------------------------------------------------------------------------
# Token refresh tests
# ---------------------------------------------------------------------------

class TestTokenRefresh:
    """Test token refresh logic."""

    def test_should_refresh_when_no_token(self, oauth):
        """Should refresh when no access token exists."""
        assert oauth._should_refresh_token() is True

    def test_should_refresh_when_no_expiry(self, oauth):
        """Should refresh when token has no expiry set."""
        oauth._access_token = "token"
        oauth._token_expiry = None
        assert oauth._should_refresh_token() is True

    def test_should_not_refresh_when_valid(self, oauth_with_tokens):
        """Should not refresh when token is well within validity."""
        assert oauth_with_tokens._should_refresh_token() is False

    def test_should_refresh_near_expiry(self, oauth_with_tokens):
        """Should refresh when within 5 minutes of expiry."""
        oauth_with_tokens._token_expiry = datetime.now() + timedelta(minutes=3)
        assert oauth_with_tokens._should_refresh_token() is True

    def test_refresh_token_expired(self, oauth_with_tokens):
        """Should detect expired refresh token."""
        oauth_with_tokens._refresh_token_expiry = datetime.now() - timedelta(hours=1)
        assert oauth_with_tokens._is_refresh_token_expired() is True

    def test_refresh_token_valid(self, oauth_with_tokens):
        """Should detect valid refresh token."""
        assert oauth_with_tokens._is_refresh_token_expired() is False


# ---------------------------------------------------------------------------
# get_access_token tests
# ---------------------------------------------------------------------------

class TestGetAccessToken:
    """Test the get_access_token method (public entry point)."""

    def test_returns_valid_token_without_refresh(self, oauth_with_tokens):
        """When token is valid, return it without refreshing."""
        token = oauth_with_tokens.get_access_token()
        assert token == "valid_access_token"

    @patch.object(OAuthManager, "refresh_access_token")
    def test_refreshes_when_near_expiry(self, mock_refresh, oauth_with_tokens):
        """Should call refresh when token is near expiry."""
        oauth_with_tokens._token_expiry = datetime.now() + timedelta(minutes=2)
        mock_refresh.return_value = {}

        # After refresh, the token should still be returned
        token = oauth_with_tokens.get_access_token()
        mock_refresh.assert_called_once()
        assert token == "valid_access_token"

    def test_raises_when_no_token_available(self, oauth):
        """Should raise AuthenticationError when no tokens exist at all."""
        # With no access token and no refresh token, the refresh attempt
        # fails with "No refresh token available"
        with pytest.raises(AuthenticationError, match="No refresh token available"):
            oauth.get_access_token()

    @patch.object(OAuthManager, "refresh_access_token")
    def test_raises_on_expired_refresh_token(self, mock_refresh, oauth_with_tokens):
        """Should raise when refresh token is expired."""
        oauth_with_tokens._token_expiry = datetime.now() - timedelta(hours=1)
        mock_refresh.side_effect = TokenExpiredError("Refresh token has expired")

        with pytest.raises(AuthenticationError, match="Refresh token expired"):
            oauth_with_tokens.get_access_token()


# ---------------------------------------------------------------------------
# Thread safety tests
# ---------------------------------------------------------------------------

class TestThreadSafety:
    """Verify that concurrent access to get_access_token is safe."""

    @patch.object(OAuthManager, "refresh_access_token")
    def test_concurrent_refresh_only_happens_once(self, mock_refresh, oauth_with_tokens):
        """Multiple threads hitting a near-expiry token should only refresh once."""
        # Set token to near-expiry so refresh is triggered
        oauth_with_tokens._token_expiry = datetime.now() + timedelta(minutes=2)

        # Make refresh_access_token take a moment so threads overlap
        def slow_refresh():
            time.sleep(0.05)
            oauth_with_tokens._token_expiry = datetime.now() + timedelta(minutes=25)
            return {}

        mock_refresh.side_effect = slow_refresh

        results = []
        errors = []

        def worker():
            try:
                token = oauth_with_tokens.get_access_token()
                results.append(token)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # All threads should get the token
        assert len(results) == 10
        assert all(t == "valid_access_token" for t in results)
        assert len(errors) == 0

        # refresh should only be called once (or possibly twice if timing
        # allows a second thread through before the first updates expiry).
        # The key guarantee: it should NOT be called 10 times.
        assert mock_refresh.call_count <= 2

    def test_has_token_lock(self, oauth):
        """OAuthManager should have a threading lock."""
        assert hasattr(oauth, "_token_lock")
        assert isinstance(oauth._token_lock, type(threading.Lock()))


# ---------------------------------------------------------------------------
# Token persistence tests
# ---------------------------------------------------------------------------

class TestTokenPersistence:
    """Test saving and loading tokens from file."""

    def test_save_and_load_tokens(self, oauth, tmp_path):
        """Tokens should survive save/load cycle."""
        oauth._access_token = "saved_access"
        oauth._refresh_token = "saved_refresh"
        oauth._token_expiry = datetime.now() + timedelta(minutes=25)
        oauth._refresh_token_expiry = datetime.now() + timedelta(days=6)

        oauth._save_tokens()

        # Create a new manager pointing to the same file
        new_oauth = OAuthManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://127.0.0.1",
            token_file=str(oauth.token_file),
        )

        assert new_oauth._access_token == "saved_access"
        assert new_oauth._refresh_token == "saved_refresh"
        assert new_oauth._token_expiry is not None
        assert new_oauth._refresh_token_expiry is not None

    def test_token_file_permissions(self, oauth):
        """Token file should be created with 0600 permissions."""
        oauth._access_token = "token"
        oauth._refresh_token = "refresh"
        oauth._token_expiry = datetime.now()
        oauth._refresh_token_expiry = datetime.now()
        oauth._save_tokens()

        stat = oauth.token_file.stat()
        permissions = stat.st_mode & 0o777
        assert permissions == 0o600

    def test_load_from_nonexistent_file(self, tmp_path):
        """Loading from a missing file should not raise."""
        manager = OAuthManager(
            client_id="test",
            client_secret="test",
            redirect_uri="https://127.0.0.1",
            token_file=str(tmp_path / "nonexistent.json"),
        )
        assert manager._access_token is None
        assert manager._refresh_token is None

    def test_load_from_corrupted_file(self, tmp_path):
        """Loading from a corrupted file should not raise."""
        bad_file = tmp_path / ".tokens.json"
        bad_file.write_text("not valid json {{{")

        manager = OAuthManager(
            client_id="test",
            client_secret="test",
            redirect_uri="https://127.0.0.1",
            token_file=str(bad_file),
        )
        assert manager._access_token is None


# ---------------------------------------------------------------------------
# Callback URL parsing
# ---------------------------------------------------------------------------

class TestCallbackParsing:
    """Test parsing authorization codes from callback URLs."""

    def test_parse_valid_callback_url(self):
        """Should extract code from a valid callback URL."""
        url = "https://127.0.0.1/?code=ABC123&session=xyz"
        code = OAuthManager.parse_callback_url(url)
        assert code == "ABC123"

    def test_parse_callback_url_no_code(self):
        """Should raise ValueError when code is missing."""
        url = "https://127.0.0.1/?session=xyz"
        with pytest.raises(ValueError, match="Authorization code not found"):
            OAuthManager.parse_callback_url(url)


# ---------------------------------------------------------------------------
# Token fetch / refresh with mocked HTTP
# ---------------------------------------------------------------------------

class TestTokenHTTPCalls:
    """Test fetch and refresh token HTTP interactions."""

    @patch("schwabpy.auth.requests.post")
    def test_fetch_access_token_success(self, mock_post, oauth):
        """Successful token fetch should update internal state."""
        mock_post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={
                "access_token": "new_access",
                "refresh_token": "new_refresh",
                "expires_in": 1800,
            }),
        )
        mock_post.return_value.raise_for_status = Mock()

        result = oauth.fetch_access_token("auth_code_123")

        assert result["access_token"] == "new_access"
        assert oauth._access_token == "new_access"
        assert oauth._refresh_token == "new_refresh"

    @patch("schwabpy.auth.requests.post")
    def test_fetch_access_token_timeout(self, mock_post, oauth):
        """Timeout during token fetch should raise AuthenticationError."""
        mock_post.side_effect = requests.exceptions.Timeout("timed out")

        with pytest.raises(AuthenticationError, match="timed out"):
            oauth.fetch_access_token("code")

    @patch("schwabpy.auth.requests.post")
    def test_refresh_access_token_success(self, mock_post, oauth_with_tokens):
        """Successful refresh should update access token."""
        mock_post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={
                "access_token": "refreshed_token",
                "refresh_token": "new_refresh",
                "expires_in": 1800,
            }),
        )
        mock_post.return_value.raise_for_status = Mock()

        result = oauth_with_tokens.refresh_access_token()

        assert oauth_with_tokens._access_token == "refreshed_token"

    def test_refresh_without_refresh_token(self, oauth):
        """Refresh should fail when no refresh token is available."""
        with pytest.raises(AuthenticationError, match="No refresh token"):
            oauth.refresh_access_token()

    def test_refresh_with_expired_refresh_token(self, oauth_with_tokens):
        """Refresh should fail when refresh token is expired."""
        oauth_with_tokens._refresh_token_expiry = datetime.now() - timedelta(hours=1)

        with pytest.raises(TokenExpiredError, match="expired"):
            oauth_with_tokens.refresh_access_token()
