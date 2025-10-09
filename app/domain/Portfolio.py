from domain.User import User

class Portfolio():
    def __init__(self, name: str, description: str, investment_strategy: str, user: User):
        self.name = name
        self.description = description
        self.investment_strategy = investment_strategy
        self.user = user