class PersonalTelegramError(Exception):
    """Safe base error that may be shown to the owner."""


class PersonalTelegramConfigurationError(PersonalTelegramError):
    pass


class PersonalTelegramNotConnectedError(PersonalTelegramError):
    pass


class PersonalTelegramAuthenticationError(PersonalTelegramError):
    pass


class PersonalTelegramCodeError(PersonalTelegramAuthenticationError):
    pass


class PersonalTelegramPasswordRequired(PersonalTelegramAuthenticationError):
    pass


class PersonalTelegramFloodWaitError(PersonalTelegramError):
    def __init__(self, seconds: int | None = None) -> None:
        self.seconds = max(0, min(seconds or 0, 86400))
        suffix = f" Taxminan {self.seconds} soniya kuting." if self.seconds else ""
        super().__init__("Telegram vaqtinchalik cheklov qo‘ydi." + suffix)


class PersonalTelegramWriteForbiddenError(PersonalTelegramError):
    pass


class PersonalTelegramUnavailableError(PersonalTelegramError):
    pass


class PersonalTelegramDraftError(PersonalTelegramError):
    pass
