"""
Example: Authentication with Schwab API

This example shows how to authenticate with the Schwab API using OAuth 2.0.
"""

from schwabpy import SchwabClient

# Initialize the client with your app credentials
client = SchwabClient(
    client_id="YOUR_APP_KEY",
    client_secret="YOUR_APP_SECRET",
    redirect_uri="https://127.0.0.1"  # Must match your app settings
)

# Start authentication flow
# This will print a URL that you need to visit in your browser
client.authenticate()

# After visiting the URL and authorizing, you'll be redirected to a URL like:
# https://127.0.0.1/?code=AUTHORIZATION_CODE&session=SESSION_ID

# Copy the FULL redirect URL and paste it here:
callback_url = input("\nPaste the full callback URL here: ")

# Complete authentication
client.authorize_from_callback(callback_url)

# Now you're authenticated! The tokens are saved and will be automatically refreshed.
print("\nAuthentication complete! You can now use the API.")

# Test the authentication by getting your account numbers
try:
    accounts = client.accounts.get_account_numbers()
    print(f"\nFound {len(accounts)} account(s):")
    for account in accounts:
        print(f"  - {account.get('accountNumber', 'N/A')}")
except Exception as e:
    print(f"Error: {e}")
