"""
Pytest configuration and shared fixtures.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_schwab_client():
    """Create a mock Schwab client for testing."""
    from schwabpy.client import SchwabClient

    # Create a mock client without actually initializing OAuth
    client = Mock(spec=SchwabClient)
    client.timeout = 30
    client._rate_limit_per_minute = 120
    client.client_id = "test_client_id"
    client.client_secret = "test_client_secret"

    return client


@pytest.fixture
def temp_token_file(tmp_path):
    """Create a temporary token file path."""
    return tmp_path / ".test_tokens.json"


@pytest.fixture
def sample_position_data():
    """Sample position data from Schwab API."""
    return {
        "instrument": {
            "symbol": "AAPL",
            "assetType": "EQUITY"
        },
        "longQuantity": 100.0,
        "shortQuantity": 0.0,
        "averagePrice": 150.0,
        "marketValue": 16000.0,
        "currentDayProfitLoss": 500.0
    }


@pytest.fixture
def sample_quote_data():
    """Sample quote data from Schwab API."""
    return {
        "symbol": "AAPL",
        "assetType": "EQUITY",
        "quote": {
            "bidPrice": 160.00,
            "askPrice": 160.05,
            "lastPrice": 160.02,
            "bidSize": 100,
            "askSize": 200,
            "totalVolume": 1000000,
            "highPrice": 162.00,
            "lowPrice": 158.00,
            "openPrice": 159.00,
            "closePrice": 161.00,
            "netChange": -0.98,
            "netPercentChange": -0.61
        }
    }


@pytest.fixture
def sample_account_data():
    """Sample account data from Schwab API."""
    return {
        "securitiesAccount": {
            "accountNumber": "123456789",
            "type": "MARGIN",
            "isDayTrader": False,
            "isClosingOnlyRestricted": False
        }
    }
