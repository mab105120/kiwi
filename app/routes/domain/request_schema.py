from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    username: str = Field(
        min_length=1, max_length=30, description="Unique username for the user"
    )
    password: str = Field(min_length=6, description="Password for the user account")
    firstname: str = Field(
        min_length=1, max_length=30, description="First name of the user"
    )
    lastname: str = Field(
        min_length=1, max_length=30, description="Last name of the user"
    )
    balance: float = Field(
        ge=0.0, description="Initial balance for the user account", default=0.0
    )


class UpdateUserBalanceRequest(BaseModel):
    username: str = Field(
        min_length=1, max_length=30, description="Username of the user"
    )
    new_balance: float = Field(ge=0.0, description="New balance for the user account")


class CreatePortfolioRequest(BaseModel):
    name: str = Field(
        min_length=1, max_length=30, description="Portfolio name"
    )
    description: str = Field(
        min_length=1, max_length=500, description="Portfolio description"
    )
    username: str = Field(
        min_length=1, max_length=30, description="Owner username"
    )


class LiquidateInvestmentRequest(BaseModel):
    ticker: str = Field(
        min_length=1, max_length=10, description="Security ticker symbol"
    )
    quantity: int = Field(gt=0, description="Number of shares to liquidate")
    sale_price: float = Field(gt=0.0, description="Sale price per share")


class ExecutePurchaseOrderRequest(BaseModel):
    portfolio_id: int = Field(
        gt=0, description="ID of the portfolio to purchase securities for"
    )
    ticker: str = Field(
        min_length=1, max_length=10, description="Security ticker symbol"
    )
    quantity: int = Field(gt=0, description="Number of shares to purchase")
