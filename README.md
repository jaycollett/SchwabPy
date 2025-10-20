# SchwabPy

A Python library for accessing the Charles Schwab Trading and Market Data APIs. This library provides a simple and intuitive interface for retrieving market data, managing accounts, viewing portfolios, and placing trades.

## Features

- 🔐 **OAuth 2.0 Authentication** - Automatic token management and refresh
- 📊 **Market Data** - Real-time quotes, price history, option chains, and more
- 💼 **Account Management** - View accounts, positions, balances, and transactions
- 📈 **Trading** - Place, modify, and cancel orders (equities and options)
- 🔄 **Auto Token Refresh** - Tokens are automatically refreshed when needed
- 🎯 **Type Hints** - Full type hint support for better IDE integration
- 📝 **Comprehensive Documentation** - Clear examples and API references

## Installation

```bash
pip install -r requirements.txt
```

Or install from source:

```bash
git clone https://github.com/yourusername/schwabpy.git
cd schwabpy
pip install -e .
```

## Prerequisites

Before using this library, you need to:

1. **Create a Schwab Developer Account**: Visit [Schwab Developer Portal](https://developer.schwab.com)
2. **Register an Application**: Create an app to get your App Key and App Secret
3. **Set Redirect URI**: Configure your app's callback URL (e.g., `https://127.0.0.1`)

## Quick Start

### 1. Authentication

First, authenticate with the Schwab API:

```python
from schwabpy import SchwabClient

# Initialize the client
client = SchwabClient(
    client_id="YOUR_APP_KEY",
    client_secret="YOUR_APP_SECRET",
    redirect_uri="https://127.0.0.1"
)

# Start authentication flow
client.authenticate()
# This will print a URL - visit it in your browser and authorize

# After authorization, you'll be redirected to a URL like:
# https://127.0.0.1/?code=AUTHORIZATION_CODE&session=...

# Complete authentication with the callback URL
client.authorize_from_callback("PASTE_FULL_CALLBACK_URL_HERE")
```

**Note**: After first authentication, tokens are saved locally and automatically refreshed. You won't need to re-authenticate for 7 days.

### 2. Get Stock Quotes

```python
from schwabpy import SchwabClient

client = SchwabClient(
    client_id="YOUR_APP_KEY",
    client_secret="YOUR_APP_SECRET"
)

# Get a single quote
quote = client.market_data.get_quote("AAPL")
print(f"{quote.symbol}: ${quote.last_price}")
print(f"Change: {quote.net_change} ({quote.net_percent_change}%)")

# Get multiple quotes
quotes = client.market_data.get_quotes(["AAPL", "MSFT", "GOOGL"])
for symbol, quote in quotes.items():
    print(f"{symbol}: ${quote.last_price}")
```

### 3. View Portfolio Holdings

```python
# Get account numbers
accounts = client.accounts.get_account_numbers()
account_hash = accounts[0]['hashValue']

# Get account balance
balance = client.accounts.get_balance(account_hash)
print(f"Cash Balance: ${balance.cash_balance:,.2f}")
print(f"Buying Power: ${balance.buying_power:,.2f}")

# Get positions
positions = client.accounts.get_positions(account_hash)
for position in positions:
    print(f"{position.symbol}: {position.quantity} shares @ ${position.average_price}")
    if position.unrealized_pl:
        print(f"  P&L: ${position.unrealized_pl:.2f} ({position.unrealized_pl_percent:.2f}%)")
```

### 4. Get Price History

```python
# Get daily price history for the last month
history = client.market_data.get_price_history(
    symbol="AAPL",
    period_type="month",
    period=1,
    frequency_type="daily",
    frequency=1
)

candles = history.get('candles', [])
for candle in candles[-5:]:  # Last 5 days
    print(f"Date: {candle['datetime']}, Close: ${candle['close']}")
```

### 5. Get Option Chains

```python
# Get option chain for a stock
chain = client.market_data.get_option_chain(
    symbol="AAPL",
    contract_type="CALL",
    strike_count=10  # 10 strikes above and below current price
)

print(f"Underlying: {chain.symbol} @ ${chain.underlying_price}")
print(f"Available expirations: {len(chain.call_exp_date_map)}")
```

### 6. Place an Order

```python
from schwabpy.orders import Orders

# Get account hash
accounts = client.accounts.get_account_numbers()
account_hash = accounts[0]['hashValue']

# Build a simple market order
order = Orders.build_equity_order(
    symbol="AAPL",
    quantity=10,
    instruction="BUY",
    order_type="MARKET"
)

# Place the order
result = client.orders.place_order(account_hash, order)
print("Order placed successfully!")

# Or build a limit order
order = Orders.build_equity_order(
    symbol="AAPL",
    quantity=10,
    instruction="BUY",
    order_type="LIMIT",
    price=150.00
)
```

## API Reference

### Market Data

```python
# Quotes
quote = client.market_data.get_quote("AAPL")
quotes = client.market_data.get_quotes(["AAPL", "MSFT"])

# Price History
history = client.market_data.get_price_history(
    symbol="AAPL",
    period_type="month",
    period=1,
    frequency_type="daily",
    frequency=1
)

# Option Chains
chain = client.market_data.get_option_chain(
    symbol="AAPL",
    contract_type="CALL",
    strike_count=10
)

# Option Expirations
expirations = client.market_data.get_option_expiration_chain("AAPL")

# Search Instruments
results = client.market_data.search_instruments(
    symbol="tech",
    projection="desc-search"
)

# Get Instrument by CUSIP
instrument = client.market_data.get_instrument("037833100")  # AAPL

# Market Hours
hours = client.market_data.get_market_hours(["equity", "option"])

# Market Movers
movers = client.market_data.get_movers("$SPX", sort="PERCENT_CHANGE_UP")
```

### Accounts

```python
# Account Numbers
accounts = client.accounts.get_account_numbers()

# Account Details
account = client.accounts.get_account(account_hash, fields="positions")

# All Accounts
all_accounts = client.accounts.get_accounts(fields="positions")

# Positions
positions = client.accounts.get_positions(account_hash)

# Balance
balance = client.accounts.get_balance(account_hash)

# Orders
orders = client.accounts.get_orders(account_hash, status="WORKING")
order = client.accounts.get_order(account_hash, order_id)
all_orders = client.accounts.get_all_orders(status="FILLED")

# Transactions
transactions = client.accounts.get_transactions(
    account_hash,
    start_date="2024-01-01",
    end_date="2024-01-31"
)
transaction = client.accounts.get_transaction(account_hash, transaction_id)

# User Preferences (includes streamer info)
prefs = client.accounts.get_user_preference()
```

### Orders

```python
from schwabpy.orders import Orders

# Place Order
order = Orders.build_equity_order("AAPL", 10, "BUY", "MARKET")
result = client.orders.place_order(account_hash, order)

# Replace Order
new_order = Orders.build_equity_order("AAPL", 10, "BUY", "LIMIT", price=150.00)
result = client.orders.replace_order(account_hash, order_id, new_order)

# Cancel Order
result = client.orders.cancel_order(account_hash, order_id)

# Build Option Order
option_order = Orders.build_option_order(
    symbol="AAPL 240315C00150000",
    quantity=1,
    instruction="BUY_TO_OPEN",
    order_type="LIMIT",
    price=5.50
)

# Build Spread Order
legs = [
    {"symbol": "AAPL 240315C00150000", "quantity": 1, "instruction": "BUY_TO_OPEN"},
    {"symbol": "AAPL 240315C00155000", "quantity": 1, "instruction": "SELL_TO_OPEN"}
]
spread = Orders.build_spread_order(legs, "NET_DEBIT", price=2.50)
```

## Data Models

The library provides clean data models for API responses:

- **Account**: Account information
- **Position**: Portfolio position
- **Balance**: Account balance details
- **Quote**: Real-time quote data
- **Instrument**: Financial instrument details
- **Order**: Order information
- **OptionChain**: Option chain data

All models include:
- Clean attribute access (e.g., `quote.last_price`)
- Raw data access (`.raw_data` property)
- Type hints for better IDE support

## Authentication Details

### OAuth 2.0 Flow

SchwabPy uses OAuth 2.0 for authentication:

1. **Authorization**: User authorizes the app via browser
2. **Token Exchange**: Authorization code is exchanged for tokens
3. **Auto Refresh**: Access tokens (30 min) are automatically refreshed using refresh tokens (7 days)
4. **Token Storage**: Tokens are securely stored locally in `.schwab_tokens.json`

### Token Lifecycle

- **Access Token**: Valid for 30 minutes, automatically refreshed
- **Refresh Token**: Valid for 7 days, used to get new access tokens
- After 7 days, you'll need to re-authenticate through the browser

### Security Best Practices

1. **Never commit tokens**: Add `.schwab_tokens.json` to `.gitignore`
2. **Keep secrets secure**: Don't hardcode App Key/Secret in code
3. **Use environment variables**: Store credentials in env vars or config files

```python
import os

client = SchwabClient(
    client_id=os.getenv("SCHWAB_APP_KEY"),
    client_secret=os.getenv("SCHWAB_APP_SECRET"),
    redirect_uri="https://127.0.0.1"
)
```

## Rate Limits

The Schwab API has rate limits:

- **Order endpoints**: 0-120 requests per minute per account (configured per app)
- **Market data**: Generally higher limits
- **Account data**: Standard REST API limits

The library will raise `RateLimitError` when limits are exceeded.

## Error Handling

```python
from schwabpy import SchwabClient
from schwabpy.exceptions import (
    AuthenticationError,
    RateLimitError,
    APIError
)

try:
    quote = client.market_data.get_quote("AAPL")
except AuthenticationError:
    print("Authentication failed - please re-authenticate")
except RateLimitError:
    print("Rate limit exceeded - wait before retrying")
except APIError as e:
    print(f"API error: {e}")
```

## Examples

Check the `examples/` directory for complete examples:

- `01_authentication.py` - OAuth authentication flow
- `02_get_quotes.py` - Get stock quotes
- `03_get_portfolio.py` - View portfolio holdings

## Development

### Project Structure

```
schwabpy/
├── __init__.py          # Package initialization
├── auth.py              # OAuth 2.0 authentication
├── client.py            # Main API client
├── accounts.py          # Account operations
├── market_data.py       # Market data operations
├── orders.py            # Order management
├── models.py            # Data models
├── exceptions.py        # Custom exceptions
└── utils.py             # Utility functions
```

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

⚠️ **Important**: This library is for educational purposes. Always test with small amounts and paper trading accounts first.

- Not officially affiliated with Charles Schwab
- Use at your own risk
- No warranty provided
- Review all orders carefully before submission

## Resources

- [Schwab Developer Portal](https://developer.schwab.com)
- [Schwab API Documentation](https://developer.schwab.com/products)
- Market Data API Documentation (included in downloads)
- Trader API Documentation (included in downloads)

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review example scripts

---

**Happy Trading! 📈**
