"""
Unit tests for data models.
"""

import pytest
from schwabpy.models import Position, Quote, Account, Balance, Order


class TestPosition:
    """Tests for Position model."""

    def test_position_from_dict_basic(self, sample_position_data):
        """Test basic position creation from dict - raw API data only."""
        position = Position.from_dict(sample_position_data)

        assert position.symbol == "AAPL"
        assert position.asset_type == "EQUITY"
        assert position.long_quantity == 100.0
        assert position.short_quantity == 0.0
        assert position.average_price == 150.0
        assert position.market_value == 16000.0
        assert position.current_day_profit_loss == 500.0

    def test_position_provides_raw_api_fields(self, sample_position_data):
        """Test that position provides raw API fields without calculations."""
        position = Position.from_dict(sample_position_data)

        # Should provide raw fields from API
        assert position.current_day_profit_loss == sample_position_data["currentDayProfitLoss"]
        assert position.market_value == sample_position_data["marketValue"]
        assert position.average_price == sample_position_data["averagePrice"]

        # Raw data should be available for custom calculations
        assert position.raw_data == sample_position_data

    def test_position_with_short_position(self):
        """Test position with short quantity."""
        data = {
            "instrument": {"symbol": "SPY", "assetType": "EQUITY"},
            "longQuantity": 0.0,
            "shortQuantity": 50.0,
            "averagePrice": 400.0,
            "marketValue": -19500.0,
            "currentDayProfitLoss": -500.0
        }

        position = Position.from_dict(data)

        assert position.long_quantity == 0.0
        assert position.short_quantity == 50.0
        assert position.market_value == -19500.0
        assert position.current_day_profit_loss == -500.0

    def test_position_with_missing_optional_fields(self):
        """Test position with missing optional fields."""
        data = {
            "instrument": {"symbol": "TEST", "assetType": "EQUITY"},
            "longQuantity": 100.0,
            "shortQuantity": 0.0,
            "averagePrice": 150.0,
            "marketValue": 16000.0
        }

        position = Position.from_dict(data)

        assert position.symbol == "TEST"
        assert position.long_quantity == 100.0
        assert position.current_day_profit_loss is None  # Not provided in data


class TestQuote:
    """Tests for Quote model."""

    def test_quote_from_dict_basic(self, sample_quote_data):
        """Test basic quote creation from dict."""
        quote = Quote.from_dict("AAPL", sample_quote_data)

        assert quote.symbol == "AAPL"
        assert quote.asset_type == "EQUITY"
        assert quote.last_price == 160.02
        assert quote.bid_price == 160.00
        assert quote.ask_price == 160.05
        assert quote.net_change == -0.98
        assert quote.net_percent_change == -0.61

    def test_quote_with_missing_fields(self):
        """Test quote creation with missing optional fields."""
        minimal_data = {
            "symbol": "TEST",
            "assetType": "EQUITY",
            "quote": {}
        }

        quote = Quote.from_dict("TEST", minimal_data)

        assert quote.symbol == "TEST"
        assert quote.last_price is None
        assert quote.bid_price is None
        assert quote.ask_price is None


class TestAccount:
    """Tests for Account model."""

    def test_account_from_dict_basic(self, sample_account_data):
        """Test basic account creation from dict."""
        account = Account.from_dict(sample_account_data)

        assert account.account_number == "123456789"
        assert account.account_type == "MARGIN"
        assert account.is_day_trader is False
        assert account.is_closing_only_restricted is False

    def test_account_with_missing_fields(self):
        """Test account creation with missing optional fields."""
        minimal_data = {
            "securitiesAccount": {
                "accountNumber": "999999999"
            }
        }

        account = Account.from_dict(minimal_data)

        assert account.account_number == "999999999"
        assert account.account_type is None
        assert account.is_day_trader is None


class TestBalance:
    """Tests for Balance model."""

    def test_balance_from_dict_basic(self):
        """Test basic balance creation from dict."""
        data = {
            "currentBalances": {
                "cashBalance": 10000.0,
                "liquidationValue": 50000.0,
                "buyingPower": 40000.0,
                "equity": 50000.0
            }
        }

        balance = Balance.from_dict(data)

        assert balance.cash_balance == 10000.0
        assert balance.liquidation_value == 50000.0
        assert balance.buying_power == 40000.0
        assert balance.equity == 50000.0


class TestOrder:
    """Tests for Order model."""

    def test_order_from_dict_basic(self):
        """Test basic order creation from dict."""
        data = {
            "orderId": 12345,
            "accountNumber": "123456789",
            "status": "FILLED",
            "orderType": "LIMIT",
            "session": "NORMAL",
            "duration": "DAY",
            "price": 150.00,
            "quantity": 10.0,
            "filledQuantity": 10.0,
            "remainingQuantity": 0.0
        }

        order = Order.from_dict(data)

        assert order.order_id == "12345"
        assert order.account_number == "123456789"
        assert order.status == "FILLED"
        assert order.order_type == "LIMIT"
        assert order.price == 150.00
        assert order.quantity == 10.0
