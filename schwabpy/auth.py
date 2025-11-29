"""
OAuth 2.0 authentication for Schwab API.
"""

import json
import logging
import os
import tempfile
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse

import requests

from .exceptions import AuthenticationError, TokenExpiredError
from .utils import encode_credentials, url_encode

logger = logging.getLogger(__name__)


class OAuthManager:
    """Manages OAuth 2.0 authentication flow and token lifecycle."""

    AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
    TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"

    # Token validity periods
    ACCESS_TOKEN_LIFETIME = 1800  # 30 minutes in seconds
    REFRESH_TOKEN_LIFETIME = 604800  # 7 days in seconds
    REQUEST_TIMEOUT = 30  # Timeout for token requests in seconds

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        token_file: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize OAuth manager.

        Args:
            client_id: OAuth client ID (App Key)
            client_secret: OAuth client secret (App Secret)
            redirect_uri: OAuth redirect URI (callback URL)
            token_file: Path to store tokens (default: .schwab_tokens.json)
            timeout: Request timeout in seconds (default: 30)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_file = Path(token_file or ".schwab_tokens.json")
        self.timeout = timeout

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._refresh_token_expiry: Optional[datetime] = None

        # Try to load existing tokens
        self._load_tokens()

    def get_authorization_url(self) -> str:
        """
        Generate the authorization URL for the user to visit.

        Returns:
            Authorization URL string
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri
        }
        auth_url = f"{self.AUTH_URL}?{urlencode(params)}"
        return auth_url

    def fetch_access_token(self, authorization_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            authorization_code: Authorization code from OAuth callback

        Returns:
            Token response dictionary

        Raises:
            AuthenticationError: If token fetch fails
        """
        # Decode the authorization code (it may be URL encoded)
        decoded_code = authorization_code.replace("%40", "@")

        headers = {
            "Authorization": f"Basic {encode_credentials(self.client_id, self.client_secret)}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "authorization_code",
            "code": decoded_code,
            "redirect_uri": self.redirect_uri
        }

        try:
            response = requests.post(
                self.TOKEN_URL,
                headers=headers,
                data=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            token_data = response.json()

            self._update_tokens(token_data)
            logger.info("Successfully obtained access token")

            return token_data

        except requests.exceptions.Timeout:
            error_msg = f"Token request timed out after {self.timeout} seconds"
            logger.error(error_msg)
            raise AuthenticationError(error_msg)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch access token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise AuthenticationError(f"Failed to fetch access token: {e}")

    def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh the access token using the refresh token.

        Returns:
            Token response dictionary

        Raises:
            AuthenticationError: If token refresh fails
        """
        if not self._refresh_token:
            raise AuthenticationError("No refresh token available")

        if self._is_refresh_token_expired():
            raise TokenExpiredError("Refresh token has expired. Re-authentication required.")

        headers = {
            "Authorization": f"Basic {encode_credentials(self.client_id, self.client_secret)}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token
        }

        try:
            response = requests.post(
                self.TOKEN_URL,
                headers=headers,
                data=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            token_data = response.json()

            self._update_tokens(token_data)
            logger.info("Successfully refreshed access token")

            return token_data

        except requests.exceptions.Timeout:
            error_msg = f"Token refresh request timed out after {self.timeout} seconds"
            logger.error(error_msg)
            raise AuthenticationError(error_msg)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to refresh access token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise AuthenticationError(f"Failed to refresh access token: {e}")

    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Valid access token

        Raises:
            AuthenticationError: If unable to get valid token
        """
        # Check if we need to refresh
        if self._should_refresh_token():
            try:
                self.refresh_access_token()
            except TokenExpiredError:
                raise AuthenticationError(
                    "Refresh token expired. Please re-authenticate using authorization flow."
                )

        if not self._access_token:
            raise AuthenticationError("No access token available. Please authenticate first.")

        return self._access_token

    def _update_tokens(self, token_data: Dict[str, Any]):
        """Update internal token state and save to file."""
        self._access_token = token_data.get("access_token")
        self._refresh_token = token_data.get("refresh_token")

        expires_in = token_data.get("expires_in", self.ACCESS_TOKEN_LIFETIME)
        self._token_expiry = datetime.now() + timedelta(seconds=expires_in)

        # Refresh token expiry (7 days from now)
        self._refresh_token_expiry = datetime.now() + timedelta(seconds=self.REFRESH_TOKEN_LIFETIME)

        self._save_tokens()

    def _should_refresh_token(self) -> bool:
        """Check if token should be refreshed (within 5 minutes of expiry)."""
        if not self._access_token or not self._token_expiry:
            return True

        # Refresh if within 5 minutes of expiry
        buffer = timedelta(minutes=5)
        return datetime.now() >= (self._token_expiry - buffer)

    def _is_refresh_token_expired(self) -> bool:
        """Check if refresh token is expired."""
        if not self._refresh_token_expiry:
            return True
        return datetime.now() >= self._refresh_token_expiry

    def _save_tokens(self):
        """Save tokens to file with secure permissions (0600)."""
        token_data = {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "token_expiry": self._token_expiry.isoformat() if self._token_expiry else None,
            "refresh_token_expiry": self._refresh_token_expiry.isoformat() if self._refresh_token_expiry else None
        }

        try:
            # Create parent directory if it doesn't exist
            self.token_file.parent.mkdir(parents=True, exist_ok=True)

            # Write to temporary file first with secure permissions
            fd, temp_path = tempfile.mkstemp(dir=self.token_file.parent, text=True)
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(token_data, f, indent=2)

                # Set secure permissions (0600 = rw-------)
                # Only owner can read/write, no permissions for group or others
                os.chmod(temp_path, 0o600)

                # Move to final location (atomic operation on most filesystems)
                shutil.move(temp_path, str(self.token_file))

                logger.debug(f"Tokens saved to {self.token_file} with secure permissions")

                # Verify permissions were set correctly
                self._check_token_file_security()

            except Exception:
                # Clean up temp file if something went wrong
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise

        except Exception as e:
            logger.warning(f"Failed to save tokens: {e}")
            raise

    def _check_token_file_security(self):
        """Verify token file has secure permissions."""
        if not self.token_file.exists():
            return

        try:
            stat_info = self.token_file.stat()
            permissions = stat_info.st_mode & 0o777

            if permissions != 0o600:
                logger.warning(
                    f"Token file has insecure permissions: {oct(permissions)}. "
                    f"Recommended: 0o600 (rw-------). "
                    f"Run: chmod 600 {self.token_file}"
                )
        except Exception as e:
            logger.debug(f"Could not check token file permissions: {e}")

    def _load_tokens(self):
        """Load tokens from file."""
        if not self.token_file.exists():
            logger.debug("No token file found")
            return

        # Check security of existing token file
        self._check_token_file_security()

        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)

            self._access_token = token_data.get("access_token")
            self._refresh_token = token_data.get("refresh_token")

            if token_data.get("token_expiry"):
                self._token_expiry = datetime.fromisoformat(token_data["token_expiry"])

            if token_data.get("refresh_token_expiry"):
                self._refresh_token_expiry = datetime.fromisoformat(token_data["refresh_token_expiry"])

            logger.info("Loaded tokens from file")

        except Exception as e:
            logger.warning(f"Failed to load tokens: {e}")

    @staticmethod
    def parse_callback_url(callback_url: str) -> str:
        """
        Extract authorization code from callback URL.

        Args:
            callback_url: The full callback URL with code parameter

        Returns:
            Authorization code

        Raises:
            ValueError: If code not found in URL
        """
        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)

        code = params.get('code')
        if not code:
            raise ValueError("Authorization code not found in callback URL")

        return code[0]
