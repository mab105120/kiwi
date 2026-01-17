import pytest
import requests

from app.service.alpha_vantage_client import AlphaVantageError, get_company_name, get_price_data, get_quote


def test_get_company_name_success(app, mock_alpha_vantage_response, monkeypatch):
    def mock_requests_get(*_, **__):
        return mock_alpha_vantage_response(
            {
                'bestMatches': [
                    {
                        '1. symbol': 'MSFT',
                        '2. name': 'Microsoft Corporation',
                    }
                ]
            }
        )

    monkeypatch.setattr('app.service.alpha_vantage_client.requests.get', mock_requests_get)

    company_name = get_company_name('MSFT')
    assert company_name == 'Microsoft Corporation'


def test_get_company_name_cache_success(app, monkeypatch):
    from app import cache

    total_requests = 0

    def request_counter(*_, **__):
        nonlocal total_requests
        total_requests += 1
        return total_requests

    monkeypatch.setattr('app.service.alpha_vantage_client.requests.get', request_counter)
    cache.set('company_name:MSFT', 'Microsoft Corporation', timeout=300)

    company_name = get_company_name('MSFT')
    assert company_name == 'Microsoft Corporation'
    assert total_requests == 0


def test_missing_api_key(app, monkeypatch):
    monkeypatch.setitem(app.config, 'ALPHA_VANTAGE_API_KEY', None)

    try:
        get_company_name('AAPL')
    except Exception as e:
        assert isinstance(e, Exception)
        assert str(e) == 'API key not configured'


def test_rate_limit_exceeded(app, mock_alpha_vantage_response, monkeypatch):
    def mock_requests_get(*_, **__):
        return mock_alpha_vantage_response(
            {
                'Note': 'Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute and 500 calls per day.'
            }
        )

    monkeypatch.setattr('app.service.alpha_vantage_client.requests.get', mock_requests_get)

    with pytest.raises(AlphaVantageError) as exc_info:
        get_company_name('AAPL')
    assert 'API rate limit exceeded' in str(exc_info.value)


def test_invalid_ticker(app, mock_alpha_vantage_response, monkeypatch):
    def mock_requests_get(*_, **__):
        return mock_alpha_vantage_response({'bestMatches': []})

    monkeypatch.setattr('app.service.alpha_vantage_client.requests.get', mock_requests_get)

    with pytest.raises(AlphaVantageError) as exc_info:
        get_company_name('INVALID')
    assert 'Ticker INVALID not found' in str(exc_info.value)


def test_get_price_cache_success(app, monkeypatch):
    from app import cache

    total_requests = 0

    def request_counter(*_, **__):
        nonlocal total_requests
        total_requests += 1
        return total_requests

    monkeypatch.setattr('app.service.alpha_vantage_client.requests.get', request_counter)
    cache.set('price_data:MSFT', {'price': 300.00, 'date': '2026-01-08'}, timeout=300)

    price_data = get_price_data('MSFT')
    assert price_data == {'price': 300.00, 'date': '2026-01-08'}
    assert total_requests == 0


def test_get_price_data_success(app, mock_alpha_vantage_response, monkeypatch):
    # clear cache
    from app import cache

    cache.delete('price_data:MSFT')

    def mock_requests_get(*_, **__):
        return mock_alpha_vantage_response(
            {
                'Global Quote': {
                    '01. symbol': 'MSFT',
                    '05. price': '297.9500',
                    '07. latest trading day': '2026-01-15',
                }
            }
        )

    monkeypatch.setattr('app.service.alpha_vantage_client.requests.get', mock_requests_get)

    price_data = get_price_data('MSFT')
    assert price_data == {'price': 297.95, 'date': '2026-01-15'}


# generate tests to achieve 100% coverage for app/service/alpha_vantage_client.py
def test_get_price_data_invalid_ticker(app, mock_alpha_vantage_response, monkeypatch):
    def mock_requests_get(*_, **__):
        return mock_alpha_vantage_response({'Global Quote': {}})

    monkeypatch.setattr('app.service.alpha_vantage_client.requests.get', mock_requests_get)

    with pytest.raises(AlphaVantageError) as exc_info:
        get_price_data('INVALID')
    assert 'No quote data available for INVALID' in str(exc_info.value)


def test_get_price_data_rate_limit_exceeded(app, mock_alpha_vantage_response, monkeypatch):
    def mock_requests_get(*_, **__):
        return mock_alpha_vantage_response(
            {
                'Note': 'Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute and 500 calls per day.'
            }
        )

    monkeypatch.setattr('app.service.alpha_vantage_client.requests.get', mock_requests_get)

    with pytest.raises(AlphaVantageError) as exc_info:
        get_price_data('AAPL')
    assert 'API rate limit exceeded' in str(exc_info.value)


def test_get_quote_success(app, mock_alpha_vantage_response, monkeypatch):
    def mock_requests_get(*_, **kwargs):
        if "'function': 'SYMBOL_SEARCH'" in str(kwargs.get('params', '')):
            return mock_alpha_vantage_response(
                {
                    'bestMatches': [
                        {
                            '1. symbol': 'AAPL',
                            '2. name': 'Apple Inc.',
                        }
                    ]
                }
            )
        elif "'function': 'GLOBAL_QUOTE'" in str(kwargs.get('params', '')):
            return mock_alpha_vantage_response(
                {
                    'Global Quote': {
                        '01. symbol': 'AAPL',
                        '05. price': '150.00',
                        '07. latest trading day': '2026-01-08',
                    }
                }
            )
        return None

    monkeypatch.setattr('app.service.alpha_vantage_client.requests.get', mock_requests_get)

    quote = get_quote('AAPL')
    assert quote is not None
    assert quote.ticker == 'AAPL'
    assert quote.issuer == 'Apple Inc.'
    assert quote.price == 150.00
    assert quote.date == '2026-01-08'
