class ApiError(Exception):
    """Shared error envelope matching the error shape defined in contracts/."""

    def __init__(self, message: str, status_code: int = 400, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code

    def to_dict(self) -> dict:
        return {
            "error": {
                "message": self.message,
                "code": self.code,
            }
        }
