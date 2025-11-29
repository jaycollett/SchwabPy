"""
Account and trading API operations.
"""

import logging
from typing import List, Dict, Optional, Any

from .models import Account, Position, Balance, Order
from .utils import validate_account_hash, validate_date_format

logger = logging.getLogger(__name__)


class Accounts:
    """Handles account-related API operations."""

    def __init__(self, session):
        """
        Initialize accounts handler.

        Args:
            session: Authenticated session object with request method
        """
        self.session = session

    def get_account_numbers(self) -> List[Dict[str, str]]:
        """
        Get linked account numbers.

        Returns:
            List of account number dictionaries

        Example:
            >>> accounts = client.accounts.get_account_numbers()
            >>> for acct in accounts:
            ...     print(acct['accountNumber'])
        """
        endpoint = "/trader/v1/accounts/accountNumbers"
        response = self.session.get(endpoint)
        return response

    def get_accounts(
        self,
        fields: Optional[str] = None
    ) -> List[Account]:
        """
        Get all linked accounts with details.

        Args:
            fields: Optional fields to include (positions)

        Returns:
            List of Account objects

        Example:
            >>> accounts = client.accounts.get_accounts(fields="positions")
            >>> for account in accounts:
            ...     print(f"Account: {account.account_number}")
        """
        params = {}
        if fields:
            params['fields'] = fields

        endpoint = "/trader/v1/accounts"
        response = self.session.get(endpoint, params=params)

        accounts = []
        for account_data in response:
            accounts.append(Account.from_dict(account_data))

        return accounts

    def get_account(
        self,
        account_number: str,
        fields: Optional[str] = None
    ) -> Account:
        """
        Get details for a specific account.

        Args:
            account_number: Account number (encrypted hash)
            fields: Optional fields to include (positions)

        Returns:
            Account object

        Raises:
            ValueError: If account_number is invalid

        Example:
            >>> account = client.accounts.get_account(account_hash, fields="positions")
            >>> print(f"Account type: {account.account_type}")
        """
        account_number = validate_account_hash(account_number)

        params = {}
        if fields:
            params['fields'] = fields

        endpoint = f"/trader/v1/accounts/{account_number}"
        response = self.session.get(endpoint, params=params)

        return Account.from_dict(response)

    def get_positions(self, account_number: str) -> List[Position]:
        """
        Get all positions for an account.

        Args:
            account_number: Account number (encrypted hash)

        Returns:
            List of Position objects

        Raises:
            ValueError: If account_number is invalid

        Example:
            >>> positions = client.accounts.get_positions(account_hash)
            >>> for pos in positions:
            ...     print(f"{pos.symbol}: {pos.quantity} @ ${pos.average_price}")
        """
        # Validation happens in get_account
        account = self.get_account(account_number, fields="positions")

        positions = []
        secure_account = account.raw_data.get('securitiesAccount', {})
        position_list = secure_account.get('positions', [])

        for pos_data in position_list:
            positions.append(Position.from_dict(pos_data))

        return positions

    def get_balance(self, account_number: str) -> Balance:
        """
        Get balance information for an account.

        Args:
            account_number: Account number (encrypted hash)

        Returns:
            Balance object

        Raises:
            ValueError: If account_number is invalid

        Example:
            >>> balance = client.accounts.get_balance(account_hash)
            >>> print(f"Cash: ${balance.cash_balance}")
            >>> print(f"Buying Power: ${balance.buying_power}")
        """
        # Validation happens in get_account
        account = self.get_account(account_number)

        secure_account = account.raw_data.get('securitiesAccount', {})
        return Balance.from_dict(secure_account)

    def get_orders(
        self,
        account_number: str,
        max_results: int = 3000,
        from_entered_time: Optional[str] = None,
        to_entered_time: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Order]:
        """
        Get orders for a specific account.

        Args:
            account_number: Account number (encrypted hash)
            max_results: Maximum number of orders to return (default 3000)
            from_entered_time: Start date (yyyy-MM-dd'T'HH:mm:ss.SSSZ)
            to_entered_time: End date (yyyy-MM-dd'T'HH:mm:ss.SSSZ)
            status: Order status filter

        Returns:
            List of Order objects

        Raises:
            ValueError: If account_number is invalid

        Example:
            >>> orders = client.accounts.get_orders(account_hash, status="WORKING")
            >>> for order in orders:
            ...     print(f"Order {order.order_id}: {order.status}")
        """
        account_number = validate_account_hash(account_number)

        params = {
            'maxResults': max_results
        }
        if from_entered_time:
            params['fromEnteredTime'] = from_entered_time
        if to_entered_time:
            params['toEnteredTime'] = to_entered_time
        if status:
            params['status'] = status

        endpoint = f"/trader/v1/accounts/{account_number}/orders"
        response = self.session.get(endpoint, params=params)

        orders = []
        for order_data in response:
            orders.append(Order.from_dict(order_data))

        return orders

    def get_order(self, account_number: str, order_id: str) -> Order:
        """
        Get a specific order.

        Args:
            account_number: Account number (encrypted hash)
            order_id: Order ID

        Returns:
            Order object

        Raises:
            ValueError: If account_number or order_id is invalid

        Example:
            >>> order = client.accounts.get_order(account_hash, "12345")
            >>> print(f"Status: {order.status}")
        """
        account_number = validate_account_hash(account_number)
        if not order_id or not isinstance(order_id, str):
            raise ValueError("Order ID must be a non-empty string")

        endpoint = f"/trader/v1/accounts/{account_number}/orders/{order_id}"
        response = self.session.get(endpoint)

        return Order.from_dict(response)

    def get_all_orders(
        self,
        max_results: int = 3000,
        from_entered_time: Optional[str] = None,
        to_entered_time: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Order]:
        """
        Get orders for all linked accounts.

        Args:
            max_results: Maximum number of orders to return (default 3000)
            from_entered_time: Start date (yyyy-MM-dd'T'HH:mm:ss.SSSZ)
            to_entered_time: End date (yyyy-MM-dd'T'HH:mm:ss.SSSZ)
            status: Order status filter

        Returns:
            List of Order objects

        Example:
            >>> all_orders = client.accounts.get_all_orders(status="FILLED")
        """
        params = {
            'maxResults': max_results
        }
        if from_entered_time:
            params['fromEnteredTime'] = from_entered_time
        if to_entered_time:
            params['toEnteredTime'] = to_entered_time
        if status:
            params['status'] = status

        endpoint = "/trader/v1/orders"
        response = self.session.get(endpoint, params=params)

        orders = []
        for order_data in response:
            orders.append(Order.from_dict(order_data))

        return orders

    def get_transactions(
        self,
        account_number: str,
        start_date: str,
        end_date: str,
        types: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get account transactions.

        Args:
            account_number: Account number (encrypted hash)
            start_date: Start date (yyyy-MM-dd)
            end_date: End date (yyyy-MM-dd)
            types: Transaction types (comma-separated)
            symbol: Filter by symbol

        Returns:
            List of transaction dictionaries

        Raises:
            ValueError: If account_number or date formats are invalid

        Example:
            >>> transactions = client.accounts.get_transactions(
            ...     account_hash,
            ...     start_date="2024-01-01",
            ...     end_date="2024-01-31"
            ... )
        """
        account_number = validate_account_hash(account_number)
        start_date = validate_date_format(start_date, "yyyy-MM-dd")
        end_date = validate_date_format(end_date, "yyyy-MM-dd")

        params = {
            'startDate': start_date,
            'endDate': end_date
        }
        if types:
            params['types'] = types
        if symbol:
            params['symbol'] = symbol

        endpoint = f"/trader/v1/accounts/{account_number}/transactions"
        response = self.session.get(endpoint, params=params)

        return response

    def get_transaction(
        self,
        account_number: str,
        transaction_id: str
    ) -> Dict[str, Any]:
        """
        Get details of a specific transaction.

        Args:
            account_number: Account number (encrypted hash)
            transaction_id: Transaction ID

        Returns:
            Transaction dictionary

        Raises:
            ValueError: If account_number or transaction_id is invalid

        Example:
            >>> transaction = client.accounts.get_transaction(account_hash, "12345")
        """
        account_number = validate_account_hash(account_number)
        if not transaction_id or not isinstance(transaction_id, str):
            raise ValueError("Transaction ID must be a non-empty string")

        endpoint = f"/trader/v1/accounts/{account_number}/transactions/{transaction_id}"
        response = self.session.get(endpoint)

        return response

    def get_user_preference(self) -> Dict[str, Any]:
        """
        Get user preferences (includes streamer information).

        Returns:
            User preference dictionary

        Example:
            >>> prefs = client.accounts.get_user_preference()
            >>> streamer_info = prefs.get('streamerInfo', [])
        """
        endpoint = "/trader/v1/userPreference"
        response = self.session.get(endpoint)

        return response
