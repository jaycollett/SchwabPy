"""
Market data API operations.
"""

import logging
from typing import Optional, Dict, List, Any

from .models import Quote, Instrument, OptionChain
from .utils import format_symbol

logger = logging.getLogger(__name__)


class MarketData:
    """Handles market data API operations."""

    def __init__(self, session):
        """
        Initialize market data handler.

        Args:
            session: Authenticated session object with request method
        """
        self.session = session

    def get_quote(self, symbol: str, fields: Optional[str] = None) -> Quote:
        """
        Get a single quote for a symbol.

        Args:
            symbol: Stock symbol
            fields: Optional comma-separated list of fields to include

        Returns:
            Quote object

        Example:
            >>> quote = client.market_data.get_quote("AAPL")
            >>> print(f"{quote.symbol}: ${quote.last_price}")
        """
        symbol = format_symbol(symbol)
        params = {}
        if fields:
            params['fields'] = fields

        endpoint = f"/marketdata/v1/quotes/{symbol}"
        response = self.session.get(endpoint, params=params)

        # Response should contain the quote data
        quote_data = response.get(symbol, response)
        return Quote.from_dict(symbol, quote_data)

    def get_quotes(self, symbols: List[str], fields: Optional[str] = None, indicative: bool = False) -> Dict[str, Quote]:
        """
        Get quotes for multiple symbols.

        Args:
            symbols: List of stock symbols
            fields: Optional comma-separated list of fields
            indicative: Include indicative symbol quotes

        Returns:
            Dictionary mapping symbols to Quote objects

        Example:
            >>> quotes = client.market_data.get_quotes(["AAPL", "MSFT", "GOOGL"])
            >>> for symbol, quote in quotes.items():
            ...     print(f"{symbol}: ${quote.last_price}")
        """
        formatted_symbols = [format_symbol(s) for s in symbols]
        params = {
            'symbols': ','.join(formatted_symbols),
            'indicative': str(indicative).lower()
        }
        if fields:
            params['fields'] = fields

        endpoint = "/marketdata/v1/quotes"
        response = self.session.get(endpoint, params=params)

        return {symbol: Quote.from_dict(symbol, data) for symbol, data in response.items()}

    def get_option_chain(
        self,
        symbol: str,
        contract_type: Optional[str] = None,
        strike_count: Optional[int] = None,
        include_underlying_quote: bool = True,
        strategy: str = "SINGLE",
        interval: Optional[float] = None,
        strike: Optional[float] = None,
        range_value: str = "ALL",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        volatility: Optional[float] = None,
        underlying_price: Optional[float] = None,
        interest_rate: Optional[float] = None,
        days_to_expiration: Optional[int] = None,
        exp_month: str = "ALL",
        option_type: str = "ALL",
        entitlement: str = "PN"
    ) -> OptionChain:
        """
        Get option chain for a symbol.

        Args:
            symbol: Stock symbol
            contract_type: Type of contracts (CALL, PUT, ALL)
            strike_count: Number of strikes above/below at-the-money
            include_underlying_quote: Include underlying quote
            strategy: Option strategy (SINGLE, ANALYTICAL, COVERED, VERTICAL, etc.)
            interval: Strike interval
            strike: Strike price
            range_value: Range (ITM, NTM, OTM, SAK, SBK, SNK, ALL)
            from_date: Start date (yyyy-MM-dd)
            to_date: End date (yyyy-MM-dd)
            volatility: Volatility
            underlying_price: Underlying price
            interest_rate: Interest rate
            days_to_expiration: Days to expiration
            exp_month: Expiration month (JAN, FEB, etc., ALL)
            option_type: Option type (S=Standard, NS=NonStandard, ALL)
            entitlement: Entitlement (PN, NP, PP)

        Returns:
            OptionChain object

        Example:
            >>> chain = client.market_data.get_option_chain("AAPL", contract_type="CALL")
            >>> print(f"Calls available for {chain.symbol}")
        """
        symbol = format_symbol(symbol)

        params = {
            'symbol': symbol,
            'includeUnderlyingQuote': str(include_underlying_quote).lower(),
            'strategy': strategy,
            'range': range_value,
            'expMonth': exp_month,
            'optionType': option_type,
            'entitlement': entitlement
        }

        # Add optional parameters
        if contract_type:
            params['contractType'] = contract_type
        if strike_count:
            params['strikeCount'] = strike_count
        if interval:
            params['interval'] = interval
        if strike:
            params['strike'] = strike
        if from_date:
            params['fromDate'] = from_date
        if to_date:
            params['toDate'] = to_date
        if volatility:
            params['volatility'] = volatility
        if underlying_price:
            params['underlyingPrice'] = underlying_price
        if interest_rate:
            params['interestRate'] = interest_rate
        if days_to_expiration:
            params['daysToExpiration'] = days_to_expiration

        endpoint = "/marketdata/v1/chains"
        response = self.session.get(endpoint, params=params)

        return OptionChain.from_dict(response)

    def get_option_expiration_chain(self, symbol: str) -> Dict[str, Any]:
        """
        Get option expiration dates for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with expiration information

        Example:
            >>> expirations = client.market_data.get_option_expiration_chain("AAPL")
        """
        symbol = format_symbol(symbol)
        endpoint = f"/marketdata/v1/expirationchain/{symbol}"
        response = self.session.get(endpoint)
        return response

    def get_price_history(
        self,
        symbol: str,
        period_type: str = "day",
        period: Optional[int] = None,
        frequency_type: Optional[str] = None,
        frequency: Optional[int] = None,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        need_extended_hours: bool = True,
        need_previous_close: bool = True
    ) -> Dict[str, Any]:
        """
        Get price history for a symbol.

        Args:
            symbol: Stock symbol
            period_type: Period type (day, month, year, ytd)
            period: Number of periods
            frequency_type: Frequency type (minute, daily, weekly, monthly)
            frequency: Frequency (1, 5, 10, 15, 30 for minute)
            start_date: Start date in milliseconds since epoch
            end_date: End date in milliseconds since epoch
            need_extended_hours: Include extended hours data
            need_previous_close: Include previous close

        Returns:
            Dictionary with price history (candles)

        Example:
            >>> history = client.market_data.get_price_history("AAPL", period_type="month", period=1)
            >>> candles = history.get('candles', [])
        """
        symbol = format_symbol(symbol)

        params = {
            'periodType': period_type,
            'needExtendedHoursData': str(need_extended_hours).lower(),
            'needPreviousClose': str(need_previous_close).lower()
        }

        if period:
            params['period'] = period
        if frequency_type:
            params['frequencyType'] = frequency_type
        if frequency:
            params['frequency'] = frequency
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date

        endpoint = f"/marketdata/v1/pricehistory/{symbol}"
        response = self.session.get(endpoint, params=params)

        return response

    def search_instruments(self, symbol: str, projection: str = "symbol-search") -> Dict[str, Instrument]:
        """
        Search for instruments.

        Args:
            symbol: Symbol or search string
            projection: Search type (symbol-search, symbol-regex, desc-search, desc-regex, search, fundamental)

        Returns:
            Dictionary mapping symbols to Instrument objects

        Example:
            >>> results = client.market_data.search_instruments("tech", projection="desc-search")
        """
        params = {
            'symbol': symbol,
            'projection': projection
        }

        endpoint = "/marketdata/v1/instruments"
        response = self.session.get(endpoint, params=params)

        return {symbol_key: Instrument.from_dict(data) for symbol_key, data in response.items()}

    def get_instrument(self, cusip: str) -> Instrument:
        """
        Get instrument by CUSIP.

        Args:
            cusip: CUSIP identifier

        Returns:
            Instrument object

        Example:
            >>> instrument = client.market_data.get_instrument("037833100")  # AAPL
        """
        endpoint = f"/marketdata/v1/instruments/{cusip}"
        response = self.session.get(endpoint)

        # Response contains list of instruments
        instruments = response.get('instruments', [])
        if instruments:
            return Instrument.from_dict(instruments[0])

        raise ValueError(f"No instrument found for CUSIP: {cusip}")

    def get_market_hours(
        self,
        markets: List[str],
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get market hours for specified markets.

        Args:
            markets: List of markets (equity, option, bond, future, forex)
            date: Date in yyyy-MM-dd format (defaults to today)

        Returns:
            Dictionary with market hours information

        Example:
            >>> hours = client.market_data.get_market_hours(["equity", "option"])
        """
        params = {
            'markets': ','.join(markets)
        }
        if date:
            params['date'] = date

        endpoint = "/marketdata/v1/markets"
        response = self.session.get(endpoint, params=params)

        return response

    def get_movers(
        self,
        symbol: str,
        sort: str = "PERCENT_CHANGE_UP",
        frequency: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get market movers for an index.

        Args:
            symbol: Index symbol ($DJI, $COMPX, $SPX)
            sort: Sort order (PERCENT_CHANGE_UP, PERCENT_CHANGE_DOWN, VOLUME, TRADES)
            frequency: Frequency in minutes (0 for all day, 1, 5, 10, 30, 60)

        Returns:
            List of mover dictionaries

        Example:
            >>> movers = client.market_data.get_movers("$SPX", sort="PERCENT_CHANGE_UP")
        """
        params = {
            'sort': sort,
            'frequency': frequency
        }

        endpoint = f"/marketdata/v1/movers/{symbol}"
        response = self.session.get(endpoint, params=params)

        return response.get('screeners', [])
