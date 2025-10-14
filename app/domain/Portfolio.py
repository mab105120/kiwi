from typing import List
from domain.User import User
from domain.Investment import Investment

class Portfolio():
    def __init__(self, name: str, description: str, user: User):
        self.name: str = name
        self.description: str = description
        self.user: User = user
        self.investments: List[Investment] = []

    def __str__(self):
        return f"<Portfolio: name={self.name}; description={self.description}; user={self.user.username}>"
    
    def set_id(self, id: int):
        self.id = id
        
    def get_portfolio_value(self) -> float:
        total_value = 0.0
        for investment in self.investments:
            total_value += investment.security.price * investment.quantity
        return total_value