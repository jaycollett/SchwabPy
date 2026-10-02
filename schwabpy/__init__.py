"""
SchwabPy - Python library for Charles Schwab API

A simple and intuitive Python library for accessing Charles Schwab's
trading and market data APIs.
"""

from .client import SchwabClient
from .auth import AuthProvider, OAuthManager, StaticBearerAuth
from .models import Account, Position, Balance, Quote, Instrument, Order, OptionChain
from .exceptions import (
    SchwabAPIException,
    AuthenticationError,
    TokenExpiredError,
    InvalidTokenError,
    APIError,
    RateLimitError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ServerError,
    ServiceUnavailableError,
    ProxyAuthenticationError
)

__version__ = "2.1.0"
__author__ = "SchwabPy Contributors"
__all__ = [
    # Main client
    "SchwabClient",
    # Auth
    "AuthProvider",
    "OAuthManager",
    "StaticBearerAuth",
    # Models
    "Account",
    "Position",
    "Balance",
    "Quote",
    "Instrument",
    "Order",
    "OptionChain",
    # Exceptions
    "SchwabAPIException",
    "AuthenticationError",
    "TokenExpiredError",
    "InvalidTokenError",
    "APIError",
    "RateLimitError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ServerError",
    "ServiceUnavailableError",
    "ProxyAuthenticationError",
]
