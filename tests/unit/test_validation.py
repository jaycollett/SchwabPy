"""
Unit tests for input validation functions.
"""

import pytest
from schwabpy.utils import (
    validate_symbol,
    validate_quantity,
    validate_price,
    validate_account_hash,
    validate_order_instruction,
    validate_order_type,
    validate_order_session,
    validate_order_duration,
    validate_date_format
)


class TestValidateSymbol:
    """Tests for validate_symbol function."""

    def test_valid_symbols(self):
        """Test validation of valid symbols."""
        assert validate_symbol("AAPL") == "AAPL"
        assert validate_symbol("aapl") == "AAPL"  # Should uppercase
        assert validate_symbol(" MSFT ") == "MSFT"  # Should strip
        assert validate_symbol("BRK.B") == "BRK.B"  # Dots allowed
        assert validate_symbol("$SPX") == "$SPX"  # Dollar signs allowed

    def test_invalid_empty_symbol(self):
        """Test that empty symbols are rejected."""
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            validate_symbol("")

        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            validate_symbol("   ")

    def test_invalid_symbol_type(self):
        """Test that non-string symbols are rejected."""
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            validate_symbol(None)

        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            validate_symbol(123)

    def test_invalid_symbol_too_long(self):
        """Test that overly long symbols are rejected."""
        with pytest.raises(ValueError, match="Symbol too long"):
            validate_symbol("A" * 51)

    def test_invalid_symbol_characters(self):
        """Test that symbols with invalid characters are rejected."""
        with pytest.raises(ValueError, match="Symbol contains invalid characters"):
            validate_symbol("AAPL@")

        with pytest.raises(ValueError, match="Symbol contains invalid characters"):
            validate_symbol("TEST#123")


class TestValidateQuantity:
    """Tests for validate_quantity function."""

    def test_valid_quantities(self):
        """Test validation of valid quantities."""
        assert validate_quantity(10) == 10
        assert validate_quantity(1) == 1
        assert validate_quantity(1000000) == 1000000
        assert validate_quantity(10.5) == 10  # Should convert to int

    def test_invalid_zero_quantity(self):
        """Test that zero quantity is rejected by default."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            validate_quantity(0)

    def test_valid_zero_quantity_when_allowed(self):
        """Test that zero quantity is accepted when explicitly allowed."""
        assert validate_quantity(0, allow_zero=True) == 0

    def test_invalid_negative_quantity(self):
        """Test that negative quantities are rejected."""
        with pytest.raises(ValueError, match="Quantity cannot be negative"):
            validate_quantity(-10, allow_zero=True)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            validate_quantity(-10)

    def test_invalid_quantity_type(self):
        """Test that non-numeric quantities are rejected."""
        with pytest.raises(ValueError, match="Quantity must be numeric"):
            validate_quantity("10")

    def test_invalid_quantity_too_large(self):
        """Test that excessively large quantities are rejected."""
        with pytest.raises(ValueError, match="Quantity exceeds maximum"):
            validate_quantity(1000001)


class TestValidatePrice:
    """Tests for validate_price function."""

    def test_valid_prices(self):
        """Test validation of valid prices."""
        assert validate_price(100.50) == 100.50
        assert validate_price(1) == 1.0
        assert validate_price(0.01) == 0.01

    def test_invalid_negative_price(self):
        """Test that negative prices are rejected."""
        with pytest.raises(ValueError, match="Price cannot be negative"):
            validate_price(-10.0)

    def test_invalid_zero_price(self):
        """Test that zero price is rejected by default."""
        with pytest.raises(ValueError, match="Price cannot be zero"):
            validate_price(0.0)

    def test_valid_zero_price_when_allowed(self):
        """Test that zero price is accepted when explicitly allowed."""
        assert validate_price(0.0, allow_zero=True) == 0.0

    def test_invalid_price_type(self):
        """Test that non-numeric prices are rejected."""
        with pytest.raises(ValueError, match="Price must be numeric"):
            validate_price("100.50")

    def test_invalid_price_too_large(self):
        """Test that excessively large prices are rejected."""
        with pytest.raises(ValueError, match="Price exceeds maximum"):
            validate_price(1000001.0)


class TestValidateAccountHash:
    """Tests for validate_account_hash function."""

    def test_valid_account_hashes(self):
        """Test validation of valid account hashes."""
        assert validate_account_hash("ABC123") == "ABC123"
        assert validate_account_hash(" XYZ999 ") == "XYZ999"  # Should strip

    def test_invalid_empty_account_hash(self):
        """Test that empty account hashes are rejected."""
        with pytest.raises(ValueError, match="Account hash must be a non-empty string"):
            validate_account_hash("")

        with pytest.raises(ValueError, match="Account hash cannot be empty"):
            validate_account_hash("   ")

    def test_invalid_account_hash_type(self):
        """Test that non-string account hashes are rejected."""
        with pytest.raises(ValueError, match="Account hash must be a non-empty string"):
            validate_account_hash(None)

    def test_invalid_account_hash_characters(self):
        """Test that account hashes with invalid characters are rejected."""
        with pytest.raises(ValueError, match="Invalid account hash format"):
            validate_account_hash("ABC-123")

        with pytest.raises(ValueError, match="Invalid account hash format"):
            validate_account_hash("ABC@123")


class TestValidateOrderInstruction:
    """Tests for validate_order_instruction function."""

    def test_valid_equity_instructions(self):
        """Test validation of valid equity order instructions."""
        assert validate_order_instruction("BUY", "EQUITY") == "BUY"
        assert validate_order_instruction("sell", "EQUITY") == "SELL"  # Should uppercase
        assert validate_order_instruction("BUY_TO_COVER", "EQUITY") == "BUY_TO_COVER"
        assert validate_order_instruction("SELL_SHORT", "EQUITY") == "SELL_SHORT"

    def test_valid_option_instructions(self):
        """Test validation of valid option order instructions."""
        assert validate_order_instruction("BUY_TO_OPEN", "OPTION") == "BUY_TO_OPEN"
        assert validate_order_instruction("BUY_TO_CLOSE", "OPTION") == "BUY_TO_CLOSE"
        assert validate_order_instruction("SELL_TO_OPEN", "OPTION") == "SELL_TO_OPEN"
        assert validate_order_instruction("SELL_TO_CLOSE", "OPTION") == "SELL_TO_CLOSE"

    def test_invalid_instruction_for_asset_type(self):
        """Test that equity instructions are rejected for options."""
        with pytest.raises(ValueError, match="Invalid instruction 'BUY' for OPTION"):
            validate_order_instruction("BUY", "OPTION")

    def test_invalid_instruction_value(self):
        """Test that invalid instruction values are rejected."""
        with pytest.raises(ValueError, match="Invalid instruction 'BUUY'"):
            validate_order_instruction("BUUY", "EQUITY")


class TestValidateOrderType:
    """Tests for validate_order_type function."""

    def test_valid_order_types(self):
        """Test validation of valid order types."""
        assert validate_order_type("MARKET") == "MARKET"
        assert validate_order_type("limit") == "LIMIT"  # Should uppercase
        assert validate_order_type("STOP") == "STOP"
        assert validate_order_type("STOP_LIMIT") == "STOP_LIMIT"

    def test_invalid_order_type(self):
        """Test that invalid order types are rejected."""
        with pytest.raises(ValueError, match="Invalid order type 'INVALID'"):
            validate_order_type("INVALID")


class TestValidateOrderSession:
    """Tests for validate_order_session function."""

    def test_valid_sessions(self):
        """Test validation of valid order sessions."""
        assert validate_order_session("NORMAL") == "NORMAL"
        assert validate_order_session("am") == "AM"  # Should uppercase
        assert validate_order_session("PM") == "PM"
        assert validate_order_session("SEAMLESS") == "SEAMLESS"

    def test_invalid_session(self):
        """Test that invalid sessions are rejected."""
        with pytest.raises(ValueError, match="Invalid session 'INVALID'"):
            validate_order_session("INVALID")


class TestValidateOrderDuration:
    """Tests for validate_order_duration function."""

    def test_valid_durations(self):
        """Test validation of valid order durations."""
        assert validate_order_duration("DAY") == "DAY"
        assert validate_order_duration("good_till_cancel") == "GOOD_TILL_CANCEL"  # Should uppercase
        assert validate_order_duration("FILL_OR_KILL") == "FILL_OR_KILL"

    def test_invalid_duration(self):
        """Test that invalid durations are rejected."""
        with pytest.raises(ValueError, match="Invalid duration 'INVALID'"):
            validate_order_duration("INVALID")


class TestValidateDateFormat:
    """Tests for validate_date_format function."""

    def test_valid_date_formats(self):
        """Test validation of valid date formats."""
        assert validate_date_format("2024-01-01") == "2024-01-01"
        assert validate_date_format("2024-12-31") == "2024-12-31"

    def test_invalid_date_format(self):
        """Test that invalid date formats are rejected."""
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_format("01-01-2024")

        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_format("2024/01/01")

        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_format("01/01/2024")

    def test_invalid_empty_date(self):
        """Test that empty dates are rejected."""
        with pytest.raises(ValueError, match="Date must be a non-empty string"):
            validate_date_format("")
