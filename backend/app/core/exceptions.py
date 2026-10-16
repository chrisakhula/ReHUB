"""Domain exceptions for ReHUB Finance and Accounting."""

from fastapi import HTTPException, status


class FinancialPostingError(HTTPException):
    """Raised when an accounting ledger or General Ledger posting fails,

    ensuring transactions are rolled back atomically without partial financial state.
    """

    def __init__(
        self,
        detail: str = "The financial transaction could not be completed because accounting posting failed. No changes were saved.",
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class FinancialAuthorizationError(HTTPException):
    """Raised when maker-checker or threshold authorization controls are violated."""

    def __init__(
        self,
        detail: str = "Action violates financial segregation of duties or requires senior authorization.",
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )
