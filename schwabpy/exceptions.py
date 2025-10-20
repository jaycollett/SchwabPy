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
