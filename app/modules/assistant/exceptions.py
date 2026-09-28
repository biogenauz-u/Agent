class AssistantError(Exception):
    pass


class AssistantNotConfiguredError(AssistantError):
    pass


class AssistantProviderError(AssistantError):
    pass


class AssistantValidationError(AssistantError, ValueError):
    pass


class AssistantConfirmationError(AssistantError):
    pass


class AssistantRateLimitError(AssistantError):
    pass
