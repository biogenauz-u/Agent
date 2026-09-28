class CalendarError(Exception):
    """Safe public messages only; never include provider responses or credentials."""


class CalendarConfigurationError(CalendarError):
    pass


class GoogleCalendarAuthenticationError(CalendarError):
    pass


class GoogleCalendarPermissionError(CalendarError):
    pass


class CalendarEventNotFoundError(CalendarError):
    pass


class GoogleCalendarUnavailableError(CalendarError):
    pass


class CalendarConflictError(CalendarError):
    pass


class OAuthStateError(CalendarError):
    pass
