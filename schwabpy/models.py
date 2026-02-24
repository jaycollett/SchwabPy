"""
Data models for API responses.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class Account:
    """Represents a Schwab account."""
    account_number: str
    account_type: Optional[str] = None
    is_day_trader: Optional[bool] = None
    is_closing_only_restricted: Optional[bool] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Account':
        """Create Account from API response dictionary."""
        secure_data = data.get('securitiesAccount', {})
        return cls(
            account_number=secure_data.get('accountNumber', ''),
            account_type=secure_data.get('type'),
            is_day_trader=secure_data.get('isDayTrader'),
            is_closing_only_restricted=secure_data.get('isClosingOnlyRestricted'),
            raw_data=data
        )


@dataclass
class Position:
    """Represents a position in a portfolio - provides raw API data."""
    symbol: str
    asset_type: str
    long_quantity: float
    short_quantity: float
    average_price: float
    market_value: float
    current_day_profit_loss: Optional[float] = None
    instrument: Optional[Dict[str, Any]] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """Create Position from API response dictionary."""
        instrument = data.get('instrument', {})

        return cls(
            symbol=instrument.get('symbol', ''),
            asset_type=instrument.get('assetType', ''),
            long_quantity=data.get('longQuantity', 0),
            short_quantity=data.get('shortQuantity', 0),
            average_price=data.get('averagePrice', 0),
            market_value=data.get('marketValue', 0),
            current_day_profit_loss=data.get('currentDayProfitLoss'),
            instrument=instrument,
            raw_data=data
        )


@dataclass
class Balance:
    """Represents account balance information."""
    cash_balance: float
    liquidation_value: float
    long_market_value: Optional[float] = None
    short_market_value: Optional[float] = None
    equity: Optional[float] = None
    buying_power: Optional[float] = None
    margin_balance: Optional[float] = None
    available_funds: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Balance':
        """Create Balance from API response dictionary."""
        current_balances = data.get('currentBalances', {})
        initial_balances = data.get('initialBalances', {})

        return cls(
            cash_balance=current_balances.get('cashBalance', 0),
            liquidation_value=current_balances.get('liquidationValue', 0),
            long_market_value=current_balances.get('longMarketValue'),
            short_market_value=current_balances.get('shortMarketValue'),
            equity=current_balances.get('equity'),
            buying_power=current_balances.get('buyingPower'),
            margin_balance=current_balances.get('marginBalance'),
            available_funds=current_balances.get('availableFunds'),
            raw_data=data
        )


@dataclass
class Quote:
    """Represents a real-time quote for an instrument."""
    symbol: str
    asset_type: str
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    last_price: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    volume: Optional[int] = None
    total_volume: Optional[int] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    open_price: Optional[float] = None
    close_price: Optional[float] = None
    net_change: Optional[float] = None
    net_percent_change: Optional[float] = None
    mark_price: Optional[float] = None
    exchange: Optional[str] = None
    quote_time: Optional[int] = None
    trade_time: Optional[int] = None
    market_maker: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, symbol: str, data: Dict[str, Any]) -> 'Quote':
        """Create Quote from API response dictionary."""
        quote_data = data.get('quote', data)  # Handle nested or flat structure

        return cls(
            symbol=symbol,
            asset_type=data.get('assetType', data.get('assetMainType', 'UNKNOWN')),
            bid_price=quote_data.get('bidPrice'),
            ask_price=quote_data.get('askPrice'),
            last_price=quote_data.get('lastPrice'),
            bid_size=quote_data.get('bidSize'),
            ask_size=quote_data.get('askSize'),
            volume=quote_data.get('lastSize'),
            total_volume=quote_data.get('totalVolume'),
            high_price=quote_data.get('highPrice'),
            low_price=quote_data.get('lowPrice'),
            open_price=quote_data.get('openPrice'),
            close_price=quote_data.get('closePrice'),
            net_change=quote_data.get('netChange'),
            net_percent_change=quote_data.get('netPercentChange'),
            mark_price=quote_data.get('mark'),
            exchange=quote_data.get('exchangeName'),
            quote_time=quote_data.get('quoteTime'),
            trade_time=quote_data.get('tradeTime'),
            market_maker=quote_data.get('marketMaker'),
            raw_data=data
        )


@dataclass
class Instrument:
    """Represents a financial instrument."""
    symbol: str
    cusip: Optional[str] = None
    description: Optional[str] = None
    exchange: Optional[str] = None
    asset_type: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Instrument':
        """Create Instrument from API response dictionary."""
        return cls(
            symbol=data.get('symbol', ''),
            cusip=data.get('cusip'),
            description=data.get('description'),
            exchange=data.get('exchange'),
            asset_type=data.get('assetType'),
            raw_data=data
        )


@dataclass
class Order:
    """Represents a trading order."""
    order_id: str
    account_number: str
    status: str
    order_type: str
    session: str
    duration: str
    entered_time: Optional[str] = None
    close_time: Optional[str] = None
    quantity: Optional[float] = None
    filled_quantity: Optional[float] = None
    remaining_quantity: Optional[float] = None
    price: Optional[float] = None
    stop_price: Optional[float] = None
    order_legs: List[Dict[str, Any]] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        """Create Order from API response dictionary."""
        return cls(
            order_id=str(data.get('orderId', '')),
            account_number=data.get('accountNumber', ''),
            status=data.get('status', ''),
            order_type=data.get('orderType', ''),
            session=data.get('session', ''),
            duration=data.get('duration', ''),
            entered_time=data.get('enteredTime'),
            close_time=data.get('closeTime'),
            quantity=data.get('quantity'),
            filled_quantity=data.get('filledQuantity'),
            remaining_quantity=data.get('remainingQuantity'),
            price=data.get('price'),
            stop_price=data.get('stopPrice'),
            order_legs=data.get('orderLegCollection', []),
            raw_data=data
        )


@dataclass
class OptionChain:
    """Represents an option chain."""
    symbol: str
    status: str
    underlying_price: Optional[float] = None
    call_exp_date_map: Dict[str, Any] = field(default_factory=dict)
    put_exp_date_map: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptionChain':
        """Create OptionChain from API response dictionary."""
        return cls(
            symbol=data.get('symbol', ''),
            status=data.get('status', ''),
            underlying_price=data.get('underlyingPrice'),
            call_exp_date_map=data.get('callExpDateMap', {}),
            put_exp_date_map=data.get('putExpDateMap', {}),
            raw_data=data
        )
