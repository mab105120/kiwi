from app.service import alpha_vantage_client
from app.service.alpha_vantage_client import AlphaVantageError


class SecurityException(Exception):
    pass


def get_security_by_ticker(ticker: str):
    try:
        security_quote = alpha_vantage_client.get_quote(ticker)
        return security_quote
    except AlphaVantageError as e:
        raise SecurityException(f'Failed to retrieve security due to error: {str(e)}')
    except Exception as e:
        raise SecurityException(f'Failed to retrieve security due to error: {str(e)}')
