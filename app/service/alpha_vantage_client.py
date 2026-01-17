"""
Alpha Vantage API Client for fetching stock market data.

This module provides functions to interact with the Alpha Vantage API
to retrieve real-time stock quotes and company information.
"""

import logging
from dataclasses import dataclass

import requests
from flask import current_app

logger = logging.getLogger(__name__)


class AlphaVantageError(Exception):
    pass


class APIConnectionError(AlphaVantageError):
    pass


class APIRateLimitError(AlphaVantageError):
    pass


class InvalidTickerError(AlphaVantageError):
    pass


@dataclass
class SecurityQuote:
    ticker: str
    issuer: str
    price: float
    date: str


def _get_cache():
    from app import cache

    return cache


def _get_api_key():
    api_key = current_app.config.get('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        logger.error('ALPHA_VANTAGE_API_KEY not configured')
        raise AlphaVantageError('API key not configured')
    return api_key


def _rate_limit_exceeded(response_json: dict) -> bool:
    return 'Note' in response_json and 'API call frequency' in response_json['Note']


# generate a function to check whether the rate limit is exceeded. if so throw an exception
def _check_rate_limit(response_json: dict):
    if 'Note' in response_json and 'API call frequency' in response_json['Note']:
        logger.warning(f'Alpha Vantage rate limit hit: {response_json["Note"]}')
        raise APIRateLimitError('API rate limit exceeded')


def get_company_name(ticker: str) -> str | None:
    cache = _get_cache()
    cache_key = f'company_name:{ticker.upper()}'
    cached_value = cache.get(cache_key)
    if cached_value is not None:
        return cached_value

    api_key = _get_api_key()
    url = f'{current_app.config.get("ALPHA_VANTAGE_BASE_URL")}/query'
    params = {'function': 'SYMBOL_SEARCH', 'keywords': ticker, 'apikey': api_key}

    try:
        logger.info(f'Fetching company name for ticker: {ticker}')
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        _check_rate_limit(data)

        # Extract best match
        best_matches = data.get('bestMatches', [])
        if not best_matches:
            logger.warning(f'No matches found for ticker: {ticker}')
            raise InvalidTickerError(f'Ticker {ticker} not found')

        company_name = best_matches[0].get('2. name')
        logger.info(f'Found company name for {ticker}: {company_name}')

        # Cache the result
        cache.set(cache_key, company_name, timeout=300)
        return company_name

    except Exception as e:
        msg = f'Error fetching company name for {ticker}. [Error type: {type(e).__name__} | Error: {str(e)}]'
        logger.error(msg)
        raise AlphaVantageError(msg)


def get_price_data(ticker: str) -> dict | None:
    cache = _get_cache()
    cache_key = f'price_data:{ticker.upper()}'
    cached_value = cache.get(cache_key)
    if cached_value is not None:
        return cached_value

    api_key = _get_api_key()

    url = f'{current_app.config.get("ALPHA_VANTAGE_BASE_URL")}/query'
    params = {'function': 'GLOBAL_QUOTE', 'symbol': ticker, 'apikey': api_key}

    try:
        logger.info(f'Fetching price data for ticker: {ticker}')
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        _check_rate_limit(data)

        # Extract quote data
        global_quote = data.get('Global Quote', {})
        if not global_quote:
            logger.warning(f'No quote data found for ticker: {ticker}')
            raise InvalidTickerError(f'No quote data available for {ticker}')

        price = float(global_quote.get('05. price', 0))
        date = global_quote.get('07. latest trading day', '')

        if price == 0:
            logger.warning(f'Invalid price data for ticker: {ticker}')
            raise InvalidTickerError(f'Invalid price data for {ticker}')

        result = {'price': price, 'date': date}
        logger.info(f'Found price for {ticker}: ${price} on {date}')

        # Cache the result
        cache.set(cache_key, result, timeout=300)
        return result

    except Exception as e:
        msg = f'Error fetching price data for {ticker}. [Error type: {type(e).__name__} | Error: {str(e)}]'
        logger.error(msg)
        raise AlphaVantageError(msg)


def get_quote(ticker: str) -> SecurityQuote | None:
    try:
        issuer = get_company_name(ticker)
        if not issuer:
            return None

        price_data = get_price_data(ticker)
        if not price_data:
            return None

        return SecurityQuote(ticker=ticker.upper(), issuer=issuer, price=price_data['price'], date=price_data['date'])
    except Exception as e:
        logger.error(f'Unexpected error fetching quote for {ticker}: {str(e)}')
        raise AlphaVantageError(f'Failed to fetch quote: {str(e)}')
