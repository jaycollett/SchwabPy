"""
Main Schwab API client.
"""

import logging
import random
import time
from collections import deque
from typing import Optional, Dict, Any

import requests

from .auth import AuthProvider, OAuthManager
from .accounts import Accounts
from .market_data import MarketData
from .orders import Orders
from .exceptions import (
    APIError,
    RateLimitError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ServerError,
    ServiceUnavailableError,
    AuthenticationError
)

logger = logging.getLogger(__name__)


class SchwabClient:
    """
    Main client for interacting with Schwab APIs.

    This client handles authentication, rate limiting, and provides
    access to all API endpoints through sub-modules.
    """

    BASE_URL = "https://api.schwabapi.com"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: str = "https://127.0.0.1",
        token_file: Optional[str] = None,
        timeout: int = 30,
        rate_limit_per_minute: int = 120,
        base_url: Optional[str] = None,
        auth: Optional[AuthProvider] = None
    ):
        """
        Initialize Schwab API client.

        Args:
            client_id: OAuth client ID (App Key from developer portal)
            client_secret: OAuth client secret (App Secret)
            redirect_uri: OAuth redirect URI (must match app settings)
            token_file: Path to store OAuth tokens (default: .schwab_tokens.json)
            timeout: Request timeout in seconds (default: 30)
            rate_limit_per_minute: Maximum requests per minute (default: 120)
            base_url: API root used for every request (default:
                https://api.schwabapi.com). Set it to a proxy that mirrors
                Schwab's /trader/v1 and /marketdata/v1 paths.
            auth: Auth provider for requests. Defaults to an OAuthManager
                built from client_id/client_secret. Pass StaticBearerAuth
                to use a proxy API key; then client_id and client_secret
                are not needed and no token file is read or written.

        Example:
            >>> client = SchwabClient(
            ...     client_id="YOUR_APP_KEY",
            ...     client_secret="YOUR_APP_SECRET",
            ...     redirect_uri="https://127.0.0.1"
            ... )
            >>> proxied = SchwabClient(
            ...     base_url="https://broker.example/api/public/v1/schwab",
            ...     auth=StaticBearerAuth("YOUR_API_KEY")
            ... )
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.timeout = timeout
        self.base_url = (base_url or self.BASE_URL).rstrip('/')

        # Initialize rate limiting
        self._rate_limit_per_minute = rate_limit_per_minute
        self._request_times = deque(maxlen=rate_limit_per_minute)

        # Initialize auth: a supplied provider, or the file-backed OAuth manager
        if auth is not None:
            self.auth = auth
        else:
            # Only the call that used to be a TypeError (no credentials at all) is rejected
            if client_id is None and client_secret is None:
                raise ValueError(
                    "client_id and client_secret are required unless an auth provider is given"
                )
            self.auth = OAuthManager(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                token_file=token_file,
                timeout=timeout
            )

        # Initialize session
        self._session = requests.Session()
        self._session.headers.update({
            'Accept': 'application/json'
            # Note: Content-Type is set per-request only for POST/PUT/PATCH
        })

        # Initialize API modules
        self.accounts = Accounts(self)
        self.market_data = MarketData(self)
        self.orders = Orders(self)

        logger.info(
            f"Schwab API client initialized (base URL: {self.base_url}, "
            f"rate limit: {rate_limit_per_minute}/min)"
        )

    def _require_oauth(self) -> OAuthManager:
        """Return the OAuth manager, or raise if a different auth provider is in use."""
        if not isinstance(self.auth, OAuthManager):
            raise AuthenticationError(
                f"OAuth sign-in is not available with {type(self.auth).__name__}"
            )
        return self.auth

    def authenticate(self):
        """
        Start the OAuth authentication flow.

        This will print the authorization URL that you need to visit
        in your browser. After authorizing, you'll be redirected to
        your callback URL with an authorization code.

        Example:
            >>> client.authenticate()
            Visit this URL to authorize: https://api.schwabapi.com/v1/oauth/...
            >>> # After visiting URL and getting redirected
            >>> client.authorize_from_callback("https://127.0.0.1/?code=...")
        """
        auth_url = self._require_oauth().get_authorization_url()
        print("\n" + "="*70)
        print("SCHWAB API AUTHENTICATION")
        print("="*70)
        print("\n1. Visit this URL in your browser:\n")
        print(f"   {auth_url}\n")
        print("2. Log in and authorize the application")
        print("3. After authorization, you'll be redirected to a URL like:")
        print(f"   {self.redirect_uri}/?code=AUTHORIZATION_CODE...")
        print("\n4. Copy the FULL redirect URL and use it with:")
        print("   client.authorize_from_callback(url)")
        print("="*70 + "\n")

    def authorize_from_callback(self, callback_url: str):
        """
        Complete authentication using the callback URL.

        Args:
            callback_url: The full URL you were redirected to after authorization

        Example:
            >>> client.authorize_from_callback("https://127.0.0.1/?code=ABC123...")
            Successfully authenticated!
        """
        try:
            code = OAuthManager.parse_callback_url(callback_url)
            self._require_oauth().fetch_access_token(code)
            print("\n✓ Successfully authenticated!")
            print(f"✓ Tokens saved to: {self.auth.token_file}\n")
            logger.info("Authentication successful")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def authorize_from_code(self, authorization_code: str):
        """
        Complete authentication using just the authorization code.

        Args:
            authorization_code: The authorization code from the callback URL

        Example:
            >>> client.authorize_from_code("ABC123...")
            Successfully authenticated!
        """
        try:
            self._require_oauth().fetch_access_token(authorization_code)
            print("\n✓ Successfully authenticated!")
            print(f"✓ Tokens saved to: {self.auth.token_file}\n")
            logger.info("Authentication successful")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def _check_rate_limit(self):
        """
        Check and enforce rate limiting.

        Sleeps if necessary to stay within rate limits.
        """
        now = time.time()

        # Remove requests older than 60 seconds
        while self._request_times and now - self._request_times[0] > 60:
            self._request_times.popleft()

        # If at limit, wait until oldest request is > 60 seconds old
        if len(self._request_times) >= self._rate_limit_per_minute:
            sleep_time = 60 - (now - self._request_times[0]) + 0.1  # Add small buffer
            if sleep_time > 0:
                logger.warning(
                    f"Rate limit reached ({self._rate_limit_per_minute}/min). "
                    f"Sleeping for {sleep_time:.2f}s"
                )
                time.sleep(sleep_time)

                # Remove old requests after sleeping
                now = time.time()
                while self._request_times and now - self._request_times[0] > 60:
                    self._request_times.popleft()

        # Record this request
        self._request_times.append(now)

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        **kwargs
    ) -> Any:
        """
        Make an authenticated API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            json: JSON body
            **kwargs: Additional arguments for requests

        Returns:
            Response data (JSON parsed or raw response)

        Raises:
            APIError: On API errors
        """
        # Enforce rate limiting
        self._check_rate_limit()

        # Get auth headers (OAuth refreshes the token here if needed)
        try:
            headers = dict(self._auth_headers())
        except AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            raise

        # Build URL by appending the endpoint to base_url (which may carry a path prefix)
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Add Content-Type for requests with body
        if method in ['POST', 'PUT', 'PATCH'] and json is not None:
            headers['Content-Type'] = 'application/json'

        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        # Make request with retry logic
        max_retries = 3
        backoff_base = 2

        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"{method} {url} (attempt {attempt + 1}/{max_retries + 1})")
                if params:
                    logger.debug(f"Query params: {params}")
                if json:
                    logger.debug(f"JSON body: {json}")
                # Redact credentials in logs - only show length
                logger.debug(
                    f"Headers: Authorization=[redacted:{len(headers.get('Authorization', ''))} chars]"
                )

                response = self._session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs
                )

                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                if response.status_code >= 400:
                    # Log error responses at warning level for debugging
                    logger.warning(f"API error response ({response.status_code}): {response.text[:500]}")
                else:
                    logger.debug(f"Response body: {response.text[:500]}")

                # Handle response
                return self._handle_response(response)

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                # These are transient errors we can retry
                is_last_attempt = (attempt == max_retries)

                if is_last_attempt:
                    logger.error(f"Request failed after {max_retries + 1} attempts: {e}")
                    error_type = "timeout" if isinstance(e, requests.exceptions.Timeout) else "connection error"
                    raise APIError(f"Request {error_type} after {max_retries + 1} attempts: {e}")

                # Calculate backoff with jitter
                sleep_time = (backoff_base ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Transient error (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {sleep_time:.2f}s"
                )
                time.sleep(sleep_time)

            except ServerError as e:
                # A proxy saying its Schwab token is unavailable will not recover
                # within our backoff window; surface it right away.
                if isinstance(e, ServiceUnavailableError) and e.error == 'token_unavailable':
                    raise

                # 5xx errors from server - retry these too
                is_last_attempt = (attempt == max_retries)

                if is_last_attempt:
                    logger.error(f"Server error persists after {max_retries + 1} attempts")
                    raise

                # Calculate backoff with jitter
                sleep_time = (backoff_base ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Server error (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {sleep_time:.2f}s"
                )
                time.sleep(sleep_time)

            except requests.exceptions.RequestException as e:
                # Other request exceptions - don't retry
                logger.error(f"Request failed: {e}")
                raise APIError(f"Request failed: {e}")

        # Should never reach here, but just in case
        raise APIError("Request failed: maximum retries exceeded")

    def _handle_response(self, response: requests.Response) -> Any:
        """
        Handle API response and errors.

        Args:
            response: Response object

        Returns:
            Parsed response data

        Raises:
            APIError: On error responses
        """
        # Log response
        logger.debug(f"Response status: {response.status_code}")

        # Success responses (2xx)
        if 200 <= response.status_code < 300:
            # Some endpoints return empty body
            if response.status_code == 204 or not response.content:
                return {}

            # Return JSON response
            try:
                return response.json()
            except ValueError:
                return response.text

        # Error responses
        error_msg = f"API error {response.status_code}"
        error_data = None
        try:
            error_data = response.json()
            if 'message' in error_data:
                error_msg = error_data['message']
            elif 'error' in error_data:
                error_msg = error_data['error']
                if error_data.get('detail'):
                    error_msg = f"{error_msg}: {error_data['detail']}"
        except ValueError:
            error_msg = response.text or error_msg
        except TypeError:
            # JSON body that is not an object (e.g. a list or string)
            pass

        # Let the auth provider replace the default 401/403 error
        if response.status_code in (401, 403):
            on_unauthorized = getattr(self.auth, 'on_unauthorized', None)
            if on_unauthorized is not None:
                on_unauthorized(response)

        # Raise specific exceptions based on status code
        if response.status_code == 400:
            raise BadRequestError(error_msg, response.status_code, response)
        elif response.status_code == 401:
            raise UnauthorizedError(error_msg, response.status_code, response)
        elif response.status_code == 403:
            raise ForbiddenError(error_msg, response.status_code, response)
        elif response.status_code == 404:
            raise NotFoundError(error_msg, response.status_code, response)
        elif response.status_code == 429:
            raise RateLimitError(error_msg, response.status_code, response)
        elif response.status_code == 503:
            raise ServiceUnavailableError(error_msg, response.status_code, response, error_data)
        elif response.status_code >= 500:
            raise ServerError(error_msg, response.status_code, response)
        else:
            raise APIError(error_msg, response.status_code, response)

    def _auth_headers(self) -> Dict[str, str]:
        """Headers from the auth provider; falls back to get_access_token() for older providers."""
        get_headers = getattr(self.auth, 'get_headers', None)
        if get_headers is not None:
            return get_headers()
        return {'Authorization': f'Bearer {self.auth.get_access_token()}'}

    def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Any:
        """Make a GET request."""
        return self._request('GET', endpoint, params=params, **kwargs)

    def post(self, endpoint: str, json: Optional[Dict] = None, **kwargs) -> Any:
        """Make a POST request."""
        return self._request('POST', endpoint, json=json, **kwargs)

    def put(self, endpoint: str, json: Optional[Dict] = None, **kwargs) -> Any:
        """Make a PUT request."""
        return self._request('PUT', endpoint, json=json, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> Any:
        """Make a DELETE request."""
        return self._request('DELETE', endpoint, **kwargs)

    def close(self):
        """Close the HTTP session and cleanup resources."""
        if self._session:
            self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.close()
        return False  # Don't suppress exceptions

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.close()
        except Exception:
            # Suppress errors in destructor
            pass

    def __repr__(self) -> str:
        """String representation of the client."""
        if isinstance(self.auth, OAuthManager):
            client_id = (self.client_id or '')[:8]
            return f"SchwabClient(client_id='{client_id}...', authenticated={bool(self.auth._access_token)})"
        return f"SchwabClient(base_url='{self.base_url}', auth={type(self.auth).__name__})"
