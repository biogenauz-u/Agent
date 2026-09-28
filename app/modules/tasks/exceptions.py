class TaskError(Exception):
    pass


class TaskValidationError(TaskError, ValueError):
    pass


class TaskNotFoundError(TaskError):
    pass


class TaskConflictError(TaskError):
    pass


class TaskConfirmationError(TaskError):
    pass

