from app.models import Portfolio, Investment, Security

def test_get_portfolio_value():
    p = Portfolio(name="Test Portfolio", description="A test portfolio", owner="test_user")
    security = Security(issuer="Test Security", ticker="TST", price=10.00)
    p.investments = [
        Investment(security=security, quantity=10),
        Investment(security=security, quantity=20)
    ]
    assert str(p) == "<Portfolio: id=None; name=Test Portfolio; description=A test portfolio; user=N/A; #investments=2>"
    assert p.get_portfolio_value() == 300.00