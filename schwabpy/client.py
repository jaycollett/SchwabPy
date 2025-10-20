"""
Main Schwab API client.
"""

import logging
import time
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import requests

from .auth import OAuthManager
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
        client_id: str,
        client_secret: str,
        redirect_uri: str = "https://127.0.0.1",
        token_file: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Schwab API client.

        Args:
            client_id: OAuth client ID (App Key from developer portal)
            client_secret: OAuth client secret (App Secret)
            redirect_uri: OAuth redirect URI (must match app settings)
            token_file: Path to store OAuth tokens (default: .schwab_tokens.json)
            timeout: Request timeout in seconds (default: 30)

        Example:
            >>> client = SchwabClient(
            ...     client_id="YOUR_APP_KEY",
            ...     client_secret="YOUR_APP_SECRET",
            ...     redirect_uri="https://127.0.0.1"
            ... )
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.timeout = timeout

        # Initialize OAuth manager
        self.auth = OAuthManager(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            token_file=token_file
        )

        # Initialize session
        self._session = requests.Session()
        self._session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

        # Initialize API modules
        self.accounts = Accounts(self)
        self.market_data = MarketData(self)
        self.orders = Orders(self)

        logger.info("Schwab API client initialized")

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
        auth_url = self.auth.get_authorization_url()
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
            self.auth.fetch_access_token(code)
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
            self.auth.fetch_access_token(authorization_code)
            print("\n✓ Successfully authenticated!")
            print(f"✓ Tokens saved to: {self.auth.token_file}\n")
            logger.info("Authentication successful")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

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
        # Get valid access token (will refresh if needed)
        try:
            access_token = self.auth.get_access_token()
        except AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            raise

        # Build URL
        url = urljoin(self.BASE_URL, endpoint.lstrip('/'))

        # Set authorization header
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        # Make request
        try:
            logger.info(f"{method} {url}")
            if params:
                logger.info(f"Query params: {params}")
            if json:
                logger.info(f"JSON body: {json}")
            logger.info(f"Headers: Authorization=Bearer {access_token[:20]}...")

            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )

            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            try:
                logger.info(f"Response body: {response.text[:500]}")
            except:
                pass

            # Handle response
            return self._handle_response(response)

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {url}")
            raise APIError(f"Request timeout after {self.timeout} seconds")

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise APIError(f"Connection error: {e}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise APIError(f"Request failed: {e}")

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
        try:
            error_data = response.json()
            if 'message' in error_data:
                error_msg = error_data['message']
            elif 'error' in error_data:
                error_msg = error_data['error']
        except ValueError:
            error_msg = response.text or error_msg

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
        elif response.status_code >= 500:
            raise ServerError(error_msg, response.status_code, response)
        else:
            raise APIError(error_msg, response.status_code, response)

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

    def __repr__(self) -> str:
        """String representation of the client."""
        return f"SchwabClient(client_id='{self.client_id[:8]}...', authenticated={bool(self.auth._access_token)})"
