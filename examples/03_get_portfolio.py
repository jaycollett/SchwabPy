"""
Example: Get portfolio holdings and account information

This example shows how to retrieve your account information,
positions, and balances.
"""

from schwabpy import SchwabClient

# Initialize client
client = SchwabClient(
    client_id="YOUR_APP_KEY",
    client_secret="YOUR_APP_SECRET",
    redirect_uri="https://127.0.0.1"
)

# Get all account numbers
print("=" * 70)
print("ACCOUNT INFORMATION")
print("=" * 70)

accounts = client.accounts.get_account_numbers()
print(f"\nYou have {len(accounts)} account(s):\n")

for i, account in enumerate(accounts, 1):
    account_hash = account.get('hashValue', '')
    print(f"{i}. Account ending in ...{account_hash[-4:]}")

# Select first account for detailed info
if accounts:
    account_hash = accounts[0]['hashValue']
    print(f"\nGetting details for account ...{account_hash[-4:]}")

    # Get account balance
    print("\n" + "=" * 70)
    print("ACCOUNT BALANCE")
    print("=" * 70)

    balance = client.accounts.get_balance(account_hash)
    print(f"\nCash Balance:        ${balance.cash_balance:,.2f}")
    print(f"Liquidation Value:   ${balance.liquidation_value:,.2f}")
    if balance.buying_power:
        print(f"Buying Power:        ${balance.buying_power:,.2f}")
    if balance.equity:
        print(f"Equity:              ${balance.equity:,.2f}")

    # Get positions
    print("\n" + "=" * 70)
    print("PORTFOLIO POSITIONS")
    print("=" * 70)

    positions = client.accounts.get_positions(account_hash)

    if not positions:
        print("\nNo positions found.")
    else:
        print(f"\nYou have {len(positions)} position(s):\n")
        print(f"{'Symbol':<10} {'Type':<10} {'Quantity':<12} {'Avg Price':<15} {'Market Value':<15}")
        print("-" * 70)

        total_value = 0
        for pos in positions:
            print(f"{pos.symbol:<10} {pos.asset_type:<10} {pos.quantity:<12.2f} "
                  f"${pos.average_price:<14.2f} ${pos.market_value:>14.2f}")
            total_value += pos.market_value

        print("-" * 70)
        print(f"{'Total':<42} ${total_value:>14.2f}\n")

        # Show P&L if available
        print("Unrealized Profit/Loss:")
        print("-" * 70)
        total_pl = 0
        for pos in positions:
            if pos.unrealized_pl is not None:
                pl_percent = pos.unrealized_pl_percent or 0
                print(f"{pos.symbol:<10} ${pos.unrealized_pl:>10.2f} ({pl_percent:>6.2f}%)")
                total_pl += pos.unrealized_pl

        if total_pl != 0:
            print("-" * 70)
            print(f"{'Total P&L':<10} ${total_pl:>10.2f}\n")

else:
    print("\nNo accounts found.")
