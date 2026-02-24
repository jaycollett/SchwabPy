"""
Utility functions for SchwabPy library.
"""

import base64
import logging
import re
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Valid values for order parameters
EQUITY_INSTRUCTIONS = {"BUY", "SELL", "BUY_TO_COVER", "SELL_SHORT"}
OPTION_INSTRUCTIONS = {"BUY_TO_OPEN", "BUY_TO_CLOSE", "SELL_TO_OPEN", "SELL_TO_CLOSE"}
ORDER_TYPES = {"MARKET", "LIMIT", "STOP", "STOP_LIMIT", "NET_DEBIT", "NET_CREDIT"}
ORDER_SESSIONS = {"NORMAL", "AM", "PM", "SEAMLESS"}
ORDER_DURATIONS = {"DAY", "GOOD_TILL_CANCEL", "FILL_OR_KILL", "IMMEDIATE_OR_CANCEL"}


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



def format_symbol(symbol: str) -> str:
    """
    Format a symbol for API requests.

    Args:
        symbol: Stock or option symbol

    Returns:
        Formatted and validated symbol

    Raises:
        ValueError: If symbol is invalid
    """
    return validate_symbol(symbol)


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


def validate_symbol(symbol: str) -> str:
    """
    Validate and format a trading symbol.

    Args:
        symbol: Stock or option symbol

    Returns:
        Validated and formatted symbol

    Raises:
        ValueError: If symbol is invalid
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string")

    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError("Symbol cannot be empty or whitespace")

    if len(symbol) > 50:  # Reasonable limit (options symbols can be long)
        raise ValueError(f"Symbol too long (max 50 characters): {symbol}")

    # Allow alphanumeric, spaces (for options), dots, hyphens, and dollar signs
    if not re.match(r'^[A-Z0-9 .$-]+$', symbol):
        raise ValueError(f"Symbol contains invalid characters: {symbol}")

    return symbol


def validate_quantity(quantity: int, allow_zero: bool = False) -> int:
    """
    Validate order quantity.

    Args:
        quantity: Number of shares/contracts
        allow_zero: Whether to allow zero quantity

    Returns:
        Validated quantity

    Raises:
        ValueError: If quantity is invalid
    """
    if not isinstance(quantity, (int, float)):
        raise ValueError(f"Quantity must be numeric, got {type(quantity).__name__}")

    quantity = int(quantity)

    if allow_zero and quantity < 0:
        raise ValueError(f"Quantity cannot be negative: {quantity}")
    elif not allow_zero and quantity <= 0:
        raise ValueError(f"Quantity must be positive: {quantity}")

    if quantity > 1000000:  # Reasonable upper limit
        raise ValueError(f"Quantity exceeds maximum (1,000,000): {quantity}")

    return quantity


def validate_price(price: float, allow_zero: bool = False) -> float:
    """
    Validate price value.

    Args:
        price: Price value
        allow_zero: Whether to allow zero price

    Returns:
        Validated price

    Raises:
        ValueError: If price is invalid
    """
    if not isinstance(price, (int, float)):
        raise ValueError(f"Price must be numeric, got {type(price).__name__}")

    price = float(price)

    if price < 0:
        raise ValueError(f"Price cannot be negative: {price}")

    if not allow_zero and price == 0:
        raise ValueError("Price cannot be zero")

    if price > 1000000:  # Reasonable upper limit
        raise ValueError(f"Price exceeds maximum (1,000,000): {price}")

    return price


def validate_account_hash(account_hash: str) -> str:
    """
    Validate account hash format.

    Args:
        account_hash: Account hash/number from Schwab API

    Returns:
        Validated account hash

    Raises:
        ValueError: If account hash is invalid
    """
    if not account_hash or not isinstance(account_hash, str):
        raise ValueError("Account hash must be a non-empty string")

    account_hash = account_hash.strip()

    if not account_hash:
        raise ValueError("Account hash cannot be empty or whitespace")

    # Schwab account hashes are typically alphanumeric
    if not re.match(r'^[A-Za-z0-9]+$', account_hash):
        raise ValueError(f"Invalid account hash format: {account_hash}")

    if len(account_hash) > 100:  # Reasonable limit
        raise ValueError(f"Account hash too long: {account_hash}")

    return account_hash


def validate_order_instruction(instruction: str, asset_type: str = "EQUITY") -> str:
    """
    Validate order instruction.

    Args:
        instruction: Order instruction (BUY, SELL, etc.)
        asset_type: Asset type (EQUITY or OPTION)

    Returns:
        Validated instruction

    Raises:
        ValueError: If instruction is invalid
    """
    if not instruction or not isinstance(instruction, str):
        raise ValueError("Instruction must be a non-empty string")

    instruction = instruction.upper().strip()

    if asset_type.upper() == "OPTION":
        valid_instructions = OPTION_INSTRUCTIONS
    else:
        valid_instructions = EQUITY_INSTRUCTIONS

    if instruction not in valid_instructions:
        raise ValueError(
            f"Invalid instruction '{instruction}' for {asset_type}. "
            f"Must be one of: {', '.join(sorted(valid_instructions))}"
        )

    return instruction


def validate_order_type(order_type: str) -> str:
    """
    Validate order type.

    Args:
        order_type: Order type (MARKET, LIMIT, etc.)

    Returns:
        Validated order type

    Raises:
        ValueError: If order type is invalid
    """
    if not order_type or not isinstance(order_type, str):
        raise ValueError("Order type must be a non-empty string")

    order_type = order_type.upper().strip()

    if order_type not in ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(ORDER_TYPES))}"
        )

    return order_type


def validate_order_session(session: str) -> str:
    """
    Validate order session.

    Args:
        session: Order session (NORMAL, AM, PM, SEAMLESS)

    Returns:
        Validated session

    Raises:
        ValueError: If session is invalid
    """
    if not session or not isinstance(session, str):
        raise ValueError("Session must be a non-empty string")

    session = session.upper().strip()

    if session not in ORDER_SESSIONS:
        raise ValueError(
            f"Invalid session '{session}'. "
            f"Must be one of: {', '.join(sorted(ORDER_SESSIONS))}"
        )

    return session


def validate_order_duration(duration: str) -> str:
    """
    Validate order duration.

    Args:
        duration: Order duration (DAY, GOOD_TILL_CANCEL, etc.)

    Returns:
        Validated duration

    Raises:
        ValueError: If duration is invalid
    """
    if not duration or not isinstance(duration, str):
        raise ValueError("Duration must be a non-empty string")

    duration = duration.upper().strip()

    if duration not in ORDER_DURATIONS:
        raise ValueError(
            f"Invalid duration '{duration}'. "
            f"Must be one of: {', '.join(sorted(ORDER_DURATIONS))}"
        )

    return duration


def validate_date_format(date_str: str, format_desc: str = "yyyy-MM-dd") -> str:
    """
    Validate date string format.

    Args:
        date_str: Date string to validate
        format_desc: Description of expected format

    Returns:
        Validated date string

    Raises:
        ValueError: If date format is invalid
    """
    if not date_str or not isinstance(date_str, str):
        raise ValueError(f"Date must be a non-empty string in format {format_desc}")

    date_str = date_str.strip()

    # Basic validation for yyyy-MM-dd format
    # Also accept ISO 8601 format with time component (YYYY-MM-DDTHH:MM:SS.sssZ)
    if format_desc == "yyyy-MM-dd":
        if not re.match(r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}\.\d{3}Z)?$', date_str):
            raise ValueError(
                f"Invalid date format: {date_str}. Expected format: yyyy-MM-dd or yyyy-MM-ddTHH:MM:SS.sssZ"
            )

    return date_str
