"""
Order management API operations.
"""

import logging
from typing import Dict, Any, Optional

from .models import Order

logger = logging.getLogger(__name__)


class Orders:
    """Handles order placement and management."""

    def __init__(self, session):
        """
        Initialize orders handler.

        Args:
            session: Authenticated session object with request method
        """
        self.session = session

    def place_order(self, account_number: str, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place an order.

        Args:
            account_number: Account number (encrypted hash)
            order: Order specification dictionary

        Returns:
            Response dictionary with order ID in headers

        Example:
            >>> order_spec = {
            ...     "orderType": "MARKET",
            ...     "session": "NORMAL",
            ...     "duration": "DAY",
            ...     "orderStrategyType": "SINGLE",
            ...     "orderLegCollection": [{
            ...         "instruction": "BUY",
            ...         "quantity": 10,
            ...         "instrument": {
            ...             "symbol": "AAPL",
            ...             "assetType": "EQUITY"
            ...         }
            ...     }]
            ... }
            >>> result = client.orders.place_order(account_hash, order_spec)
        """
        endpoint = f"/trader/v1/accounts/{account_number}/orders"
        response = self.session.post(endpoint, json=order)

        return response

    def replace_order(
        self,
        account_number: str,
        order_id: str,
        order: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Replace an existing order.

        Args:
            account_number: Account number (encrypted hash)
            order_id: Order ID to replace
            order: New order specification

        Returns:
            Response dictionary

        Example:
            >>> new_order = {...}  # Modified order specification
            >>> result = client.orders.replace_order(account_hash, "12345", new_order)
        """
        endpoint = f"/trader/v1/accounts/{account_number}/orders/{order_id}"
        response = self.session.put(endpoint, json=order)

        return response

    def cancel_order(self, account_number: str, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order.

        Args:
            account_number: Account number (encrypted hash)
            order_id: Order ID to cancel

        Returns:
            Response dictionary

        Example:
            >>> result = client.orders.cancel_order(account_hash, "12345")
        """
        endpoint = f"/trader/v1/accounts/{account_number}/orders/{order_id}"
        response = self.session.delete(endpoint)

        return response

    def preview_order(self, account_number: str, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preview an order before placing (if supported).

        Args:
            account_number: Account number (encrypted hash)
            order: Order specification

        Returns:
            Preview response dictionary

        Note:
            This endpoint may not be available in all API versions.
        """
        endpoint = f"/trader/v1/accounts/{account_number}/previewOrder"
        response = self.session.post(endpoint, json=order)

        return response

    # Order builder helper methods

    @staticmethod
    def build_equity_order(
        symbol: str,
        quantity: int,
        instruction: str,
        order_type: str = "MARKET",
        session: str = "NORMAL",
        duration: str = "DAY",
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Build an equity order specification.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            instruction: BUY, SELL, BUY_TO_COVER, SELL_SHORT
            order_type: MARKET, LIMIT, STOP, STOP_LIMIT
            session: NORMAL, AM, PM, SEAMLESS
            duration: DAY, GOOD_TILL_CANCEL, FILL_OR_KILL
            price: Limit price (required for LIMIT orders)
            stop_price: Stop price (required for STOP orders)

        Returns:
            Order specification dictionary

        Example:
            >>> order = Orders.build_equity_order("AAPL", 10, "BUY", "LIMIT", price=150.00)
        """
        order = {
            "orderType": order_type,
            "session": session,
            "duration": duration,
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": instruction,
                    "quantity": quantity,
                    "instrument": {
                        "symbol": symbol.upper(),
                        "assetType": "EQUITY"
                    }
                }
            ]
        }

        if price is not None:
            order["price"] = str(price)

        if stop_price is not None:
            order["stopPrice"] = str(stop_price)

        return order

    @staticmethod
    def build_option_order(
        symbol: str,
        quantity: int,
        instruction: str,
        order_type: str = "MARKET",
        session: str = "NORMAL",
        duration: str = "DAY",
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Build an option order specification.

        Args:
            symbol: Option symbol (e.g., "AAPL 240315C00150000")
            quantity: Number of contracts
            instruction: BUY_TO_OPEN, BUY_TO_CLOSE, SELL_TO_OPEN, SELL_TO_CLOSE
            order_type: MARKET, LIMIT, STOP, STOP_LIMIT, NET_DEBIT, NET_CREDIT
            session: NORMAL, AM, PM, SEAMLESS
            duration: DAY, GOOD_TILL_CANCEL, FILL_OR_KILL
            price: Limit price (required for LIMIT orders)
            stop_price: Stop price (required for STOP orders)

        Returns:
            Order specification dictionary

        Example:
            >>> order = Orders.build_option_order(
            ...     "AAPL 240315C00150000",
            ...     1,
            ...     "BUY_TO_OPEN",
            ...     "LIMIT",
            ...     price=5.50
            ... )
        """
        order = {
            "orderType": order_type,
            "session": session,
            "duration": duration,
            "orderStrategyType": "SINGLE",
            "complexOrderStrategyType": "NONE",
            "orderLegCollection": [
                {
                    "instruction": instruction,
                    "quantity": quantity,
                    "instrument": {
                        "symbol": symbol.upper(),
                        "assetType": "OPTION"
                    }
                }
            ]
        }

        if price is not None:
            order["price"] = str(price)

        if stop_price is not None:
            order["stopPrice"] = str(stop_price)

        return order

    @staticmethod
    def build_spread_order(
        legs: list,
        order_type: str = "NET_DEBIT",
        price: Optional[float] = None,
        session: str = "NORMAL",
        duration: str = "DAY"
    ) -> Dict[str, Any]:
        """
        Build a multi-leg spread order.

        Args:
            legs: List of leg dictionaries with keys: symbol, quantity, instruction
            order_type: NET_DEBIT, NET_CREDIT, MARKET, LIMIT
            price: Limit price for the spread
            session: NORMAL, AM, PM, SEAMLESS
            duration: DAY, GOOD_TILL_CANCEL

        Returns:
            Order specification dictionary

        Example:
            >>> legs = [
            ...     {"symbol": "AAPL 240315C00150000", "quantity": 1, "instruction": "BUY_TO_OPEN"},
            ...     {"symbol": "AAPL 240315C00155000", "quantity": 1, "instruction": "SELL_TO_OPEN"}
            ... ]
            >>> order = Orders.build_spread_order(legs, "NET_DEBIT", price=2.50)
        """
        order_legs = []
        for leg in legs:
            order_legs.append({
                "instruction": leg["instruction"],
                "quantity": leg["quantity"],
                "instrument": {
                    "symbol": leg["symbol"].upper(),
                    "assetType": leg.get("assetType", "OPTION")
                }
            })

        order = {
            "orderType": order_type,
            "session": session,
            "duration": duration,
            "orderStrategyType": "SINGLE",
            "orderLegCollection": order_legs
        }

        if price is not None:
            order["price"] = str(price)

        return order
