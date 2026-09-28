class GmailError(Exception):
    """Safe base error for the Gmail integration."""


class GmailConfigurationError(GmailError):
    pass


class GmailAuthenticationError(GmailError):
    pass


class GmailPermissionError(GmailError):
    pass


class GmailMessageNotFoundError(GmailError):
    pass


class GmailRateLimitError(GmailError):
    pass


class GmailUnavailableError(GmailError):
    pass


class MalformedEmailError(GmailError):
    pass
