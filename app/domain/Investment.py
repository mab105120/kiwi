from domain.Security import Security

class Investment():
    def __init__(self, security: Security, quantity: int):
        self.security=security
        self.quantity=quantity

    def __str__(self):
        return f"<Investment: security={self.security}; quantity={self.quantity}>"