"""
Custom exceptions for SchwabPy library.
"""


class SchwabAPIException(Exception):
    """Base exception for all Schwab API errors."""
    pass


class AuthenticationError(SchwabAPIException):
    """Raised when authentication fails."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when the access token has expired."""
    pass


class InvalidTokenError(AuthenticationError):
    """Raised when the token is invalid."""
    pass


class APIError(SchwabAPIException):
    """Raised when the API returns an error response."""

    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""
    pass


class BadRequestError(APIError):
    """Raised when the request is malformed (400)."""
    pass


class UnauthorizedError(APIError):
    """Raised when authentication is required or failed (401)."""
    pass


class ForbiddenError(APIError):
    """Raised when access is forbidden (403)."""
    pass


class NotFoundError(APIError):
    """Raised when the resource is not found (404)."""
    pass


class ServerError(APIError):
    """Raised when the server encounters an error (5xx)."""
    pass


class ProxyAuthenticationError(AuthenticationError, APIError):
    """Raised when a Schwab API proxy rejects the static API key (401/403).

    Subclasses both AuthenticationError and APIError, so existing handlers
    for either keep catching it. ``body`` holds the proxy's parsed JSON error
    body (or None) and ``error`` its ``error`` code when present.
    """

    def __init__(self, message, status_code=None, response=None, body=None):
        super().__init__(message, status_code, response)
        self.body = body
        self.error = body.get("error") if isinstance(body, dict) else None


class ServiceUnavailableError(ServerError):
    """Raised on a 503 response.

    ``body`` holds the parsed JSON body (or None). A Schwab token broker sends
    ``state`` and ``sign_in_url`` when Schwab needs a person to sign in again;
    those are exposed as attributes, along with the ``Retry-After`` header.
    """

    def __init__(self, message, status_code=None, response=None, body=None):
        super().__init__(message, status_code, response)
        self.body = body
        data = body if isinstance(body, dict) else {}
        self.error = data.get("error")
        self.state = data.get("state")
        self.sign_in_url = data.get("sign_in_url")
        self.retry_after = response.headers.get("Retry-After") if response is not None else None
