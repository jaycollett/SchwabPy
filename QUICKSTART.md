# SchwabPy Quick Start Guide

## 1. Initial Setup (5 minutes)

### Install Dependencies
```bash
cd SchwabPy
pip install -r requirements.txt
```

### Get Your Credentials
1. Go to https://developer.schwab.com
2. Create/register an application
3. Note your **App Key** (Client ID) and **App Secret** (Client Secret)
4. Set redirect URI to `https://127.0.0.1`

## 2. First Authentication

Create a file `authenticate.py`:

```python
from schwabpy import SchwabClient

client = SchwabClient(
    client_id="YOUR_APP_KEY_HERE",
    client_secret="YOUR_APP_SECRET_HERE",
    redirect_uri="https://127.0.0.1"
)

# Start auth flow
client.authenticate()

# Copy the printed URL, visit it in browser, authorize
# You'll be redirected to: https://127.0.0.1/?code=...

# Paste the FULL redirect URL when prompted
callback_url = input("Paste callback URL: ")
client.authorize_from_callback(callback_url)

print("✓ Authenticated! Tokens saved to .schwab_tokens.json")
```

Run it:
```bash
python authenticate.py
```

## 3. Get Stock Quotes

Create `get_quotes.py`:

```python
from schwabpy import SchwabClient

# After first auth, tokens are auto-loaded
client = SchwabClient(
    client_id="YOUR_APP_KEY",
    client_secret="YOUR_APP_SECRET"
)

# Single quote
quote = client.market_data.get_quote("AAPL")
print(f"{quote.symbol}: ${quote.last_price:.2f}")

# Multiple quotes
quotes = client.market_data.get_quotes(["AAPL", "MSFT", "GOOGL"])
for symbol, quote in quotes.items():
    print(f"{symbol}: ${quote.last_price:.2f} ({quote.net_percent_change:+.2f}%)")
```

## 4. View Your Portfolio

Create `view_portfolio.py`:

```python
from schwabpy import SchwabClient

client = SchwabClient(
    client_id="YOUR_APP_KEY",
    client_secret="YOUR_APP_SECRET"
)

# Get accounts
accounts = client.accounts.get_account_numbers()
account_hash = accounts[0]['hashValue']

# Get balance
balance = client.accounts.get_balance(account_hash)
print(f"Cash: ${balance.cash_balance:,.2f}")
print(f"Buying Power: ${balance.buying_power:,.2f}")

# Get positions
positions = client.accounts.get_positions(account_hash)
for pos in positions:
    print(f"{pos.symbol}: {pos.quantity} @ ${pos.average_price:.2f}")
```

## 5. Common Tasks

### Get Price History
```python
history = client.market_data.get_price_history(
    "AAPL",
    period_type="month",
    period=1,
    frequency_type="daily"
)
candles = history['candles']
print(f"Got {len(candles)} days of data")
```

### Get Option Chain
```python
chain = client.market_data.get_option_chain(
    "AAPL",
    contract_type="CALL",
    strike_count=5
)
print(f"Underlying: ${chain.underlying_price}")
```

### Search for Stocks
```python
results = client.market_data.search_instruments(
    "technology",
    projection="desc-search"
)
for symbol, instrument in results.items():
    print(f"{symbol}: {instrument.description}")
```

### Place an Order (BE CAREFUL!)
```python
from schwabpy.orders import Orders

# Build order
order = Orders.build_equity_order(
    symbol="AAPL",
    quantity=1,
    instruction="BUY",
    order_type="LIMIT",
    price=150.00
)

# Place order (REAL MONEY!)
# result = client.orders.place_order(account_hash, order)
```

## 6. Important Notes

### Token Management
- First auth: Requires browser interaction
- After that: Tokens auto-refresh for 7 days
- After 7 days: Re-authenticate via browser
- Tokens stored in: `.schwab_tokens.json`

### Security
```python
# Use environment variables
import os

client = SchwabClient(
    client_id=os.getenv("SCHWAB_APP_KEY"),
    client_secret=os.getenv("SCHWAB_APP_SECRET")
)
```

Add to `.gitignore`:
```
.schwab_tokens.json
*.env
```

### Error Handling
```python
from schwabpy.exceptions import APIError, AuthenticationError

try:
    quote = client.market_data.get_quote("AAPL")
except AuthenticationError:
    print("Need to re-authenticate")
    client.authenticate()
except APIError as e:
    print(f"API Error: {e}")
```

## 7. Next Steps

- Read full README.md for complete API reference
- Check examples/ directory for more examples
- Review Schwab API docs for endpoint details
- Test with paper trading account first!

## Troubleshooting

### "Authentication failed"
- Check App Key/Secret are correct
- Verify redirect URI matches exactly
- Make sure you copied full callback URL

### "Token expired"
- Run authentication flow again
- Refresh tokens expire after 7 days

### "Rate limit exceeded"
- Wait before retrying
- Check your app's rate limit settings
- Reduce request frequency

## Quick Reference

```python
# Initialize
from schwabpy import SchwabClient
client = SchwabClient(client_id="...", client_secret="...")

# Market Data
client.market_data.get_quote("AAPL")
client.market_data.get_quotes(["AAPL", "MSFT"])
client.market_data.get_price_history("AAPL", period_type="month", period=1)
client.market_data.get_option_chain("AAPL")
client.market_data.search_instruments("tech", "desc-search")

# Accounts
client.accounts.get_account_numbers()
client.accounts.get_accounts(fields="positions")
client.accounts.get_balance(account_hash)
client.accounts.get_positions(account_hash)
client.accounts.get_orders(account_hash)

# Orders
from schwabpy.orders import Orders
order = Orders.build_equity_order("AAPL", 10, "BUY", "MARKET")
client.orders.place_order(account_hash, order)
```

---

**Ready to start? Run `python authenticate.py` first!**
