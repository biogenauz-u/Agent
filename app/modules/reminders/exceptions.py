class ReminderError(Exception):
    """Safe domain error suitable for owner-facing messages."""


class ReminderConfigurationError(ReminderError):
    pass


class ReminderNotFoundError(ReminderError):
    pass


class ReminderValidationError(ReminderError):
    pass
