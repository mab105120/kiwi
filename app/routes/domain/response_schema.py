from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error_msg: str = Field(..., description='Error message')
    request_id: str = Field(..., description='Unique request identifier')
