class FinanceError(Exception):
    """Safe finance-domain error."""


class FinanceValidationError(FinanceError, ValueError):
    pass


class FinanceNotFoundError(FinanceError):
    pass


class FinanceDuplicateError(FinanceError):
    pass


class FinanceConfirmationError(FinanceError):
    pass
