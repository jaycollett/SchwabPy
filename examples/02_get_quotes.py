"""
Example: Get stock quotes

This example shows how to get real-time quotes for stocks.
"""

from schwabpy import SchwabClient

# Initialize client (will use saved tokens from previous authentication)
client = SchwabClient(
    client_id="YOUR_APP_KEY",
    client_secret="YOUR_APP_SECRET",
    redirect_uri="https://127.0.0.1"
)

# Get a single quote
print("=" * 70)
print("Getting quote for AAPL...")
print("=" * 70)

quote = client.market_data.get_quote("AAPL")
print(f"\n{quote.symbol} - {quote.asset_type}")
print(f"  Last Price: ${quote.last_price:.2f}")
print(f"  Bid/Ask: ${quote.bid_price:.2f} / ${quote.ask_price:.2f}")
print(f"  Day Range: ${quote.low_price:.2f} - ${quote.high_price:.2f}")
print(f"  Volume: {quote.total_volume:,}")
print(f"  Change: ${quote.net_change:+.2f} ({quote.net_percent_change:+.2f}%)")

# Get multiple quotes
print("\n" + "=" * 70)
print("Getting quotes for multiple stocks...")
print("=" * 70)

symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
quotes = client.market_data.get_quotes(symbols)

print(f"\n{'Symbol':<10} {'Last Price':<15} {'Change':<15} {'Volume':<15}")
print("-" * 70)

for symbol, quote in quotes.items():
    if quote.last_price and quote.net_change:
        print(f"{symbol:<10} ${quote.last_price:<14.2f} "
              f"{quote.net_change:+6.2f} ({quote.net_percent_change:+5.2f}%)  "
              f"{quote.total_volume:>12,}")
