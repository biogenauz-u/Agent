class NotebookError(Exception):
    """Base exception safe to translate at transport boundaries."""


class NotebookConfigurationError(NotebookError):
    pass


class NotebookValidationError(NotebookError, ValueError):
    pass


class NotebookNotFoundError(NotebookError):
    pass


class NotebookDuplicateError(NotebookError):
    pass


class NotebookIntegrityError(NotebookError):
    pass


class NotebookConfirmationError(NotebookError):
    pass

