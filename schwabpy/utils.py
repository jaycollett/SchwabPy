"""
Utility functions for SchwabPy library.
"""

import base64
import logging
from typing import Dict, Any
from urllib.parse import urlencode, quote

logger = logging.getLogger(__name__)


def encode_credentials(client_id: str, client_secret: str) -> str:
    """
    Base64 encode client credentials for OAuth.

    Args:
        client_id: OAuth client ID (App Key)
        client_secret: OAuth client secret (App Secret)

    Returns:
        Base64 encoded credentials string
    """
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return encoded


def build_url(base_url: str, endpoint: str, params: Dict[str, Any] = None) -> str:
    """
    Build a complete URL with query parameters.

    Args:
        base_url: Base API URL
        endpoint: API endpoint path
        params: Query parameters

    Returns:
        Complete URL string
    """
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    if params:
        # Filter out None values
        filtered_params = {k: v for k, v in params.items() if v is not None}
        if filtered_params:
            url += f"?{urlencode(filtered_params)}"

    return url


def format_symbol(symbol: str) -> str:
    """
    Format a symbol for API requests.

    Args:
        symbol: Stock or option symbol

    Returns:
        Formatted symbol
    """
    return symbol.upper().strip()


def url_encode(value: str) -> str:
    """
    URL encode a value.

    Args:
        value: Value to encode

    Returns:
        URL encoded string
    """
    return quote(value, safe='')


def setup_logging(level=logging.INFO):
    """
    Setup logging configuration for the library.

    Args:
        level: Logging level (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
