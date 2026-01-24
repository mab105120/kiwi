from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=30, description='Unique username for the user')
    firstname: str = Field(min_length=1, max_length=30, description='First name of the user')
    lastname: str = Field(min_length=1, max_length=30, description='Last name of the user')
    balance: float = Field(ge=0.0, description='Initial balance for the user account', default=0.0)


class UpdateUserBalanceRequest(BaseModel):
    username: str = Field(min_length=1, max_length=30, description='Username of the user')
    new_balance: float = Field(ge=0.0, description='New balance for the user account')


class CreatePortfolioRequest(BaseModel):
    name: str = Field(min_length=1, max_length=30, description='Portfolio name')
    description: str = Field(min_length=1, max_length=500, description='Portfolio description')
    username: str = Field(min_length=1, max_length=30, description='Owner username')


class LiquidateInvestmentRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=10, description='Security ticker symbol')
    quantity: int = Field(gt=0, description='Number of shares to liquidate')


class ExecutePurchaseOrderRequest(BaseModel):
    portfolio_id: int = Field(gt=0, description='ID of the portfolio to purchase securities for')
    ticker: str = Field(min_length=1, max_length=10, description='Security ticker symbol')
    quantity: int = Field(gt=0, description='Number of shares to purchase')


class AssignPortfolioSecurityRequest(BaseModel):
    portfolio_id: int = Field(gt=0, description='ID of the portfolio')
    username: str = Field(min_length=1, max_length=30, description='Username of the user to assign')
    role: str = Field(min_length=1, max_length=30, description='Role of the user in the portfolio')


class RemovePortfolioSecurityRequest(BaseModel):
    portfolio_id: int = Field(gt=0, description='ID of the portfolio')
    username: str = Field(min_length=1, max_length=30, description='Username of the user to remove')
